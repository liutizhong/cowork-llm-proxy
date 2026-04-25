# cowork-llm-proxy Wiki

一个轻量级的 Anthropic API 兼容代理，将 Claude SDK 的请求透明转发到 DeepSeek、阿里云 DashScope 等后端，无需修改客户端代码。

---

## 核心思路

市面上很多优秀的 LLM（DeepSeek、通义千问、Kimi、GLM 等）都提供了 Anthropic 兼容的 API 端点，但各家的 API Key、Base URL 各不相同。直接在客户端（如 Claude Code、Continue.dev）切换既麻烦又不安全——API Key 需要分发给每个使用方。

bmg-llm-proxy 在中间层做一件事：**用你自己的 API Key 对外暴露一个统一的 Anthropic 端点**，在内部按模型 ID 前缀路由到正确的上游提供商，并用上游提供商的 Key 转发请求。客户端永远只看到一个地址、一个 Key。

```
客户端 (Claude Code / curl)
        │  x-api-key: sk-your-proxy-key
        ▼
  https://my.cowork.llm/v1/messages
        │
  ┌─────▼──────────────────────────┐
  │        bmg-llm-proxy           │
  │   AuthMiddleware → Registry    │
  │   model="deepseek-v4-pro" ──► DeepSeekProvider ──► api.deepseek.com
  │   model="glm-5"           ──► DashScopeProvider ──► dashscope.aliyuncs.com
  └────────────────────────────────┘
```

---

## 架构

### 层次结构

```
app/
├── main.py              # FastAPI 应用入口，挂载路由和中间件
├── config.py            # 所有配置项（pydantic-settings，读取 .env）
├── auth.py              # API Key 鉴权中间件
├── api/
│   ├── messages.py      # POST /v1/messages
│   └── models.py        # GET  /v1/models
└── providers/
    ├── base.py          # BaseProvider 抽象类
    ├── anthropic_compat.py  # 通用 Anthropic 兼容实现（HTTP 纯代理）
    ├── deepseek.py      # DeepSeek 提供商
    ├── dashscope.py     # 阿里云 DashScope 提供商
    └── registry.py      # ProviderRegistry：注册 + 路由
```

### 核心组件

**ProviderRegistry** — 启动时构建，存在 `app.state.registry`。按注册顺序遍历提供商，第一个 `can_handle(model_id)` 返回 True 的提供商负责处理请求。

**AnthropicCompatProvider** — 所有提供商的通用基类实现。不使用任何 SDK，直接用 `httpx` 做纯 HTTP 代理，保留原始请求体和 Anthropic 专属 Header（`anthropic-version`、`anthropic-beta`）。模型列表有 5 分钟内存缓存，避免频繁请求上游。

**AuthMiddleware** — Starlette 中间件，对除 `/health` 和 `/` 之外的所有路径验证 API Key。接受两种格式：
- `x-api-key: <key>`
- `Authorization: Bearer <key>`

使用 `hmac.compare_digest` 做时序安全比较，防止时序攻击。

---

## 提供商

### DeepSeek

| 项目 | 值 |
|---|---|
| 模型路由规则 | `model_id.lower().startswith("deepseek-")` |
| 默认推理端点 | `https://api.deepseek.com/anthropic` |
| 默认模型列表 | `https://api.deepseek.com/models` |
| 内置 fallback 模型 | `deepseek-v4-flash`, `deepseek-v4-pro` |
| display_name 前缀 | `DeepSeek - ` |

### DashScope（阿里云）

路由前缀匹配：`glm-`、`kimi-`、`minimax-`、`qwen-`

| 项目 | 值 |
|---|---|
| 默认推理端点 | `https://dashscope.aliyuncs.com/apps/anthropic` |
| 默认模型列表 | `https://dashscope.aliyuncs.com/compatible-mode/v1/models` |
| 内置 fallback 模型 | `glm-5`, `glm-5.1`, `glm-4.7`, `kimi-k2.5`, `minimax-m2.5` |
| display_name 前缀 | `Aliyun - ` |

---

## API 端点

### `POST /v1/messages`

与 Anthropic Messages API 完全兼容。请求体原样转发至上游，SSE 流式响应原样回传（无重新序列化）。

```bash
curl https://my.cowork.llm/v1/messages \
  -H "x-api-key: sk-your-proxy-key" \
  -H "content-type: application/json" \
  -d '{
    "model": "deepseek-v4-pro",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

流式：在请求体加 `"stream": true`，响应为 `text/event-stream`。

### `GET /v1/models`

合并所有启用提供商的模型列表，去重后返回。如果设置了 `ALLOWED_MODELS`，仅返回白名单中的模型。

```bash
curl https://my.cowork.llm/v1/models \
  -H "x-api-key: sk-your-proxy-key"
