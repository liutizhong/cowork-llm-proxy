# 添加新提供商

> 相关页面：[providers/anthropic-compat.md](providers/anthropic-compat.md) · [providers/base.md](providers/base.md) · [config.md](config.md) · [routing.md](routing.md)

如果新提供商支持 Anthropic Messages API 格式，添加一个新提供商只需约 **20 行代码**，修改 4 个文件。

---

## 步骤

### 1. 新建 Provider 文件

`app/providers/my_provider.py`：

```python
from ..config import settings
from .anthropic_compat import AnthropicCompatProvider

class MyProvider(AnthropicCompatProvider):
    _name = "MyProvider"
    _display_prefix = "My - "
    _default_models = [
        {
            "id": "my-model-v1",
            "owned_by": "myprovider",
            "provider": "myprovider",
            "display_name": "My - my-model-v1",
        },
    ]

    def __init__(self) -> None:
        super().__init__()
        self._api_key = settings.my_api_key
        self._base_url = settings.my_base_url
        self._models_url = settings.my_models_url

    def can_handle(self, model_id: str) -> bool:
        return model_id.lower().startswith("my-")
```

### 2. 添加配置字段

`app/config.py` 的 `Settings` 类中添加：

```python
enable_my_provider: bool = False
my_api_key: str = ""
my_base_url: str = "https://api.myprovider.com/anthropic"
my_models_url: str = "https://api.myprovider.com/models"
```

### 3. 注册到 Registry

`app/providers/registry.py` 的 `build_registry()` 中：

```python
from .my_provider import MyProvider

def build_registry(settings) -> ProviderRegistry:
    registry = ProviderRegistry()
    # ... 已有提供商 ...
    if settings.enable_my_provider and settings.my_api_key:
        registry.register(MyProvider())
    return registry
```

### 4. 更新 .env.example

```bash
# MyProvider
ENABLE_MY_PROVIDER=false
MY_API_KEY=
# MY_BASE_URL=https://api.myprovider.com/anthropic
```

---

## 注意事项

**路由前缀冲突**：确保 `can_handle` 的前缀不与现有提供商重叠。当前已使用：`deepseek-`、`glm-`、`kimi-`、`minimax-`、`qwen-`、`ollama-`。

**格式不兼容**：如果上游不是 Anthropic 格式（类似 Ollama 的情况），需要直接继承 `BaseProvider` 并自行实现格式转换。参考 [providers/ollama.md](providers/ollama.md)。

**不同的鉴权方式**：`AnthropicCompatProvider` 默认同时发送 `x-api-key` 和 `Authorization: Bearer` 两个头。如果上游只接受其中一种，需在子类中覆盖 `_build_headers()` 方法。

**Fallback 模型**：`_default_models` 在上游模型列表请求失败时使用，至少填写一到两个稳定的模型，避免 `/v1/models` 返回空列表。

---

## 不需要修改的内容

添加新提供商时，以下代码**不需要改动**：

- `app/auth.py`
- `app/api/messages.py`
- `app/api/models.py`
- `app/main.py`

路由层、鉴权层、API 层完全通过 `ProviderRegistry` 和 `BaseProvider` 接口工作，对具体提供商实现无感知。

---

## 相关页面

- AnthropicCompatProvider 详解 → [providers/anthropic-compat.md](providers/anthropic-compat.md)
- 路由机制 → [routing.md](routing.md)
- 配置参考 → [config.md](config.md)
