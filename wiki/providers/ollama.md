# Ollama Provider

> 相关页面：[base.md](base.md) · [../config.md](../config.md) · [../routing.md](../routing.md)

源文件：`app/providers/ollama.py`

## 基本信息

| 项目 | 值 |
|---|---|
| 类名 | `OllamaProvider` |
| 继承自 | `BaseProvider`（**不**继承 `AnthropicCompatProvider`） |
| `name` | `"Ollama"` |
| `display_prefix` | `"Ollama - "` |
| API Key | 不需要 |

## 为什么独立实现

Ollama 暴露 **OpenAI 兼容格式**，而非 Anthropic 格式。无法用 `AnthropicCompatProvider` 的透传逻辑，必须独立实现双向格式转换。

## 路由规则

```python
def can_handle(self, model_id: str) -> bool:
    return model_id.lower().startswith("ollama-")
```

## 模型 ID 安全化

Ollama 原生模型名包含 `/` 和 `:` 等不安全字符（如 `llama3.2:latest`、`mistral:7b-instruct`）。`OllamaProvider` 在 `list_models()` 时做映射：

```
原生名称              → 安全 ID
llama3.2:latest       → ollama-llama3-2-latest
mistral:7b-instruct   → ollama-mistral-7b-instruct
```

转换规则：`ollama-` 前缀 + 将 `.` 和 `:` 替换为 `-`。

内部维护 `_id_to_name: dict[str, str]`，`forward()` 时从安全 ID 还原为原生名称。

## 格式转换：Anthropic → OpenAI（请求）

`POST /v1/messages` 的 Anthropic 请求体转换为 OpenAI `/api/chat` 请求体：

| Anthropic 字段 | OpenAI 字段 | 说明 |
|---|---|---|
| `model` | `model` | 还原为 Ollama 原生名称 |
| `messages` | `messages` | 基本兼容，system message 提取处理 |
| `system` | `messages[0]` (role=system) | Anthropic 的顶层 `system` 插入为首条消息 |
| `max_tokens` | `options.num_predict` | |
| `temperature` | `options.temperature` | |
| `stream` | `stream` | |

## 格式转换：OpenAI → Anthropic（响应）

**非流式响应**：

| OpenAI 字段 | Anthropic 字段 |
|---|---|
| `choices[0].message.content` | `content[0].text` |
| `usage.prompt_tokens` | `usage.input_tokens` |
| `usage.completion_tokens` | `usage.output_tokens` |

组装为标准 Anthropic `Message` 对象（`type: "message"`）。

**流式响应**：OpenAI SSE (`data: {"choices":[{"delta":...}]}`) 转换为 Anthropic SSE 格式：

```
event: message_start
data: {...}

event: content_block_delta
data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"..."}}

event: message_stop
data: {}
```

## 模型列表

动态从 Ollama `/api/tags` 获取，**无缓存**（Ollama 是本地服务，启动慢的不是网络而是模型加载）。

## 端点配置

| 配置项 | 默认值 | Docker 内推荐 | 环境变量 |
|---|---|---|---|
| Base URL | `http://localhost:11434` | `http://host.docker.internal:11434` | `OLLAMA_BASE_URL` |

`host.docker.internal` 由 `docker-compose.yml` 的 `extra_hosts: host.docker.internal:host-gateway` 解析到宿主机。

## 已知限制

- **不支持所有 Anthropic 特性**：`tools`、`thinking`、`vision` 等高级特性取决于 Ollama 版本和具体模型支持情况，不保证兼容。
- **无 API Key 验证**：本地 Ollama 无需认证，代理层也不做额外验证。

## 相关页面

- 接口定义 → [base.md](base.md)
- 配置参考 → [../config.md](../config.md)
- 部署（Docker 访问宿主机 Ollama）→ [../deployment.md](../deployment.md)
