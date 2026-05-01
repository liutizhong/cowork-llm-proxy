# BaseProvider 抽象接口

> 相关页面：[anthropic-compat.md](anthropic-compat.md) · [ollama.md](ollama.md) · [../routing.md](../routing.md)

源文件：`app/providers/base.py`

## 接口定义

```python
class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def display_prefix(self) -> str: ...

    @abstractmethod
    def can_handle(self, model_id: str) -> bool: ...

    @abstractmethod
    async def list_models(self) -> list[dict]: ...

    @abstractmethod
    async def forward(self, request: Request) -> Response: ...

    @abstractmethod
    async def forward_stream(self, request: Request) -> AsyncGenerator[bytes, None]: ...
```

## 方法说明

| 方法 | 说明 |
|---|---|
| `name` | 提供商的唯一标识符，用于 `/health` 响应和日志 |
| `display_prefix` | 展示给客户端的模型名前缀（如 `"DeepSeek - "`） |
| `can_handle(model_id)` | 路由判断：该提供商是否能处理此 model_id |
| `list_models()` | 返回该提供商支持的模型列表（Anthropic 格式） |
| `forward(request)` | 处理非流式请求，返回完整 `Response` |
| `forward_stream(request)` | 处理流式请求，yield 原始 SSE 字节 |

## 实现层次

```
BaseProvider (抽象)
├── AnthropicCompatProvider (通用 HTTP 代理)
│   ├── DeepSeekProvider
│   └── DashScopeProvider
└── OllamaProvider (独立实现，含格式转换)
```

`AnthropicCompatProvider` 提供了 `list_models`、`forward`、`forward_stream` 的完整实现，子类通常只需覆盖 `can_handle` 和初始化逻辑。

`OllamaProvider` 完全独立实现，因为 Ollama 使用 OpenAI 格式而非 Anthropic 格式。

## 模型列表格式

`list_models()` 返回的每条记录格式：

```json
{
  "id": "deepseek-v4-pro",
  "owned_by": "deepseek",
  "provider": "deepseek",
  "display_name": "DeepSeek - deepseek-v4-pro"
}
```

## 相关页面

- 通用代理实现 → [anthropic-compat.md](anthropic-compat.md)
- Ollama 独立实现 → [ollama.md](ollama.md)
- 路由如何使用此接口 → [../routing.md](../routing.md)
