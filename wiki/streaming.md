# Streaming — 流式响应

## Anthropic SSE 帧格式

Anthropic Messages API 的流式响应由一系列 Server-Sent Events 组成：

```
event: message_start
data: {
  "type": "message_start",
  "message": {
    "id": "msg_xxx",
    "type": "message",
    "role": "assistant",
    "content": [],
    "model": "glm-5.1",
    "stop_reason": null,
    "usage": {"input_tokens": 0, "output_tokens": 0}
  }
}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: ping
data: {"type":"ping"}

event: content_block_delta         # 每个 token 一个
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"你"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {
  "type": "message_delta",
  "delta": {"stop_reason": "end_turn", "stop_sequence": null},
  "usage": {"output_tokens": 42}
}

event: message_stop
data: {"type":"message_stop"}
```

## DeepSeek / DashScope 流式处理

这两个 provider 的端点是 Anthropic-compatible，直接返回符合上述格式的 SSE。

`AnthropicCompatProvider.forward_stream()` 做纯字节透传：

```python
async with client.stream("POST", url, json=body, headers=...) as resp:
    async for chunk in resp.aiter_bytes():
        yield chunk
```

无格式转换，延迟最低。

## Ollama 流式处理

Ollama 返回 OpenAI-compatible SSE。`OllamaProvider.forward_stream()` 负责转换：

### 输入（Ollama SSE）
```
data: {"id":"...","choices":[{"delta":{"content":"你"},"finish_reason":null}]}
data: {"id":"...","choices":[{"delta":{},"finish_reason":"stop"}],"usage":{...}}
data: [DONE]
```

### 转换逻辑
```python
async for line in resp.aiter_lines():
    if not line.startswith("data: "): continue
    payload = line[6:].strip()
    if payload == "[DONE]": break
    chunk = json.loads(payload)
    text = chunk["choices"][0].get("delta", {}).get("content") or ""
    if text:
        output_tokens += 1
        yield _sse("content_block_delta", {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": text},
        })
```

### 关键：延迟发送开头帧

```python
# 先等待 Ollama 返回 HTTP 状态码
async with client.stream("POST", url, ...) as resp:
    if resp.status_code != 200:
        yield _sse("error", {...}); return

    # 确认 200 OK 后才发送 message_start 等
    yield _sse("message_start", {...})
    yield _sse("content_block_start", {...})
    yield _sse("ping", {...})
    # 然后开始 token 流
```

若不这样做，Ollama 报错时客户端已经收到 `message_start`，会尝试解析错误的流，产生混乱。

## nginx 流式配置要点

| 指令 | 值 | 作用 |
|------|-----|------|
| `proxy_buffering` | `off` | 禁用 nginx 缓冲，token 实时下发 |
| `proxy_http_version` | `1.1` | 启用 chunked transfer，HTTP/1.0 不支持流 |
| `proxy_set_header Connection` | `""` | 防止 `Connection: keep-alive` 被 hop-by-hop 转发 |
| `proxy_read_timeout` | `300s` | 等待上游数据的超时，大模型生成时间长 |
| `proxy_send_timeout` | `300s` | 发送给客户端的超时，客户端接收慢时防 ECONNRESET |

## httpx 超时配置

```python
httpx.Timeout(
    timeout=settings.timeout,  # read timeout（默认 300s）
    connect=10,                 # AnthropicCompat（远程 API）
)

httpx.Timeout(
    timeout=settings.timeout,
    connect=30,                 # OllamaProvider（模型加载可能慢）
)
```

`connect` 超时：建立 TCP 连接的等待时间。  
`timeout`：等待响应数据的时间（包括流式的两个 chunk 之间）。

## 常见流式问题

| 症状 | 根因 | 解法 |
|------|------|------|
| 客户端收到 ECONNRESET | nginx `proxy_send_timeout` 默认 60s 过短 | 设为 300s |
| 流不实时，批量到达 | nginx `proxy_buffering on`（默认） | 设为 `off` |
| Ollama 流式响应触发 TLS 错误 | `forward_stream` 内部有 `await httpx.get()`（名称解析） | 改为同步 dict 查询 |
| 流中途断开无错误事件 | 异步生成器内 `BaseException`（如 `CancelledError`）未 yield | 补充 `except BaseException` 分支 |
