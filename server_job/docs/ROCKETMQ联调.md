# RocketMQ 5 Proxy 联调说明（server_job + ai_job）

## 1. 架构速查

| 项 | 值 |
|----|-----|
| Proxy HTTP（本地） | `localhost:18080` → 容器 `8080`（`ROCKETMQ_PROXY_PORT`） |
| Proxy gRPC（本地） | `localhost:18081` → 容器 `8081`（`ROCKETMQ_PROXY_GRPC_PORT`） |
| NameServer（容器内） | `rocketmq-nameserver:9876`；宿主机 `localhost:9876` |
| Broker 配置（compose） | `~/workspace/docker/rocketmq/broker.conf`（`brokerIP1=host.docker.internal` 供 Dashboard；`proxyAdvertiseAddr=127.0.0.1:18081`） |

| Topic | 说明 | 生产者 | 消费者 |
|-------|------|--------|--------|
| `interview_ai_task` | 异步 AI 任务 | server_job / ai_job_a | ai_job_b (`ai_job_b_worker`) |
| `interview_ai_result` | AI 结果回写 | ai_job_b / ai_job_a | server_job (`server_job_interview_result_consumer`) |
| `interview_timer_event` | 超时事件（预留） | server_job | — |
| `interview_dlq` | 死信（预留） | — | — |

**客户端协议（方案 A）**

| 进程 | 依赖 / SDK | 连接地址 |
|------|------------|----------|
| server_job | `rocketmq-v5-client-spring-boot-starter` 2.3.x | `ROCKETMQ_PROXY_GRPC_ENDPOINT=127.0.0.1:18081`（勿用 `host.docker.internal`） |
| ai_job | `rocketmq-python-client` | 同上 + `ROCKETMQ_ROUTE_REWRITE=1`（默认） |

勿再使用旧版 `rocketmq-spring-boot-starter` + `name-server:18080`（Proxy remoting），在 RocketMQ 5 下消费者常注册为 `NO_CONSUMER`。

## 2. 启动中间件

```bash
cd server_job
docker compose up -d rocketmq-nameserver rocketmq-broker
```

若从 **`~/workspace/docker`** 启动 compose（挂载 `docker/rocketmq/broker.conf`）：

- **`brokerIP1=host.docker.internal`**：Dashboard（容器内）可连 Broker；**不影响**本机 server_job，只要下面环境变量指向 **`127.0.0.1:18081`**。
- compose 须包含端口：`18081:8081`、`8081:8081`（SDK 路由二次连接可能走 `*:8081`）。

```bash
cd ~/workspace/docker
docker compose up -d rocketmq-broker rocketmq-nameserver
cd /path/to/PycharmProjects/server_job && ./scripts/rocketmq-init-topics.sh
```

确认端口：

```bash
nc -zv localhost 18081   # Proxy gRPC（业务收发）
nc -zv localhost 18080   # Proxy HTTP（可选）
nc -zv localhost 9876    # NameServer（可选）
```

## 3. 初始化 Topic

```bash
chmod +x scripts/rocketmq-init-topics.sh
./scripts/rocketmq-init-topics.sh
```

## 4. 环境变量

**server_job**（复制 `.env.example` → `.env` 或 IDE Environment）：

```bash
# 必填：只连 Proxy gRPC（application.yml 已绑定这些变量）
ROCKETMQ_PROXY_GRPC_ENDPOINT=127.0.0.1:18081
ROCKETMQ_PROXY_ENDPOINT=127.0.0.1:18080
ROCKETMQ_SSL_ENABLED=false

ROCKETMQ_PRODUCER_GROUP=server_job_producer
INTERVIEW_MQ_ENABLED=true
INTERVIEW_MQ_CONSUMER_ENABLED=true
```

**不要配置**（旧版 4.x / Remoting，会与 5.x gRPC 冲突）：

```bash
# rocketmq.name-server=localhost:9876
# rocketmq.name-server=localhost:18080
```

`application.yml` 中 `rocketmq.producer.endpoints` / `rocketmq.push-consumer.endpoints`
已引用 `ROCKETMQ_PROXY_GRPC_ENDPOINT`，无需再改 YAML。

**ai_job**（`ai_job/.env`）：

