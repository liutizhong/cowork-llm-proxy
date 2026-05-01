# DashScope Provider（阿里云）

> 相关页面：[anthropic-compat.md](anthropic-compat.md) · [../config.md](../config.md) · [../routing.md](../routing.md)

源文件：`app/providers/dashscope.py`

## 基本信息

| 项目 | 值 |
|---|---|
| 类名 | `DashScopeProvider` |
| 继承自 | `AnthropicCompatProvider` |
| `name` | `"DashScope"` |
| `display_prefix` | `"Aliyun - "` |

## 路由规则

DashScope 托管来自多个模型家族，通过前缀匹配：

```python
def can_handle(self, model_id: str) -> bool:
    prefixes = ("glm-", "kimi-", "minimax-", "qwen-")
    return any(model_id.lower().startswith(p) for p in prefixes)
```

| 前缀 | 模型家族 |
|---|---|
| `glm-` | 智谱 GLM 系列 |
| `kimi-` | 月之暗面 Kimi 系列 |
| `minimax-` | MiniMax 系列 |
| `qwen-` | 阿里通义千问系列 |

## 端点配置

| 配置项 | 默认值 | 环境变量覆盖 |
|---|---|---|
| 推理端点 | `https://dashscope.aliyuncs.com/apps/anthropic` | `DASHSCOPE_BASE_URL` |
| 模型列表 | `https://dashscope.aliyuncs.com/compatible-mode/v1/models` | `DASHSCOPE_MODELS_URL` |
| API Key | — | `DASHSCOPE_API_KEY` |

## 内置 Fallback 模型

| 模型 ID | 家族 |
|---|---|
| `glm-5` | GLM |
| `glm-5.1` | GLM |
| `glm-4.7` | GLM |
| `kimi-k2.5` | Kimi |
| `minimax-m2.5` | MiniMax |

## 启用条件

```
ENABLE_DASHSCOPE=true
DASHSCOPE_API_KEY=sk-...
```

## 使用示例

```bash
# GLM
curl ... -d '{"model": "glm-5", ...}'

# Kimi
curl ... -d '{"model": "kimi-k2.5", ...}'
```

## 相关页面

- 实现基类 → [anthropic-compat.md](anthropic-compat.md)
- 配置参考 → [../config.md](../config.md)
