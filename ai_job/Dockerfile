# =========================
# ai_job 生产 Dockerfile
# =========================
# 单阶段构建：Python 3.11 slim + 系统依赖 + pip install + 源码
# PaddlePaddle 需走国内加速源
FROM python:3.11-slim-bookworm

WORKDIR /app

# 系统依赖：PaddleOCR 需要 libgomp1、libgl1 等，curl 用于健康检查
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先安装 pip 依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir python-dotenv

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 复制源码
COPY --chown=appuser:appuser . .

USER appuser

# 容器内监听 0.0.0.0（宿主机 127.0.0.1 在容器内是容器自己）
ENV AI_JOB_HOST=0.0.0.0
ENV AI_JOB_PORT=8001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=90s \
    CMD curl -f http://localhost:8001/api/internal/health || exit 1

CMD ["sh", "-c", "python -c \"from web_app import app; import uvicorn; uvicorn.run(app, host='${AI_JOB_HOST}', port=${AI_JOB_PORT})\""]
