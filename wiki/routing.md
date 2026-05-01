# Routing — 请求路由

## 路由决策树

```
POST /v1/messages
body.model = "???"
        │
        ▼
┌───────────────────┐
│ model.startswith  │
│   "deepseek-"?    │──YES──→ DeepSeekProvider
└───────────────────┘
        │ NO
        ▼
┌───────────────────────────────────────────┐
│ model.startswith any of:                  │
│   "glm-" | "kimi-" | "minimax-" | "qwen-"│──YES──→ DashScopeProvider
└───────────────────────────────────────────┘
        │ NO
        ▼
┌───────────────────┐
│ model.startswith  │
│   "ollama-"?      │──YES──→ OllamaProvider
└───────────────────┘
        │ NO
        ▼
    ValueError → 404 not_found_error
    (日志: WARNING "No provider for model 'xxx'")
```

## Model ID 命名规范

| Provider | 前缀 | 示例 |
|----------|------|------|
| DeepSeek | `deepseek-` | `deepseek-v4-pro`, `deepseek-v4-flash` |
| DashScope | `glm-` | `glm-5`, `glm-5.1`, `glm-4.7` |
| DashScope | `kimi-` | `kimi-k2.5`, `kimi-k2.6` |
| DashScope | `minimax-` | `minimax-m2.5` |
| DashScope | `qwen-` | `qwen-max`, `qwen-plus`, ... |
| Ollama | `ollama-` | `ollama-llama3-2-latest`, `ollama-qwen3-6-27b` |

## Ollama Model ID 转换规则

```python
# 原始名称 → 安全代理 ID
"llama3.2:latest"  →  "ollama-llama3-2-latest"
"qwen3.6:27b"      →  "ollama-qwen3-6-27b"
"nomic-embed-text" →  "ollama-nomic-embed-text"

# 规则：
# 1. 替换 '/' → '-'
# 2. 替换 ':' → '-'
# 3. 替换 '.' → '-'
# 4. 加前缀 "ollama-"
```

反向映射保存在 `OllamaProvider._id_to_name`，在 `list_models()` 时填充，在 `forward()` / `forward_stream()` 时查询。

## 路由注意事项

### 1. ALLOWED_MODELS 只过滤展示，不影响路由

`/v1/models` 接口根据 `ALLOWED_MODELS` 过滤，但 `registry.route()` 不看白名单。若客户端直接传一个不在白名单里但在 provider 前缀范围内的 model ID，请求仍会被路由到对应 provider。

### 2. 优先级由注册顺序决定

`build_registry()` 按 DeepSeek → DashScope → Ollama 顺序注册。若将来新增前缀有重叠，靠前的 provider 获胜。

### 3. 未知 model ID 导致 404

客户端（如 trading-agent）可能使用了不匹配任何前缀的 model ID（如 `claude-3-5-sonnet-20241022`）。这会触发 404。**解决办法**：
- 检查客户端配置，确保使用代理支持的 model ID
- 或增加新的 provider 处理该前缀

### 4. Ollama 模型名在重启后需要重新加载

`_id_to_name` 是内存 dict，容器重启清空。`lifespan` 中的 `await registry.list_all_models()` 会在启动时预热。若 Ollama 在代理启动时不可达，映射为空，首次请求会触发 `list_models()` 刷新。
