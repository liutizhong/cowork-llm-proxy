# 项目概览

> 相关页面：[architecture.md](architecture.md) · [routing.md](routing.md)

## 问题背景

多家优秀的 LLM 服务商（DeepSeek、阿里云通义/GLM/Kimi、Minimax）都提供了 **Anthropic 兼容端点**，可以直接用 Claude SDK 调用。但直接使用有两个痛点：

1. **多套密钥管理**：每个使用方（开发者本机、团队成员、CI）都要配置多个上游 API Key，泄露风险高。
2. **频繁切换配置**：切换模型提供商需要改 `apiBaseUrl` + `apiKey`，打断工作流。

## 解决方案

**bmg-llm-proxy** 在客户端和上游之间加一层轻代理：

```
客户端 (Claude Code / 任何 Anthropic SDK)
    │  apiBaseUrl = https://my.cowork.llm
    │  apiKey     = sk-your-proxy-key        ← 只需管理这一个 Key
    ▼
bmg-llm-proxy
    │  model="deepseek-v4-pro"  →  DeepSeek API  (用 DEEPSEEK_API_KEY)
    │  model="glm-5"            →  DashScope API  (用 DASHSCOPE_API_KEY)
    │  model="ollama/llama3.2"  →  本地 Ollama    (无需 Key)
    ▼
各上游服务
```

客户端永远只看到一个地址、一个 Key。**切换模型只需改 `--model` 参数**，其他不变。

## 设计哲学

**最小化代理**：不做请求体转换（Ollama 例外，因为格式完全不同），不做缓存，不做重试。职责单一：鉴权 + 路由 + 透传。

**Anthropic API 优先**：假设所有上游都支持 Anthropic Messages API 格式。不支持的上游（Ollama）在 Provider 层自行处理格式转换，对路由层透明。

**配置驱动**：所有行为通过 `.env` 控制，无需改代码。提供商按需启用/禁用。

**可扩展性**：添加新提供商只需新建一个 Python 文件 + 继承基类，约 20 行代码。见 [extending.md](extending.md)。

## 技术选型

| 技术 | 选择 | 原因 |
|---|---|---|
| Web 框架 | FastAPI + uvicorn | 原生异步，SSE 流式响应无需额外封装 |
| HTTP 客户端 | httpx (async) | 支持流式 `.stream()` 上下文管理器 |
| 配置管理 | pydantic-settings | 类型安全，自动读取 `.env` |
| 反向代理 | Caddy | `tls internal` 一行搞定本地 HTTPS |
| 容器化 | Docker Compose | 多服务一键启动，`extra_hosts` 打通宿主机 Ollama |

## 相关页面

- 架构细节 → [architecture.md](architecture.md)
- 路由机制 → [routing.md](routing.md)
- 部署指南 → [deployment.md](deployment.md)
