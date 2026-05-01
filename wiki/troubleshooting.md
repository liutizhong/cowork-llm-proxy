# Troubleshooting — 已解决问题清单

按发现时间排序，每条包含：现象、根因、修复。

---

## #1 开启 ENABLE_OLLAMA 后 Claude Desktop 模型列表空白

**现象**：`ENABLE_OLLAMA=true` 后 Claude Desktop 无法显示任何模型。

**根因**：Ollama 模型名称包含 `.`（如 `llama3.2:latest`），导致 model ID 在 URL path 中被解析为文件扩展名，或客户端拒绝使用含特殊字符的 ID。

**修复**：引入 `_safe_model_id()` 函数，将 `/` `:` `.` 替换为 `-`，并加 `ollama-` 前缀。双向映射存在 `_id_to_name`。

```python
def _safe_model_id(name: str) -> str:
    safe = name.replace("/", "-").replace(":", "-").replace(".", "-")
    return f"ollama-{safe}"
```

---

## #2 容器重启后 Ollama 模型路由失败

**现象**：`POST /v1/messages` body 中 model=`ollama-xxx`，返回 503，日志显示 `ollama_name` 等于 proxy ID 本身（`ollama-xxx`），Ollama 报 model not found。

**根因**：`_id_to_name` dict 是内存结构，容器重启后清空，但 `forward_stream` 中直接做 dict 查询（不 await），不会触发 `list_models()` 刷新。

**修复**：在 FastAPI `lifespan` 启动时调用 `await registry.list_all_models()` 预热，确保 `_id_to_name` 在第一个请求前已填充。

```python
async def lifespan(app):
    registry = build_registry()
    app.state.registry = registry
    await registry.list_all_models()   # 预热 _id_to_name
    yield
```

---

## #3 `/v1/models` 返回后 Claude Desktop 仍无法显示模型

**现象**：`GET /v1/models` 有响应数据，但 Claude Desktop UI 不渲染。

**根因**：误删了响应中的 `"object": "list"` 字段，认为它是 OpenAI 格式不需要。事实上 Claude Desktop 强依赖这个字段。

**修复**：恢复 `"object": "list"`，同时保留 Anthropic 格式字段（`first_id`、`last_id`、`has_more`）。

---

## #4 Ollama forward_stream 触发 TLS ConnectTimeout

**现象**：流式请求报 `httpcore.ConnectTimeout: start_tls`。

**根因**：`forward_stream` 是 `AsyncGenerator`。在 generator 内部调用 `await self._resolve_name()`（其内部发起 `httpx.AsyncClient.get()`），会与外层 `client.stream()` 共享 httpx 连接池，触发意外的 TLS upgrade 尝试。

**修复**：`forward_stream` 内改为同步 dict 查询，不发起任何异步 HTTP：

```python
# 改前（有问题）
ollama_name = await self._resolve_name(model_id)

# 改后（正确）
ollama_name = self._id_to_name.get(model, model.removeprefix(_PREFIX))
```

---

## #5 stream=False 请求长时间挂起

**现象**：非流式请求（`stream=False`）对大模型（如 27B）一直等待，最终超时。

**根因**：Ollama 是单线程 HTTP 服务。非流式请求会阻塞 Ollama 进程，直到完整输出生成完毕。同时代理也在等待，形成双重阻塞，极易触发 httpx 读超时。

**修复**：`OllamaProvider.forward()` 内部改为向 Ollama 发流式请求，在本地逐 token 聚合，最后组装完整响应返回：

```python
async with client.stream("POST", url, json=_to_openai_body(body, name, stream=True)) as resp:
    async for line in resp.aiter_lines():
        # 收集 token，拼接 full_text
return 200, {..., "content": [{"type":"text","text": full_text}]}, None
```

---

## #6 客户端报 ECONNRESET

**现象**：Claude Desktop 报 `Unable to connect to API (ECONNRESET)`，日志无明显异常。

**根因**（两处）：
1. `OllamaProvider.forward()` 捕获 `httpx.ReadTimeout` 后没有 catch，导致 uvicorn 任务崩溃，连接被强制关闭。
2. nginx `proxy_send_timeout` 默认 60s，长时间推理时 nginx 主动断开与客户端的连接。

**修复**：
1. `forward()` 加 `except httpx.ReadTimeout` 返回 503。
2. `nginx.conf` 加 `proxy_send_timeout 300s`。

---

## #7 DeepSeek 401 Authorization Required

**现象**：DeepSeek 请求报 `401`，日志显示 `Authorization Required`。

**根因**：旧版 `_upstream_headers()` 只发 `x-api-key`（Anthropic 格式），但 DeepSeek 的 Anthropic-compatible 端点要求 `Authorization: Bearer` 头（OpenAI 格式）。

**修复**：同时发送两种认证头：

```python
{
    "x-api-key": self._api_key,
    "Authorization": f"Bearer {self._api_key}",
}
```

---

## #8 ASGI 崩溃（前置异常未捕获）

**现象**：日志出现 `Exception in ASGI application`，uvicorn traceback，某些请求后服务不稳定。

**根因**：`AnthropicCompatProvider.forward()` 和 `forward_stream()` 没有顶层异常处理，`httpx.ConnectTimeout` 等直接冒泡到 ASGI 层。

**修复**：两个方法都加完整 try/except：

- `forward()`：`ConnectTimeout` → 503 overloaded、`ReadTimeout` → 503 overloaded、`Exception` → 503 api_error
- `forward_stream()`：`Exception` → yield error SSE 帧

---

## #9 pydantic-settings v2 SettingsError（ALLOWED_MODELS）

**现象**：启动时崩溃：
```
SettingsError: error parsing value for field "allowed_models" from source "EnvSettingsSource"
```
`.env` 中 `ALLOWED_MODELS=deepseek-v4-pro,glm-5,...`（CSV 格式）。

**根因**：pydantic-settings v2 对 `list[str]` 字段会先尝试 JSON 解析，然后才调用 `@field_validator`。CSV 字符串不是合法 JSON，直接抛出 `SettingsError`，validator 根本没机会运行。

**修复**：改为 `str` 字段 + `@property`：

```python
# 字段类型改为 str
allowed_models_raw: str = Field(default="", alias="ALLOWED_MODELS")

# 对外接口保持 list[str]
@property
def allowed_models(self) -> list[str]:
    v = self.allowed_models_raw.strip()
    return [m.strip() for m in v.split(",") if m.strip()] if v else []
```

---

## #10 /v1/messages/count_tokens 404

**现象**：客户端频繁请求 `POST /v1/messages/count_tokens?beta=true`，全部 404。

**根因**：该端点未实现，客户端（如 Claude Code、trading-agent）会预估 token 用量，若 404 可能触发重试风暴。

**修复**：添加存根实现，按 `total_chars // 4` 估算 `input_tokens`：

```python
@router.post("/messages/count_tokens")
async def count_tokens(request: Request):
    # ... 统计 system + messages 字符数
    return JSONResponse(content={"input_tokens": max(1, total_chars // 4)})
```

---

## 诊断工具

```bash
# 查看实时日志
docker logs -f llm-proxy

# 测试模型路由（会在日志中打印 provider 名）
curl -s -H "x-api-key: $KEY" -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model":"<model_id>","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'

# 检查 404 模型的原因（看 WARNING 日志行）
docker logs llm-proxy 2>&1 | grep "No provider for model"
```
