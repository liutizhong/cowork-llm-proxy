# Config — 配置参考

**文件**：`app/config.py`，使用 `pydantic-settings v2`，从 `.env` 文件和环境变量中读取。

---

## 完整变量表

### 代理鉴权

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `API_KEY` | `str` | 必填 | 客户端使用的 API Key，代理对外鉴权 |
| `REQUIRE_AUTH` | `bool` | `true` | `false` 则跳过鉴权（仅内网开发用） |

### DeepSeek

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ENABLE_DEEPSEEK` | `bool` | `false` | 是否启用 |
| `DEEPSEEK_API_KEY` | `str` | `""` | DeepSeek 官方 API Key，为空则即使 ENABLE=true 也不注册 |
| `DEEPSEEK_BASE_URL` | `str` | `https://api.deepseek.com/anthropic` | Anthropic-compat 推理端点 |
| `DEEPSEEK_MODELS_URL` | `str` | `https://api.deepseek.com/models` | OpenAI-compat 模型列表端点 |

### DashScope（阿里云）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ENABLE_DASHSCOPE` | `bool` | `false` | 是否启用 |
| `DASHSCOPE_API_KEY` | `str` | `""` | 阿里云 DashScope API Key |
| `DASHSCOPE_BASE_URL` | `str` | `https://dashscope.aliyuncs.com/apps/anthropic` | |
| `DASHSCOPE_MODELS_URL` | `str` | `https://dashscope.aliyuncs.com/compatible-mode/v1/models` | |

### Ollama（本地）

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ENABLE_OLLAMA` | `bool` | `false` | 是否启用 |
| `OLLAMA_BASE_URL` | `str` | `http://localhost:11434` | **Docker 内**应改为 `http://host.docker.internal:11434` |

### 模型白名单

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ALLOWED_MODELS` | `str`（CSV）| `""` | 留空则暴露所有模型；填写则只展示这些 |

示例：
```
ALLOWED_MODELS=deepseek-v4-pro,deepseek-v4-flash,glm-5,kimi-k2.5,glm-5.1
```

### 服务器参数

| 变量 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `HOST` | `str` | `0.0.0.0` | uvicorn 绑定地址 |
| `PORT` | `int` | `8000` | uvicorn 端口 |
| `WORKERS` | `int` | `2` | uvicorn worker 进程数 |
| `LOG_LEVEL` | `str` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `TIMEOUT` | `int` | `300` | httpx 读取超时秒数（connect 超时单独设为 10s） |

---

## pydantic-settings v2 陷阱

### ALLOWED_MODELS 字段类型

**问题**：若将 `allowed_models` 定义为 `list[str]`，pydantic-settings v2 会在调用 `@field_validator` 之前尝试将 CSV 字符串 JSON 解析为列表，导致：

```
SettingsError: error parsing value for field "allowed_models" from source "EnvSettingsSource"
```

**解决方案**：改为 `str` 字段 + `@property`，绕过自动 JSON 解析：

```python
# 正确写法
allowed_models_raw: str = Field(default="", alias="ALLOWED_MODELS")

@property
def allowed_models(self) -> list[str]:
    v = self.allowed_models_raw.strip()
    return [m.strip() for m in v.split(",") if m.strip()] if v else []
```

这样 `settings.allowed_models` 返回 `list[str]`，对外接口不变。

---

## .env 示例

```ini
# 代理鉴权
API_KEY=sk-your-proxy-key-here
REQUIRE_AUTH=true

# DeepSeek
ENABLE_DEEPSEEK=true
DEEPSEEK_API_KEY=sk-...

# DashScope
ENABLE_DASHSCOPE=true
DASHSCOPE_API_KEY=sk-...

# Ollama（Docker 内访问宿主机）
ENABLE_OLLAMA=false
OLLAMA_BASE_URL=http://host.docker.internal:11434

# 只暴露这几个模型
ALLOWED_MODELS=deepseek-v4-pro,deepseek-v4-flash,glm-5,kimi-k2.5,glm-5.1

# 服务器
TIMEOUT=300
LOG_LEVEL=INFO
```

---

## nginx 端口环境变量

这两个变量在 `docker-compose.yml` 中使用，不由 FastAPI 读取：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `NGINX_HTTP_PORT` | `80` | nginx HTTP 监听端口 |
| `NGINX_HTTPS_PORT` | `443` | nginx HTTPS 监听端口 |
