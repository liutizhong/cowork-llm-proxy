# Log — 知识库变更日志

追加格式：`## [YYYY-MM-DD] <操作> | <标题>`

---

## [2026-04-30] init | 知识库初始化

**操作**：从代码库生成初始 wiki，涵盖全量架构知识。

**创建的页面**：
- `index.md` — 目录和项目文件树
- `overview.md` — 项目定位、解决的问题、技术选型
- `architecture.md` — 分层图、完整请求流程、Docker 网络拓扑、关键设计决策
- `providers.md` — BaseProvider / AnthropicCompatProvider / DeepSeek / DashScope / Ollama / Registry 详解
- `api-endpoints.md` — 全部 HTTP 端点的请求/响应格式
- `config.md` — 所有环境变量、pydantic-settings v2 陷阱、.env 示例
- `deployment.md` — Docker Compose、nginx 配置、多 compose 栈网络、运维命令
- `routing.md` — 路由决策树、model ID 命名规范、注意事项
- `streaming.md` — SSE 帧格式、Ollama 格式转换、nginx 流式配置
- `troubleshooting.md` — 10 个已解决 Bug（#1-#10）的根因与修复

**代码库状态**（此次 init 时）：
- 最新修复：`count_tokens` 存根端点 + 404 路由失败日志 + `forward_stream` 错误类名输出
- Provider：DeepSeek + DashScope（Ollama 可选）
- Python：3.11，FastAPI，httpx，pydantic-settings v2

---

<!-- 之后每次重要改动追加新的 ## 条目 -->
