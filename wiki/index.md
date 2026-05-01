# cowork-llm-proxy Wiki — Index

> 这是项目的持久化知识库，由 LLM 维护。所有页面均由 Claude 生成并持续更新。
> 最后更新：2026-04-30

## 快速导航

| 页面 | 一句话摘要 |
|------|-----------|
| [overview](overview.md) | 项目定位、解决的问题、整体思路 |
| [architecture](architecture.md) | 系统分层图、请求完整流程、各层职责 |
| [providers](providers.md) | Provider 体系：BaseProvider / AnthropicCompatProvider / Ollama / DeepSeek / DashScope |
| [api-endpoints](api-endpoints.md) | 所有 HTTP 端点的请求/响应格式 |
| [config](config.md) | 所有环境变量、`.env` 示例、pydantic-settings 注意事项 |
| [deployment](deployment.md) | Docker Compose 部署、nginx 配置、多 compose 栈网络 |
| [routing](routing.md) | 请求路由决策树、model ID 命名规范、can_handle 逻辑 |
| [streaming](streaming.md) | SSE 帧格式、Ollama 流式内部实现、nginx 流式配置 |
| [troubleshooting](troubleshooting.md) | 已遇到并解决的 Bug 清单，含根因与修复方式 |
| [log](log.md) | 追加日志（知识库的变更历史） |

## 目录结构速览

```
cowork-llm-proxy/
├── app/
│   ├── main.py               # FastAPI 入口 + lifespan
│   ├── config.py             # pydantic-settings Settings
│   ├── auth.py               # AuthMiddleware（Bearer / x-api-key）
│   ├── api/
│   │   ├── messages.py       # POST /v1/messages, /v1/messages/count_tokens
│   │   └── models.py         # GET /v1/models, GET /v1/models/{id}
│   └── providers/
│       ├── base.py           # BaseProvider ABC
│       ├── registry.py       # ProviderRegistry + build_registry()
│       ├── anthropic_compat.py  # AnthropicCompatProvider（DeepSeek/DashScope 基类）
│       ├── deepseek.py       # DeepSeekProvider
│       ├── dashscope.py      # DashScopeProvider
│       └── ollama.py         # OllamaProvider（Anthropic↔OpenAI 格式转换）
├── nginx/nginx.conf          # 反向代理 + 流式超时配置
├── docker-compose.yml        # proxy + nginx 服务
├── Dockerfile                # python:3.11，2 workers
└── wiki/                     # 本知识库
```
