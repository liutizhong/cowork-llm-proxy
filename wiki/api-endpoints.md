# API Endpoints

所有端点均带前缀 `/v1`，需要通过 `AuthMiddleware`（除 `/health` 和 `/`）。

---

## POST /v1/messages

创建消息，代理到对应上游提供商。

### 请求

```http
POST /v1/messages
x-api-key: <proxy_api_key>
Content-Type: application/json

{
  "model": "glm-5.1",
  "messages": [{"role": "user", "content": "你好"}],
  "max_tokens": 1024,
  "stream": false
}
```

**查询参数**：`?beta=true`（可选，客户端有时带，代理忽略）

### 响应（stream=false）

```json
{
  "id": "msg_xxx",
  "type": "message",
  "role": "assistant",
  "model": "glm-5.1",
  "content": [{"type": "text", "text": "你好！"}],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {"input_tokens": 5, "output_tokens": 10}
}
```

### 响应（stream=true）

`Content-Type: text/event-stream`，Anthropic SSE 格式：

```
event: message_start
data: {"type":"message_start","message":{...}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: ping
data: {"type":"ping"}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"你好"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"output_tokens":5}}

event: message_stop
data: {"type":"message_stop"}
```

> **DeepSeek / DashScope**：SSE 字节直接透传，格式由上游保证。
> **Ollama**：由 `OllamaProvider` 构造 Anthropic SSE 帧。

### 错误响应

```json
{
  "type": "error",
  "error": {
    "type": "not_found_error",
    "message": "No provider can handle model 'xxx'."
  }
}
```

| HTTP 状态 | error.type | 触发条件 |
|-----------|-----------|---------|
| 400 | `invalid_request_error` | body 非 JSON 或缺 model 字段 |
| 401 | `authentication_error` | API Key 缺失或错误 |
| 404 | `not_found_error` | 无 provider 匹配该 model |
| 503 | `overloaded_error` | 上游连接超时 / 读超时 |
| 503 | `api_error` | 其他上游异常 |

---

## POST /v1/messages/count_tokens

估算 token 数（存根实现，不调用上游）。

### 请求

```http
POST /v1/messages/count_tokens
x-api-key: <proxy_api_key>
Content-Type: application/json

{
  "model": "glm-5.1",
  "system": "You are helpful.",
  "messages": [{"role": "user", "content": "Hello"}]
}
```

### 响应

```json
{"input_tokens": 8}
```

**估算算法**：`max(1, total_chars // 4)`，其中 `total_chars` = system + 所有 message content 的字符数之和。

> 这是粗略估算，仅用于客户端上下文窗口预算参考，不保证精确。

---

## GET /v1/models

列出所有可用模型。

### 请求

```http
GET /v1/models
x-api-key: <proxy_api_key>
```

### 响应

```json
{
  "object": "list",
  "data": [
    {
      "type": "model",
      "id": "deepseek-v4-pro",
      "display_name": "DeepSeek - deepseek-v4-pro",
      "created_at": "2024-01-01T00:00:00Z",
      "provider": "deepseek",
      "owned_by": "deepseek"
    },
    {
      "type": "model",
      "id": "glm-5.1",
      "display_name": "Aliyun - GLM-5.1",
      "created_at": "2024-01-01T00:00:00Z",
      "provider": "dashscope",
      "owned_by": "dashscope"
    }
  ],
  "has_more": false,
  "first_id": "deepseek-v4-pro",
  "last_id": "glm-5.1"
}
```

- 若设置了 `ALLOWED_MODELS`，只返回白名单内的模型
- `object: "list"` 是 Claude Desktop 要求的字段

---

## GET /v1/models/{model_id}

获取单个模型详情。

### 响应

成功：返回单个 model 对象（同上格式）

失败：
```json
{
  "type": "error",
  "error": {"type": "not_found_error", "message": "Model 'xxx' not found."}
}
```

---

## GET /health

健康检查，无需鉴权。

```json
{"status": "ok", "providers": ["DeepSeek", "DashScope"]}
```

---

## GET /

服务信息，无需鉴权。

```json
{
  "name": "LLM Proxy",
  "version": "1.0.0",
  "endpoints": {
    "messages": "/v1/messages",
    "models": "/v1/models",
    "health": "/health",
    "docs": "/docs"
  }
}
```

---

## GET /docs

FastAPI 自动生成的 Swagger UI（仅开发环境建议开放）。
