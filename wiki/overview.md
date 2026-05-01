# Overview — cowork-llm-proxy

## 项目定位

`cowork-llm-proxy` 是一个轻量级的 **Anthropic 兼容代理服务器**。它的核心价值在于：

- **统一入口**：让 Claude Desktop、Claude Code、或任何 Anthropic SDK 客户端，不改一行代码地调用 DeepSeek、阿里云 DashScope、本地 Ollama 等后端模型。
- **协议桥接**：Ollama 原生是 OpenAI-compatible 格式；本代理在服务端做 Anthropic ↔ OpenAI 格式转换，客户端无感知。
- **访问控制**：通过 `API_KEY` 对外鉴权，代理内部再用各厂商 API Key 访问上游，实现"一个代理 key 多路复用"。
- **模型聚合**：把多个提供商的模型列表合并成一个 `/v1/models` 接口，支持 `ALLOWED_MODELS` 白名单过滤。

## 解决的问题

| 痛点 | 代理的解法 |
|------|-----------|
| 不同厂商 API Key 分散，客户端配置复杂 | 客户端只需一个 `API_KEY`，厂商 Key 在服务端统一管理 |
| DeepSeek/DashScope 非标准 Anthropic 端点 | `AnthropicCompatProvider` 封装厂商差异，对外表现完全一致 |
| Ollama 使用 OpenAI 格式，Claude Desktop 不兼容 | `OllamaProvider` 做全量格式转换（含 SSE 事件映射） |
| 模型太多，不想暴露全部给客户端 | `ALLOWED_MODELS` 白名单，只展示指定模型 |
| 大模型非流式请求阻塞 | Ollama 的 `forward()` 内部始终用 streaming 采集，组装后返回 |

## 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| Web 框架 | FastAPI | 异步、自带 OpenAPI 文档、Streaming 友好 |
| HTTP 客户端 | httpx (async) | 支持流式、连接池、可配置超时 |
| 配置管理 | pydantic-settings v2 | 直接从环境变量读取并校验 |
| 反向代理 | nginx | 处理 TLS 终止、连接升级、流式超时 |
| 容器化 | Docker Compose | 与宿主机 Ollama 通过 `host.docker.internal` 互通 |

## 关键约束

- **Python ≥ 3.11**（使用了 `str.removeprefix`、`list[str]` 类型注解等特性）
- **无状态**：所有请求级状态仅在 request 生命周期内，provider 实例挂在 `app.state.registry` 上
- **不重新序列化**：DeepSeek/DashScope 的请求体直接透传，只替换 header；不做 body 解析（除了流式错误处理）
