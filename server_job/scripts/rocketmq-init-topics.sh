#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# RocketMQ 5 — 创建面试模块 Topic（本地 docker-compose）
#
# 用法:
#   cd server_job
#   chmod +x scripts/rocketmq-init-topics.sh
#   ./scripts/rocketmq-init-topics.sh
#
# 环境变量（可选）:
#   ROCKETMQ_NS_CONTAINER   NameServer 容器名，默认 server-job-rocketmq-nameserver
#   ROCKETMQ_BROKER_CONTAINER Broker 容器名，默认 server-job-rocketmq-broker
#   ROCKETMQ_NAMESRV_ADDR     默认 rocketmq-nameserver:9876
#   ROCKETMQ_CLUSTER          默认 DefaultCluster
# -----------------------------------------------------------------------------

set -euo pipefail

NS_CONTAINER="${ROCKETMQ_NS_CONTAINER:-server-job-rocketmq-nameserver}"
BROKER_CONTAINER="${ROCKETMQ_BROKER_CONTAINER:-server-job-rocketmq-broker}"
NAMESRV_ADDR="${ROCKETMQ_NAMESRV_ADDR:-rocketmq-nameserver:9876}"
CLUSTER="${ROCKETMQ_CLUSTER:-DefaultCluster}"

TOPICS=(
  "${INTERVIEW_MQ_TOPIC_AI_TASK:-interview_ai_task}"
  "${INTERVIEW_MQ_TOPIC_AI_RESULT:-interview_ai_result}"
  "${INTERVIEW_MQ_TOPIC_TIMER:-interview_timer_event}"
  "${INTERVIEW_MQ_TOPIC_DLQ:-interview_dlq}"
)

if ! docker ps --format '{{.Names}}' | grep -q "^${BROKER_CONTAINER}\$"; then
  echo "错误: 未找到 Broker 容器 ${BROKER_CONTAINER}"
  echo "请先执行: docker compose up -d rocketmq-nameserver rocketmq-broker"
  exit 1
fi

mqadmin() {
  docker exec "${BROKER_CONTAINER}" sh mqadmin "$@" -n "${NAMESRV_ADDR}"
}

echo "==> NameServer: ${NAMESRV_ADDR}  Cluster: ${CLUSTER}"
echo "==> 创建 Topic ..."
for topic in "${TOPICS[@]}"; do
  echo "    - ${topic}"
  mqadmin updateTopic -t "${topic}" -c "${CLUSTER}" || {
    echo "警告: updateTopic ${topic} 失败，尝试继续"
  }
done

echo ""
echo "==> 当前 Topic 列表（节选）"
mqadmin topicList -c "${CLUSTER}" 2>/dev/null | head -30 || true

echo ""
echo "完成。应用连接 Proxy: ROCKETMQ_PROXY_ENDPOINT=localhost:18080"
echo "联调接口见: server_job/docs/ROCKETMQ联调.md"
