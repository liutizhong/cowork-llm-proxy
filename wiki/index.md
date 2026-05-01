# bmg-llm-proxy Wiki — 索引

> 本 wiki 是项目知识的持久化汇集点。每个页面聚焦一个概念，页面之间通过链接相互关联。

---

## 核心概念

| 页面 | 摘要 |
|---|---|
| [overview.md](overview.md) | 项目存在的原因、解决的问题、设计哲学 |
| [architecture.md](architecture.md) | 整体分层架构、模块职责、启动流程 |
| [routing.md](routing.md) | 请求如何从模型 ID 路由到对应提供商 |

## 提供商

| 页面 | 摘要 |
|---|---|
| [providers/base.md](providers/base.md) | `BaseProvider` 抽象接口定义 |
| [providers/anthropic-compat.md](providers/anthropic-compat.md) | 通用 HTTP 代理实现，DeepSeek/DashScope 的基类 |
| [providers/deepseek.md](providers/deepseek.md) | DeepSeek 提供商：路由规则、端点、模型列表 |
| [providers/dashscope.md](providers/dashscope.md) | 阿里云 DashScope：多模型家族的统一入口 |
| [providers/ollama.md](providers/ollama.md) | 本地 Ollama：Anthropic ↔ OpenAI 格式双向转换 |

## 参考

| 页面 | 摘要 |
|---|---|
| [auth.md](auth.md) | API Key 鉴权中间件：验证逻辑、时序安全比较 |
| [config.md](config.md) | 所有环境变量的完整参考 |
| [api.md](api.md) | HTTP 端点规格：请求/响应格式、错误体 |
| [deployment.md](deployment.md) | Docker Compose、Caddy HTTPS、本地证书信任 |
| [extending.md](extending.md) | 如何添加新提供商的分步指南 |

## 元

| 页面 | 摘要 |
|---|---|
| [log.md](log.md) | 变更与摄入记录（时序追加） |

---

*最后更新：2026-05-01*
