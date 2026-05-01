# 变更日志

> 追加式记录。每次摄入、重要变更或决策都在此留档。

---

## 2026-05-01 — Wiki 初始化

- 基于项目源码（`app/`）、`README.md`、`docker-compose.yml`、`Caddyfile` 完成首次 wiki 摄入
- 生成页面：overview、architecture、routing、auth、config、api、deployment、extending
- 生成提供商页面：base、anthropic-compat、deepseek、dashscope、ollama
- 关键发现：
  - Ollama provider 不继承 `AnthropicCompatProvider`，独立实现双向格式转换
  - 模型缓存为 per-provider 5 分钟内存缓存，多 worker 独立缓存
  - `hmac.compare_digest` 用于时序安全的 API Key 比较

---

<!-- 后续变更追加在此处 -->
