# 部署指南

> 相关页面：[config.md](config.md) · [api.md](api.md)

## 方式一：仅 Docker Compose（HTTP）

最简单的启动方式，服务监听 `http://localhost:8000`：

```bash
cp .env.example .env
# 编辑 .env，填入 API_KEY 和上游 Key
docker compose up -d proxy
```

验证：
```bash
curl http://localhost:8000/health
```

---

## 方式二：完整栈（HTTPS + 自定义域名）

包含 Caddy 反向代理，通过 `tls internal` 自动签发本地受信证书，域名 `my.cowork.llm`。

### 服务端口分配

| 服务 | 容器名 | 对外端口 | 说明 |
|---|---|---|---|
| FastAPI | `llm-proxy` | 8000（仅内部） | 被 Caddy 反代，不直接对外 |
| Caddy | `llm-proxy-caddy` | 80, 443 | HTTP → HTTPS 重定向 + TLS 终止 |

### 步骤

**1. 修改 hosts 文件（客户端机器）**

macOS / Linux：
```bash
sudo sh -c 'echo "127.0.0.1 my.cowork.llm" >> /etc/hosts'
```

Windows（`C:\Windows\System32\drivers\etc\hosts`，管理员权限）：
```
127.0.0.1 my.cowork.llm
```

**2. 启动所有服务**

```bash
docker compose up -d
```

**3. 导出 Caddy 根证书**

```bash
docker cp llm-proxy-caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
```

**4. 信任证书**

macOS：
```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain ./caddy-root.crt
# 重启浏览器后生效
```

撤销：
```bash
sudo security delete-certificate -c "Caddy Local Authority" \
  /Library/Keychains/System.keychain
```

Windows：双击 `caddy-root.crt` → 安装证书 → 本地计算机 → **受信任的根证书颁发机构**。

Linux（Debian/Ubuntu）：
```bash
sudo cp caddy-root.crt /usr/local/share/ca-certificates/caddy-root.crt
sudo update-ca-certificates
```

**5. 验证**

```bash
curl -v https://my.cowork.llm/health
```

---

## Ollama 与 Docker 的网络问题

Ollama 通常运行在宿主机，Docker 容器内无法直接访问 `localhost:11434`。解决方案：

`docker-compose.yml` 已配置：
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

因此在 `.env` 中设置：
```
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## 多提供商网络部署

如果多个服务共享同一个 nginx/Caddy 入口（如 cowork 部署结构），可以将代理加入 `shared-proxy` 网络：

```yaml
networks:
  shared-proxy:
    external: true
```

见项目内存 [project_architecture.md](../../../memory/project_architecture.md)。

---

## 日志查看

```bash
docker compose logs -f proxy    # FastAPI 日志
docker compose logs -f caddy    # Caddy 访问日志
```

生产环境日志仅输出到 stdout，需配合日志收集器（如 Loki、Fluentd）持久化。

## 相关页面

- 配置参考 → [config.md](config.md)
- API 端点 → [api.md](api.md)
