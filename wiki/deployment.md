# Deployment — 部署指南

## 快速启动

```bash
# 1. 复制配置
cp .env.example .env
vim .env   # 填入 API_KEY、厂商 Key、启用对应 provider

# 2. 确保 shared-proxy 网络存在（与其他 compose 栈共享 nginx）
docker network create shared-proxy 2>/dev/null || true

# 3. 构建并启动
docker compose up -d --build

# 4. 验证
curl http://localhost:8000/health
# {"status":"ok","providers":["DeepSeek","DashScope"]}
```

---

## docker-compose.yml 解析

```yaml
services:
  proxy:
    build: .
    container_name: llm-proxy
    restart: unless-stopped
    ports:
      - "8000:8000"      # 直接暴露，供调试；生产走 nginx
    env_file: .env
    extra_hosts:
      - "host.docker.internal:host-gateway"   # 容器内访问宿主机 Ollama

  nginx:
    image: nginx:alpine
    container_name: llm-proxy-nginx
    ports:
      - "${NGINX_HTTP_PORT:-80}:80"
      - "${NGINX_HTTPS_PORT:-443}:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro   # 自签或 Let's Encrypt 证书
    networks:
      - default
      - shared-proxy    # 允许其他 compose 栈通过此 nginx 入口

networks:
  shared-proxy:
    external: true      # 必须提前 docker network create shared-proxy
```

---

## nginx/nginx.conf 关键配置

```nginx
location /v1/ {
    proxy_pass http://llm_proxy;    # upstream: proxy:8000
    proxy_http_version 1.1;         # 流式必须，避免 HTTP/1.0 连接复用问题
    proxy_set_header Connection ""; # 清除 hop-by-hop header
    proxy_buffering off;            # 流式必须，禁用 nginx 缓冲
    proxy_read_timeout 300s;        # 等上游读取超时
    proxy_send_timeout 300s;        # 等客户端接收超时（防 ECONNRESET）
    proxy_connect_timeout 30s;
}
```

> **流式必须的三件套**：`proxy_http_version 1.1` + `proxy_set_header Connection ""` + `proxy_buffering off`
>
> 漏掉 `proxy_send_timeout` 会导致长时间推理时客户端报 ECONNRESET（默认 60s）。

---

## Dockerfile 解析

```dockerfile
FROM python:3.11
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    fastapi "uvicorn[standard]" httpx pydantic pydantic-settings
# 使用阿里云 PyPI 镜像加速（国内环境）
COPY app ./app
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

- `python:3.11` 基础镜像，不含 dev 依赖，体积较小
- `--workers 2`：2 个 uvicorn 进程。注意：每个 worker 有独立的 `ProviderRegistry`（含独立的模型缓存），这是 OK 的，因为缓存仅影响性能不影响正确性

---

## 多 compose 栈网络

本项目设计为与其他服务共享一个 nginx 入口。典型拓扑：

```
docker network: shared-proxy
  └── cowork-llm-proxy/  → nginx 暴露 :80/:443
  └── trading-agent/     → frontend:80（通过同一 nginx 的 / 路由）
  └── other-services/    → 其他内部服务
```

nginx 路由规则：
- `/v1/` → llm-proxy（本项目）
- `/`    → trading-agent-frontend（同 compose 栈内另一个容器）

---

## 运维常用命令

```bash
# 查看日志（实时）
docker logs -f llm-proxy

# 仅重建 proxy（不重建 nginx）
docker compose up -d --build proxy

# 重启 nginx（修改 nginx.conf 后）
docker compose restart nginx

# 进入容器调试
docker exec -it llm-proxy bash

# 查看已注册的模型
curl -H "x-api-key: $API_KEY" http://localhost:8000/v1/models | jq '.data[].id'

# 测试单个模型
curl -s -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  http://localhost:8000/v1/messages \
  -d '{"model":"glm-5.1","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

---

## Claude Desktop 配置示例

```json
{
  "mcpServers": {},
  "anthropicApiKey": "sk-your-proxy-key-here",
  "anthropicBaseUrl": "http://localhost:8000"
}
```

或直接在 Claude Desktop 的 API 设置中填写：
- **API Key**：`API_KEY` 的值
- **Base URL**：`http://<server-ip>:8000`（通过 nginx）或 `http://<server-ip>:8000`（直连）
