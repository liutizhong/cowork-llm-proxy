# 系统架构

> 相关页面：[overview.md](overview.md) · [routing.md](routing.md) · [auth.md](auth.md)

## 目录结构

```
app/
├── main.py                  # FastAPI 应用入口
├── config.py                # 全局配置（pydantic-settings）
├── auth.py                  # API Key 鉴权中间件
├── api/
│   ├── messages.py          # POST /v1/messages
│   └── models.py            # GET  /v1/models
└── providers/
    ├── base.py              # BaseProvider 抽象类
    ├── registry.py          # ProviderRegistry
    ├── anthropic_compat.py  # 通用 HTTP 代理基类
    ├── deepseek.py          # DeepSeek
    ├── dashscope.py         # 阿里云 DashScope
    └── ollama.py            # 本地 Ollama
```

## 分层模型

```
┌────────────────────────────────────────┐
│  客户端 (Claude Code / curl / SDK)     │
└──────────────────┬─────────────────────┘
                   │ HTTPS (Caddy TLS 终止)
┌──────────────────▼─────────────────────┐
│           CORSMiddleware               │
│           AuthMiddleware               │  ← app/auth.py
│                                        │
│  POST /v1/messages  GET /v1/models     │  ← app/api/
│                                        │
│         ProviderRegistry               │  ← app/providers/registry.py
│    ┌────────┬──────────┬────────┐      │
│  DeepSeek DashScope  Ollama   ...      │  ← app/providers/
└────────────────────────────────────────┘
                   │
         上游 LLM API / 本地 Ollama
```

## 启动流程

`main.py` 的 lifespan 上下文管理器在应用启动时调用 `build_registry()`：

1. 读取 `settings`（来自 `.env`）
2. 按启用标志依次实例化各 Provider
3. 将 `ProviderRegistry` 存入 `app.state.registry`
4. 路由层通过 `request.app.state.registry` 获取

## 请求生命周期

```
POST /v1/messages
  │
  ├─ CORSMiddleware        添加 CORS 响应头
  ├─ AuthMiddleware        验证 x-api-key / Bearer token
  │
  ├─ messages.router
  │   ├─ 解析请求体 JSON
  │   ├─ 提取 model 字段
  │   └─ registry.route(model_id)  → Provider
  │
  ├─ provider.forward()            非流式：等待完整响应返回
  └─ provider.forward_stream()     流式：yield bytes，直接 SSE 透传
```

## 关键设计决策

**`app.state` 存储 Registry**：避免全局变量，Registry 生命周期绑定 ASGI 应用实例，便于测试时替换。

**纯 HTTP 代理（不用 SDK）**：`AnthropicCompatProvider` 直接用 httpx 转发原始请求体，不经过 Anthropic Python SDK。好处：零依赖、完整保留 `anthropic-beta` 等扩展头、流式响应字节级透传无损。

**流式响应的字节透传**：`forward_stream()` 使用 `httpx.AsyncClient.stream()` + `StreamingResponse(content=...)` 直接 yield 原始字节，不做 JSON 解析/重序列化，延迟最低。

**Ollama 格式转换隔离**：格式转换完全封装在 `OllamaProvider` 内部，路由层和 API 层对此无感知。见 [providers/ollama.md](providers/ollama.md)。

## 相关页面

- 路由详情 → [routing.md](routing.md)
- 鉴权机制 → [auth.md](auth.md)
- 各 Provider 实现 → [providers/](providers/base.md)
