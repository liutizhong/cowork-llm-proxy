# AnthropicCompatProvider

> 相关页面：[base.md](base.md) · [deepseek.md](deepseek.md) · [dashscope.md](dashscope.md)

源文件：`app/providers/anthropic_compat.py`

## 定位

所有上游支持 Anthropic Messages API 格式的提供商的通用基类实现。不使用 Anthropic Python SDK，直接用 **httpx 做纯 HTTP 代理**。

## 核心机制

### 请求转发

```
原始请求体  ──────────────────────────────► 上游端点
原始请求头  → 替换 Authorization 为上游 Key → 上游端点
             保留 anthropic-version
             保留 anthropic-beta
             保留 content-type
```

关键：**请求体完全不修改**，原样透传。这意味着任何 Anthropic Messages API 支持的字段（`system`、`tools`、`thinking` 等）都能无损传递到上游。

### 流式响应

```python
async def forward_stream(self, request):
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", self._base_url, ...) as resp:
            async for chunk in resp.aiter_bytes():
                yield chunk
```

字节级透传，不解析 SSE 帧，零额外延迟。

### 模型列表缓存

每个 Provider 实例维护一个 `_models_cache`（5 分钟 TTL）：

```
首次调用 list_models()
  └─ 请求上游 _models_url
  └─ 解析响应，提取 data[] 列表
  └─ 存入 _models_cache + 记录时间戳

后续调用（5 分钟内）
  └─ 直接返回缓存

超过 5 分钟 或 上游请求失败
  └─ 返回 _default_models（fallback）
```

> **多 worker 注意**：uvicorn 多 worker 模式下，每个 worker 进程独立维护缓存，不共享。

## 子类需实现的内容

继承 `AnthropicCompatProvider` 的子类最少只需提供：

```python
class MyProvider(AnthropicCompatProvider):
    _name = "MyProvider"
    _display_prefix = "My - "
    _default_models = [...]

    def __init__(self):
        super().__init__()
        self._api_key = settings.my_api_key
        self._base_url = settings.my_base_url
        self._models_url = settings.my_models_url

    def can_handle(self, model_id: str) -> bool:
        return model_id.lower().startswith("my-")
```

## Header 处理细节

转发时的 Header 策略：

| Header | 处理方式 |
|---|---|
| `authorization` | 替换为 `Bearer {self._api_key}` |
| `x-api-key` | 替换为 `{self._api_key}` |
| `anthropic-version` | 原样保留 |
| `anthropic-beta` | 原样保留 |
| `content-type` | 原样保留 |
| `host` | 不转发（由 httpx 自动设置） |
| `content-length` | 不转发（由 httpx 自动设置） |

## 相关页面

- 接口定义 → [base.md](base.md)
- DeepSeek 具体实现 → [deepseek.md](deepseek.md)
- DashScope 具体实现 → [dashscope.md](dashscope.md)
- 添加新提供商 → [../extending.md](../extending.md)
