# 鉴权机制

> 相关页面：[architecture.md](architecture.md) · [config.md](config.md) · [api.md](api.md)

源文件：`app/auth.py`

## 机制概述

`AuthMiddleware` 是一个 Starlette 中间件，在请求到达路由层之前验证 API Key。

## 免鉴权路径

以下路径不做鉴权，任何请求直接放行：

- `GET /health`
- `GET /`

## Key 读取顺序

中间件按以下优先级从请求头中读取 Key：

1. `x-api-key: <key>` 头
2. `Authorization: Bearer <key>` 头（提取 Bearer 后面的部分）

两者都未提供时，返回 401。

## 时序安全比较

```python
import hmac
hmac.compare_digest(provided_key, settings.API_KEY)
```

使用 `hmac.compare_digest` 而非 `==` 做字符串比较，防止**时序攻击**（通过比较耗时推断 Key 的字符内容）。

## 401 响应格式

鉴权失败时返回 Anthropic 格式的错误体：

```json
{
  "type": "error",
  "error": {
    "type": "authentication_error",
    "message": "Invalid API key"
  }
}
```

HTTP 状态码：`401 Unauthorized`。

## 禁用鉴权

内网环境下可关闭鉴权：

```
REQUIRE_AUTH=false
```

> **警告**：禁用鉴权后，任何能访问代理地址的人都可以直接调用上游 API，消耗上游额度。仅在完全隔离的内网环境下使用。

## 相关页面

- 配置 `API_KEY` 和 `REQUIRE_AUTH` → [config.md](config.md)
- 整体请求流程 → [architecture.md](architecture.md)
