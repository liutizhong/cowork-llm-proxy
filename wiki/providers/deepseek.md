# DeepSeek Provider

> 相关页面：[anthropic-compat.md](anthropic-compat.md) · [../config.md](../config.md) · [../routing.md](../routing.md)

源文件：`app/providers/deepseek.py`

## 基本信息

| 项目 | 值 |
|---|---|
| 类名 | `DeepSeekProvider` |
| 继承自 | `AnthropicCompatProvider` |
| `name` | `"DeepSeek"` |
| `display_prefix` | `"DeepSeek - "` |

## 路由规则

```python
def can_handle(self, model_id: str) -> bool:
    return model_id.lower().startswith("deepseek-")
```

匹配示例：`deepseek-v4-pro`、`deepseek-v4-flash`、`deepseek-r1`

## 端点配置

| 配置项 | 默认值 | 环境变量覆盖 |
|---|---|---|
| 推理端点 | `https://api.deepseek.com/anthropic` | `DEEPSEEK_BASE_URL` |
| 模型列表 | `https://api.deepseek.com/models` | `DEEPSEEK_MODELS_URL` |
| API Key | — | `DEEPSEEK_API_KEY` |

## 内置 Fallback 模型

上游模型列表请求失败时使用：

- `deepseek-v4-flash`
- `deepseek-v4-pro`

## 启用条件

`docker-compose` / `.env` 中同时满足：
```
ENABLE_DEEPSEEK=true
DEEPSEEK_API_KEY=sk-...
```

## 使用示例

```bash
curl https://my.cowork.llm/v1/messages \
  -H "x-api-key: $PROXY_KEY" \
  -H "content-type: application/json" \
  -d '{"model": "deepseek-v4-pro", "max_tokens": 1024,
       "messages": [{"role": "user", "content": "Hello"}]}'
```

## 相关页面

- 实现基类 → [anthropic-compat.md](anthropic-compat.md)
- 配置参考 → [../config.md](../config.md)