```bash
# rocketmq-python-client 必须连 gRPC（compose 映射 18081→8081）
ROCKETMQ_PROXY_GRPC_ENDPOINT=localhost:18081
ROCKETMQ_PRODUCER_GROUP=ai_job_a_producer
ROCKETMQ_CONSUMER_GROUP=ai_job_b_worker
ROLE=ai_job_a   # API 进程；Worker 用 ROLE=ai_job_b
```

## 5. server_job 联调 API

启动 `server_job`（默认端口 `8002`）后：

### 5.1 查看 MQ 配置

```http
GET http://localhost:8002/demo/interview-mq/config
```

应含 `proxyGrpcEndpoint: localhost:18081`。

### 5.2 检测 Proxy 连通

```http
GET http://localhost:8002/demo/rocketmq
```

检测 gRPC 端口 `18081` 是否可达。

### 5.3 发送测试任务（→ `interview_ai_task`）

```http
POST http://localhost:8002/demo/interview-mq/send-task
Content-Type: application/json

{
  "event_type": "interview.reflection.request",
  "idempotency_key": "test:session:reflection:1",
  "payload": {
    "interview_session_id": "isess_test_001",
    "student_id": "stu_test"
  }
}
```

无 Body 时使用内置样例信封。

### 5.4 发送测试结果（→ `interview_ai_result`，测 server_job 消费）

```http
POST http://localhost:8002/demo/interview-mq/send-result
Content-Type: application/json

{
  "event_type": "interview.reflection.result",
  "producer": "ai_job_b",
  "idempotency_key": "test:session:reflection:1",
  "payload": { "status": "ok" }
}
```

成功时 `server_job` 日志会出现 `收到 interview_ai_result`，并尝试写入 `interview_mq_consume_log`（需已执行建表 SQL）。

## 6. ai_job 命令行发测

```bash
cd ai_job
export ROCKETMQ_PROXY_GRPC_ENDPOINT=localhost:18081
export ROCKETMQ_PRODUCER_GROUP=ai_job_a_producer

# 发一条测试任务
python scripts/mq_send_test.py --topic interview_ai_task

# 启动 Worker 消费
export ROLE=ai_job_b
export ROCKETMQ_CONSUMER_GROUP=ai_job_b_worker
python -m app.session.role.role005.worker_main
```

## 7. 端到端建议顺序

1. `docker compose up` + `./scripts/rocketmq-init-topics.sh`
2. 启动 `server_job`（配置 `ROCKETMQ_PROXY_GRPC_ENDPOINT`），`POST /demo/interview-mq/send-result` 或等 ai_job 发 `interview_ai_result`
3. 日志出现 `收到 interview_ai_result`；`mqadmin statsAll` 中该 Topic 消费组不应为 `NO_CONSUMER`
4. 测任务流：`POST /demo/interview-mq/send-task` → 启动 ai_job Worker → 回发 result → server_job 消费

## 8. 常见问题

| 现象 | 处理 |
|------|------|
| 发送超时 | 确认 Broker/Proxy 已起、`18081` gRPC 可连 |
| `invalid ipv4 address: host.docker.internal` | server_job/ai_job 的 **环境变量** 必须用 `127.0.0.1:18081`，不要写 `host.docker.internal`（Dashboard 才依赖 broker 上的该主机名） |
| `connect to 127.0.0.1:10911 failed`（Dashboard） | compose 里 `brokerIP1` 应为 `host.docker.internal`，并 `docker compose restart rocketmq-dashboard` |
| Dashboard「生产者连接」`not exist` | 5.x gRPC 客户端不会登记 producer group，改查 Topic/消息；组名示例 `server_job_producer` |
| Topic 不存在 | 重跑 `rocketmq-init-topics.sh` |
| 消费者无日志 / `NO_CONSUMER` | 确认已换 `rocketmq-v5-client-spring-boot-starter`，且 `rocketmq.push-consumer.endpoints` 指向 18081 |
| server_job 仍用 18080 发消息失败 | 改用 gRPC 配置，勿填 `rocketmq.name-server` |
| Python 仅打日志未真发 | `pip install rocketmq-python-client`（发送走 gRPC 18081） |
