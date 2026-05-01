# Architecture — 系统架构

## 分层图

```
┌─────────────────────────────────────────────────────────────┐
│  客户端（Claude Desktop / Claude Code / SDK）                 │
│  Anthropic Messages API（x-api-key 鉴权）                    │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/HTTPS  :80/:443
┌───────────────────────▼─────────────────────────────────────┐
│  nginx（llm-proxy-nginx）                                    │
│  ・/v1/  → proxy:8000                                        │
│  ・/     → trading-agent-frontend:80（同一 shared-proxy 网络）│
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP :8000
┌───────────────────────▼─────────────────────────────────────┐
│  FastAPI App（llm-proxy）                                    │
│  ┌─────────────┐  ┌──────────────────────────────────────┐  │
│  │ AuthMiddle  │  │ ProviderRegistry                     │  │
│  │ ware        │  │  ┌────────────┐ ┌──────────────────┐ │  │
│  │ (hmac check)│  │  │DeepSeek    │ │DashScope         │ │  │
│  └─────────────┘  │  │Provider    │ │Provider          │ │  │
│                   │  └────────────┘ └──────────────────┘ │  │
│  ┌─────────────┐  │  ┌────────────┐                      │  │
│  │ /v1/messages│  │  │Ollama      │                      │  │
│  │ /v1/models  │  │  │Provider    │                      │  │
│  └─────────────┘  │  └────────────┘                      │  │
│                   └──────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼──────────────────┐
          ▼               ▼                  ▼
   api.deepseek.com  dashscope.aliyuncs.com  host.docker.internal:11434
   (Anthropic-compat) (Anthropic-compat)     (Ollama OpenAI-compat)
```

## 请求完整流程（POST /v1/messages）

```
1. 客户端发送请求
   POST /v1/messages
   headers: { x-api-key: <proxy_key> }
   body:    { model: "glm-5.1", messages: [...], stream: true }

2. nginx 透传到 proxy:8000
   - proxy_buffering off（流式关键）
   - proxy_read_timeout 300s

3. AuthMiddleware.dispatch()
   - 检查 x-api-key 或 Authorization: Bearer
   - hmac.compare_digest 对比 settings.api_key
   - 失败 → 401；成功 → call_next

4. POST /v1/messages 路由到 create_message()
   - 解析 body.model = "glm-5.1"
   - registry.route("glm-5.1") → DashScopeProvider（因为 "glm-" 前缀匹配）

5a. stream=True 分支
   - 返回 StreamingResponse(provider.forward_stream(...))
   - DashScopeProvider.forward_stream() 向 dashscope 发 POST
   - 将 dashscope 返回的 SSE 字节流原样 yield 给客户端

5b. stream=False 分支
   - await provider.forward(...)
   - 等待完整 JSON 响应后返回 JSONResponse

6. 错误处理
   - httpx.ConnectTimeout → 503 overloaded_error
   - httpx.ReadTimeout    → 503 overloaded_error
   - 其他 Exception       → 503 api_error（含类名方便调试）
```

## 模型列表流程（GET /v1/models）

```
1. GET /v1/models
2. AuthMiddleware 鉴权
3. registry.list_all_models()
   - 遍历所有 provider，调用 provider.list_models()
   - 各 provider 有 5 分钟内存缓存（asyncio.Lock 保护）
   - 去重（按 model id）
4. 若 settings.allowed_models 非空，过滤白名单
5. 返回 { object: "list", data: [...], first_id, last_id }
```

## Docker 网络拓扑

```
┌─────────────────── default network ───────────────────────┐
│  proxy (llm-proxy :8000)                                  │
│  nginx  (llm-proxy-nginx :80/:443)                        │
└───────────────────────────────────────────────────────────┘
         ↕ shared-proxy (external network)
┌─────────────────── shared-proxy ──────────────────────────┐
│  nginx（本项目）                                           │
│  trading-agent-frontend:80                                │
│  ... 其他 compose 栈的服务 ...                             │
└───────────────────────────────────────────────────────────┘

proxy → host Ollama：host.docker.internal:11434
  （docker-compose extra_hosts: host.docker.internal:host-gateway）
```

## 关键设计决策

### 1. AnthropicCompatProvider 直接透传 body
DeepSeek 和 DashScope 都有 Anthropic-compatible 端点，body 格式与 Anthropic 一致，无需转换。只替换 header（x-api-key / Authorization）。

### 2. OllamaProvider 做完整格式转换
Ollama 只有 OpenAI-compat 接口。需要：
- 请求：Anthropic body → OpenAI chat/completions body
- 响应：OpenAI response → Anthropic message response
- 流式：OpenAI SSE chunks → Anthropic SSE events（message_start / content_block_delta / message_stop 等）

### 3. OllamaProvider.forward() 内部用流式
即使客户端请求 `stream=false`，`OllamaProvider.forward()` 也向 Ollama 发流式请求，在本地聚合。原因：Ollama 是单线程 HTTP 服务，非流式大模型请求会阻塞整个进程，导致超时。

### 4. forward_stream 内不做异步 HTTP 调用
`forward_stream` 是 `AsyncGenerator`。在 generator 内部发起 `await httpx...` 会与外层 httpx 流共享连接池，触发 TLS upgrade 错误。Ollama 的模型名解析改为同步 dict 查询（`_id_to_name`）。
