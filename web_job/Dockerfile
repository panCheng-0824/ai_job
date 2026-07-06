# =========================
# web_job 生产 Dockerfile
# =========================
# 多阶段构建：Node 构建 SPA → Nginx 托管
# 构建上下文：项目根目录（PycharmProjects/），以访问 CubismSdkForWeb-5-r.5
#
# 构建命令：
#   docker build -t web_job:latest -f web_job/Dockerfile .
#
# 阶段 1：构建
FROM node:22-alpine AS builder

WORKDIR /build

# pnpm 安装
RUN corepack enable && corepack prepare pnpm@latest --activate

# CI 环境变量（避免 pnpm 10+ 的 TTY 检查）
ENV CI=true
ENV PNPM_HOME="/root/.local/share/pnpm"

# 先复制依赖文件，利用层缓存（路径相对于项目根目录）
# pnpm 10+ 默认拒绝未批准构建脚本的依赖，用 --config.ignore-scripts=true 跳过
COPY web_job/package.json web_job/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --config.ignore-scripts=true

# 复制 web_job 源码
COPY web_job/ ./

# 复制 Cubism SDK（项目根目录下）
COPY CubismSdkForWeb-5-r.5 /CubismSdkForWeb-5-r.5

# 构建（vite build 前重新 install 确认模块完整）
RUN pnpm install --frozen-lockfile --config.ignore-scripts=true && pnpm run build

# 阶段 2：Nginx 托管
FROM nginx:stable-alpine

# 健康检查依赖
RUN apk add --no-cache curl

# 复制构建产物
COPY --from=builder /build/dist /usr/share/nginx/html

# Nginx 配置（从 web_job 子目录）
COPY web_job/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