```

返回格式与 Anthropic `/v1/models` 兼容，额外包含 `provider` 和 `owned_by` 字段。

### `GET /v1/models/{model_id}`

查询单个模型详情，404 时返回 Anthropic 格式的错误体。

### `GET /health`

无需鉴权，返回当前已注册的提供商列表：

```json
{"status": "ok", "providers": ["DeepSeek", "DashScope"]}
```

---

## 配置

所有配置通过 `.env` 文件或环境变量注入，无需修改代码。

```bash
# 复制示例文件
cp .env.example .env
```

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `API_KEY` | **必填** | 对外暴露的代理 Key |
| `REQUIRE_AUTH` | `true` | 设为 `false` 可关闭鉴权（内网使用） |
| `ENABLE_DEEPSEEK` | `false` | 启用 DeepSeek |
| `DEEPSEEK_API_KEY` | — | DeepSeek 官方 Key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/anthropic` | 可覆盖为私有化部署地址 |
| `ENABLE_DASHSCOPE` | `false` | 启用阿里云 DashScope |
| `DASHSCOPE_API_KEY` | — | DashScope Key |
| `ALLOWED_MODELS` | （空，暴露全部） | 逗号分隔的模型 ID 白名单 |
| `WORKERS` | `2` | uvicorn worker 数量 |
| `TIMEOUT` | `300` | 上游请求超时（秒） |
| `LOG_LEVEL` | `INFO` | 日志级别 |

---

## 部署

### Docker Compose（推荐）

```bash
cp .env.example .env
# 编辑 .env，填入 API Key
docker compose up -d
```

服务暴露在 `http://localhost:8000`。

### 本地 HTTPS + 自定义域名（my.cowork.llm）

项目已内置 Caddy 反向代理配置，通过 `tls internal` 自动签发本地受信证书。

**步骤：**

1. 修改 hosts 文件，添加域名解析：

   **Windows**（`C:\Windows\System32\drivers\etc\hosts`）：
   ```
   127.0.0.1 my.cowork.llm
   ```

   **macOS / Linux**：
   ```bash
   sudo sh -c 'echo "127.0.0.1 my.cowork.llm" >> /etc/hosts'
   ```

2. 启动所有服务（包含 Caddy）：
   ```bash
   docker compose up -d
   ```

3. 导出 Caddy 根证书：
   ```bash
   docker cp llm-proxy-caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
   ```

4. 信任证书（按操作系统操作）：

   **Windows**：双击 `caddy-root.crt` → 安装证书 → 本地计算机 → **受信任的根证书颁发机构**。

   **macOS**：
   ```bash
   sudo security add-trusted-cert -d -r trustRoot \
     -k /Library/Keychains/System.keychain ./caddy-root.crt
   ```
   之后重启浏览器生效。撤销信任：
   ```bash
   sudo security delete-certificate -c "Caddy Local Authority" \
     /Library/Keychains/System.keychain
   ```

   **Linux（Debian/Ubuntu）**：
   ```bash
   sudo cp caddy-root.crt /usr/local/share/ca-certificates/caddy-root.crt
   sudo update-ca-certificates
   ```

5. 验证：
   ```bash
   curl -v https://my.cowork.llm/health
   ```
   访问 `https://my.cowork.llm`，浏览器无警告。

**服务端口分配：**

| 容器 | 对外端口 | 用途 |
|---|---|---|
| `llm-proxy` | 8000 | FastAPI（仅内部，被 Caddy 反代） |
| `llm-proxy-caddy` | 80, 443 | HTTP → HTTPS 重定向 + TLS 终止 |

---

## 在 Claude Code 中使用

将代理地址配置为 Anthropic API Base URL：

```bash
# 在项目 .claude/settings.json 或全局设置中
claude config set apiBaseUrl https://my.cowork.llm
claude config set apiKey sk-your-proxy-key
```

之后 `claude` 命令使用 `--model deepseek-v4-pro` 或 `--model glm-5` 即可透明路由到对应上游。

---

## 添加新提供商

1. 在 `app/providers/` 新建文件，继承 `AnthropicCompatProvider`：

```python
from ..config import settings
from .anthropic_compat import AnthropicCompatProvider

class MyProvider(AnthropicCompatProvider):
    _name = "MyProvider"
    _display_prefix = "My - "
    _default_models = [
        {"id": "my-model-v1", "owned_by": "myprovider", "provider": "myprovider", "display_name": "My Model V1"},
    ]

    def __init__(self) -> None:
        super().__init__()
        self._api_key = settings.my_api_key      # 在 config.py 中添加对应字段
        self._base_url = settings.my_base_url
        self._models_url = settings.my_models_url

    def can_handle(self, model_id: str) -> bool:
        return model_id.lower().startswith("my-")
```

2. 在 `app/config.py` 添加对应的配置字段。

3. 在 `app/providers/registry.py` 的 `build_registry()` 中注册：

```python
if settings.enable_my_provider and settings.my_api_key:
    registry.register(MyProvider())
```

4. 在 `.env.example` 补充新变量。

无需修改路由层、鉴权层或任何现有代码。

---

## 请求流程（逐步）

```
1. 客户端发送 POST /v1/messages
2. CORSMiddleware：添加跨域响应头
3. AuthMiddleware：验证 x-api-key / Bearer token
4. messages.router：解析请求体，提取 model 字段
5. registry.route(model)：遍历提供商，找到第一个 can_handle=True 的
6. provider.forward() 或 provider.forward_stream()：
   - 替换 Authorization 头为上游 Key
   - 保留 anthropic-version / anthropic-beta
   - httpx 转发到上游端点
7. 响应原样返回给客户端（流式：直接 yield bytes）
```

---

## 已知限制

- **无请求体转换**：代理假设上游支持完整的 Anthropic Messages API。如果上游对某些字段有不兼容之处，需在 Provider 层手动处理。
- **无重试**：上游失败直接返回错误，不做重试或熔断。
- **模型缓存共享**：同一进程内所有请求共享同一份模型列表缓存（per-provider），多 worker 场景下各 worker 独立缓存。
- **无请求日志持久化**：日志仅输出到 stdout，生产环境需配合日志收集器使用。
