# API 端点参考

> 相关页面：[auth.md](auth.md) · [routing.md](routing.md) · [config.md](config.md)

Base URL（本地 HTTPS）：`https://my.cowork.llm`

所有端点（除 `/health` 和 `/`）需鉴权。见 [auth.md](auth.md)。

---

## POST /v1/messages

与 [Anthropic Messages API](https://docs.anthropic.com/en/api/messages) 完全兼容。

### 请求

```http
POST /v1/messages
x-api-key: <proxy-key>
content-type: application/json
anthropic-version: 2023-06-01
```

```json
{
  "model": "deepseek-v4-pro",
  "max_tokens": 1024,
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

`model` 字段决定路由目标。见 [routing.md](routing.md)。

### 非流式响应

标准 Anthropic `Message` 对象，HTTP 200。

### 流式响应

请求体中加 `"stream": true`，响应为 `text/event-stream`（SSE）。代理做**字节级透传**，不解析 SSE 帧。

```bash
curl https://my.cowork.llm/v1/messages \
  -H "x-api-key: $PROXY_KEY" \
  -H "content-type: application/json" \
  -d '{"model": "glm-5", "max_tokens": 512, "stream": true,
       "messages": [{"role": "user", "content": "写一首诗"}]}'
```

### Token 计数（桩实现）

```http
POST /v1/messages/count_tokens
```

返回估算值（4 字符 = 1 token），非精确计算。仅供兼容性使用。

### 错误响应

| 场景 | HTTP 状态 | error.type |
|---|---|---|
| 无效 API Key | 401 | `authentication_error` |
| 模型不存在 | 404 | `not_found_error` |
| 上游超时 | 504 | `overloaded_error` |
| 上游连接失败 | 502 | `api_error` |

错误体格式：
```json
{
  "type": "error",
  "error": {
    "type": "not_found_error",
    "message": "Model not found: xxx"
  }
}
```

---

## GET /v1/models

合并所有启用提供商的模型列表。如果配置了 `ALLOWED_MODELS`，仅返回白名单内的模型。

### 响应

```json
{
  "data": [
    {
      "id": "deepseek-v4-pro",
      "object": "model",
      "owned_by": "deepseek",
      "provider": "deepseek",
      "display_name": "DeepSeek - deepseek-v4-pro"
    },
    ...
  ]
}
```

额外字段 `provider` 和 `display_name` 便于客户端区分来源，标准 Anthropic SDK 会忽略未知字段。

---

## GET /v1/models/{model_id}

查询单个模型详情。

- **200**：返回模型对象
- **404**：Anthropic 格式错误体，`type: "not_found_error"`

---

## GET /health

**无需鉴权**。返回当前注册的提供商列表，用于存活检测。

```json
{
  "status": "ok",
  "providers": ["DeepSeek", "DashScope"]
}
```

Docker health check 也调用此端点。

---

## GET /

**无需鉴权**。返回服务基本信息（版本、名称等）。

---

## 在 Claude Code 中配置

```bash
claude config set apiBaseUrl https://my.cowork.llm
claude config set apiKey sk-your-proxy-key
```

之后使用 `--model deepseek-v4-pro` 等参数即可透明路由。

## 相关页面

- 鉴权机制 → [auth.md](auth.md)
- 路由规则 → [routing.md](routing.md)
- 部署与证书 → [deployment.md](deployment.md)
