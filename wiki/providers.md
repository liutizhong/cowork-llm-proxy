# Providers — 提供商体系

## 继承树

```
BaseProvider (ABC)
├── AnthropicCompatProvider        # 直接透传 body，仅替换 header
│   ├── DeepSeekProvider           # 前缀：deepseek-
│   └── DashScopeProvider          # 前缀：glm- / kimi- / minimax- / qwen-
└── OllamaProvider                 # Anthropic ↔ OpenAI 格式转换
```

---

## BaseProvider

**文件**：`app/providers/base.py`

抽象基类，定义四个必须实现的接口：

| 方法 | 签名 | 职责 |
|------|------|------|
| `name` | `@property → str` | 提供商显示名称 |
| `display_prefix` | `@property → str` | 模型列表展示前缀，如 `"DeepSeek - "` |
| `can_handle(model_id)` | `str → bool` | 路由判断：此 provider 是否负责该 model |
| `list_models()` | `async → list[dict]` | 返回上游模型列表（带缓存） |
| `forward(path, body, headers)` | `async → (status, json, None)` | 非流式转发 |
| `forward_stream(path, body, headers)` | `async generator → bytes` | 流式转发，yield 原始 SSE 字节 |

---

## AnthropicCompatProvider

**文件**：`app/providers/anthropic_compat.py`

通用基类，供 DeepSeek 和 DashScope 继承。子类只需设置 class-level 属性，无需额外代码。

### Class 属性（子类覆盖）

```python
_name: str          # e.g. "DeepSeek"
_display_prefix: str # e.g. "DeepSeek - "
_base_url: str      # Anthropic-compat 推理端点，e.g. "https://api.deepseek.com/anthropic"
_api_key: str       # 厂商 API Key（从 settings 注入）
_models_url: str    # OpenAI-compat /models 端点
_default_models: list[dict]  # 若 /models 请求失败时的兜底列表
```

### 模型缓存

```python
_cache: list[dict] | None  # 缓存的模型列表
_cache_ts: float           # 缓存时间戳
_lock: asyncio.Lock        # 防止并发重复 fetch
TTL = 300s (5分钟)
```

### 请求头策略

同时发送两种认证头，兼容 Anthropic 格式和 OpenAI 格式的端点：

```python
{
    "x-api-key": self._api_key,           # Anthropic 格式
    "Authorization": f"Bearer {self._api_key}",  # OpenAI 格式
    "Content-Type": "application/json",
    # 透传 anthropic-version、anthropic-beta（如果客户端有）
}
```

### 错误处理

| 异常 | 返回 |
|------|------|
| `httpx.ConnectTimeout` | 503 + `overloaded_error` |
| `httpx.ReadTimeout` | 503 + `overloaded_error` |
| 其他 `Exception` | 503 + `api_error`（含 `type(exc).__name__`）|

---

## DeepSeekProvider

**文件**：`app/providers/deepseek.py`

| 属性 | 值 |
|------|-----|
| `_name` | `"DeepSeek"` |
| `_display_prefix` | `"DeepSeek - "` |
| `_base_url` | `https://api.deepseek.com/anthropic` |
| `_models_url` | `https://api.deepseek.com/models` |
| `can_handle` | `model_id.lower().startswith("deepseek-")` |

默认模型兜底：`deepseek-v4-flash`、`deepseek-v4-pro`

---

## DashScopeProvider

**文件**：`app/providers/dashscope.py`

| 属性 | 值 |
|------|-----|
| `_name` | `"DashScope"` |
| `_display_prefix` | `"Aliyun - "` |
| `_base_url` | `https://dashscope.aliyuncs.com/apps/anthropic` |
| `_models_url` | `https://dashscope.aliyuncs.com/compatible-mode/v1/models` |
| `can_handle` | 前缀匹配 `glm-` / `kimi-` / `minimax-` / `qwen-` |

默认模型兜底：`glm-5`、`glm-5.1`、`glm-4.7`、`kimi-k2.5`、`minimax-m2.5`

> **注意**：DashScope 返回约 238 个模型，但通常通过 `ALLOWED_MODELS` 白名单只暴露少数几个。

---

## OllamaProvider

**文件**：`app/providers/ollama.py`

### Model ID 命名规则

Ollama 原始名称包含 `/`、`:`、`.` 等字符，不能直接用于 URL path。代理做以下映射：

```
llama3.2:latest  →  ollama-llama3-2-latest
qwen3.6:27b      →  ollama-qwen3-6-27b
```

规则：前缀 `ollama-`，`/` `:` `.` 替换为 `-`。

双向映射存在 `_id_to_name: dict[str, str]`，在 `list_models()` 时填充，用于把安全 ID 反查回 Ollama 原始名称。

### 路由判断

```python
def can_handle(self, model_id: str) -> bool:
    return model_id.lower().startswith("ollama-")
```

### 格式转换

**请求（Anthropic → OpenAI）**

```python
# system prompt 提取为 {"role": "system", "content": "..."}
# messages 中的 content list 展开为纯文本
# 透传 max_tokens / temperature / top_p
{
    "model": "<ollama_native_name>",
    "messages": [...],
    "stream": true/false,
    "max_tokens": ...,
}
```

**响应（OpenAI → Anthropic）**

```python
{
    "id": "msg_ollama_<timestamp>",
    "type": "message",
    "role": "assistant",
    "model": "<proxy_model_id>",
    "content": [{"type": "text", "text": "..."}],
    "stop_reason": "end_turn" | "max_tokens",
    "stop_sequence": None,
    "usage": {"input_tokens": ..., "output_tokens": ...},
}
```

**SSE 事件序列（流式）**

```
event: message_start
event: content_block_start  (index=0)
event: ping
event: content_block_delta  (重复，每个 token)
...
event: content_block_stop
event: message_delta        (含 stop_reason)
event: message_stop
```

> 关键：只在确认 Ollama 返回 200 后才发送 `message_start` 等开头事件，避免客户端收到空流。

### 超时配置

```python
httpx.Timeout(settings.timeout, connect=30)
# connect 比 AnthropicCompat 的 10s 更长，因为 Ollama 加载模型可能慢
```

---

## ProviderRegistry

**文件**：`app/providers/registry.py`

```python
class ProviderRegistry:
    _providers: list[BaseProvider]

    def route(model_id) -> BaseProvider:
        # 顺序遍历，第一个 can_handle 为真的提供商获胜
        # 无匹配 → raise ValueError（被路由层转为 404）

    async def list_all_models() -> list[dict]:
        # 合并所有 provider 的 list_models()
        # 去重（按 id），添加 display_name 前缀、type="model"、created_at
```

### build_registry()

按以下顺序注册（影响路由优先级）：
1. DeepSeek（若 `ENABLE_DEEPSEEK=true` 且有 key）
2. DashScope（若 `ENABLE_DASHSCOPE=true` 且有 key）
3. Ollama（若 `ENABLE_OLLAMA=true`，无需 key）

**注意**：若一个模型 ID 可被多个 provider `can_handle`，注册顺序靠前的获胜。
