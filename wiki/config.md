# 配置参考

> 相关页面：[deployment.md](deployment.md) · [auth.md](auth.md) · [providers/deepseek.md](providers/deepseek.md) · [providers/dashscope.md](providers/dashscope.md) · [providers/ollama.md](providers/ollama.md)

源文件：`app/config.py`（pydantic-settings）

所有配置通过 `.env` 文件或环境变量注入。`.env` 优先级低于实际环境变量。

```bash
cp .env.example .env
# 编辑 .env 填入实际 Key
```

---

## 代理核心

| 变量 | 默认值 | 说明 |
|---|---|---|
| `API_KEY` | **必填** | 对外暴露的代理 Key，客户端用此 Key 访问代理 |
| `REQUIRE_AUTH` | `true` | 设为 `false` 可关闭鉴权（内网使用） |

---

## DeepSeek

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ENABLE_DEEPSEEK` | `false` | 启用 DeepSeek 提供商 |
| `DEEPSEEK_API_KEY` | — | DeepSeek 官方 API Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/anthropic` | 推理端点（可覆盖为私有化部署地址） |
| `DEEPSEEK_MODELS_URL` | `https://api.deepseek.com/models` | 模型列表端点 |

启用条件：`ENABLE_DEEPSEEK=true` **且** `DEEPSEEK_API_KEY` 非空。

---

## DashScope（阿里云）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ENABLE_DASHSCOPE` | `false` | 启用 DashScope 提供商 |
| `DASHSCOPE_API_KEY` | — | 阿里云 DashScope API Key |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com/apps/anthropic` | 推理端点 |
| `DASHSCOPE_MODELS_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1/models` | 模型列表端点 |

---

## Ollama（本地）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ENABLE_OLLAMA` | `false` | 启用 Ollama 提供商 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 地址；Docker 容器内需改为 `http://host.docker.internal:11434` |

---

## 模型白名单

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ALLOWED_MODELS` | （空，暴露全部） | 逗号分隔的模型 ID 白名单；设置后 `/v1/models` 只返回白名单内的模型，路由不受影响 |

示例：`ALLOWED_MODELS=deepseek-v4-pro,glm-5,kimi-k2.5`

---

## 服务器

| 变量 | 默认值 | 说明 |
|---|---|---|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |
| `WORKERS` | `2` | uvicorn worker 数量 |
| `LOG_LEVEL` | `INFO` | 日志级别（DEBUG / INFO / WARNING / ERROR） |
| `TIMEOUT` | `300` | 上游请求超时（秒）；长文本生成建议保持默认或调高 |

---

## 相关页面

- 鉴权配置 → [auth.md](auth.md)
- 部署时的配置文件位置 → [deployment.md](deployment.md)
- 添加新提供商时的配置扩展 → [extending.md](extending.md)
