# 请求路由机制

> 相关页面：[architecture.md](architecture.md) · [providers/base.md](providers/base.md) · [providers/registry.md](providers/anthropic-compat.md)

## 路由原理

路由逻辑极简：**按注册顺序遍历提供商，第一个 `can_handle(model_id)` 返回 `True` 的提供商处理请求**。

```python
# app/providers/registry.py
def route(self, model_id: str) -> BaseProvider:
    for provider in self._providers:
        if provider.can_handle(model_id):
            return provider
    raise ValueError(f"No provider for model: {model_id}")
```

## 各提供商的路由规则

| 提供商 | 匹配规则 | 示例模型 ID |
|---|---|---|
| DeepSeek | `model_id.lower().startswith("deepseek-")` | `deepseek-v4-pro`, `deepseek-v4-flash` |
| DashScope | 前缀为 `glm-` / `kimi-` / `minimax-` / `qwen-` | `glm-5`, `kimi-k2.5`, `qwen-max` |
| Ollama | `model_id.lower().startswith("ollama-")` | `ollama-llama3-2-latest` |

> **Ollama 的模型 ID 转换**：Ollama 原生模型名包含 `/` 和 `:` 字符（如 `llama3.2:latest`），不适合作为 HTTP 参数。`OllamaProvider` 内部维护一个 `_id_to_name` 映射，将安全 ID（如 `ollama-llama3-2-latest`）还原为 Ollama 原生名称。见 [providers/ollama.md](providers/ollama.md)。

## 注册顺序

`build_registry()` 按以下顺序注册（代码位于 `app/providers/registry.py`）：

1. DeepSeek（如 `ENABLE_DEEPSEEK=true`）
2. DashScope（如 `ENABLE_DASHSCOPE=true`）
3. Ollama（如 `ENABLE_OLLAMA=true`）

由于各提供商的 `can_handle` 规则互不重叠，当前顺序不影响路由结果。添加自定义提供商时需注意前缀冲突。

## 模型列表的合并

`GET /v1/models` 调用 `registry.list_all_models()`，依次从各提供商获取模型列表，**按提供商顺序合并、对相同 ID 去重**。如果配置了 `ALLOWED_MODELS`，在此步骤后过滤。

每个提供商的模型 `display_name` 会加上提供商前缀（如 `"DeepSeek - deepseek-v4-pro"`），便于客户端区分来源。

## 路由失败处理

如果没有提供商能处理请求的 `model_id`，`messages.router` 返回 Anthropic 格式的 404 错误：

```json
{
  "type": "error",
  "error": {
    "type": "not_found_error",
    "message": "Model not found: <model_id>"
  }
}
```

## 相关页面

- BaseProvider 接口 → [providers/base.md](providers/base.md)
- 添加新路由规则 → [extending.md](extending.md)
