#!/usr/bin/env groovy
// =========================
// 就业AI 项目 — Jenkins CI/CD Pipeline
// =========================
// 触发方式：Git push → Webhook 触发 / 定时轮询
// 部署目标：测试环境（通过 Docker Compose）
//
// 所需 Jenkins 插件：
//   - Docker Pipeline
//   - Git
//   - Credentials Binding（可选：如需推送私有镜像仓库）

pipeline {
    agent any

    // ========== 环境变量 ==========
    environment {
        // 项目根目录
        PROJECT_ROOT = '/Users/a1234/PycharmProjects'
        // 中间件 Compose 目录
        INFRA_COMPOSE_DIR = '/Users/a1234/workspace/docker'
        // 镜像标签：默认用 git commit short hash
        IMAGE_TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
        // Docker Registry（留空 = 本地构建，推送远程则填如 harbor.example.com/job-ai/）
        DOCKER_REGISTRY = ''
    }

    // ========== 参数 ==========
    parameters {
        choice(
            name: 'DEPLOY_MODE',
            choices: ['build-only', 'full-deploy'],
            description: '构建模式：build-only 只构建镜像；full-deploy 构建+部署'
        )
        string(
            name: 'IMAGE_TAG_OVERRIDE',
            defaultValue: '',
            description: '手动指定镜像标签（留空使用 git hash）'
        )
        booleanParam(
            name: 'NO_CACHE',
            defaultValue: false,
            description: '是否禁用 Docker 构建缓存'
        )
    }

    stages {

        // ========== Stage 1：代码拉取 ==========
        stage('Checkout') {
            steps {
                script {
                    echo "📥 拉取代码..."
                }
                checkout scm
                script {
                    echo "✅ 当前分支：${env.BRANCH_NAME}"
                    echo "✅ 提交哈希：${env.GIT_COMMIT.take(8)}"
                    echo "✅ 提交信息：${sh(script: 'git log -1 --oneline', returnStdout: true).trim()}"

                    // 覆盖镜像标签
                    if (params.IMAGE_TAG_OVERRIDE?.trim()) {
                        env.IMAGE_TAG = params.IMAGE_TAG_OVERRIDE.trim()
                        echo "🏷️ 镜像标签（手动）：${env.IMAGE_TAG}"
                    }
                }
            }
        }

        // ========== Stage 2：并行构建 Docker 镜像 ==========
        stage('Build Docker Images') {
            parallel {
                stage('Build ai_job') {
                    steps {
                        script {
                            echo "🐍 构建 ai_job（Python FastAPI）..."
                            def noCacheFlag = params.NO_CACHE ? '--no-cache' : ''
                            sh """
                                docker build ${noCacheFlag} \
                                    -t ${env.DOCKER_REGISTRY}ai_job:${env.IMAGE_TAG} \
                                    -t ${env.DOCKER_REGISTRY}ai_job:latest \
                                    -f ${PROJECT_ROOT}/ai_job/Dockerfile \
                                    ${PROJECT_ROOT}/ai_job
                            """
                            echo "✅ ai_job 镜像构建完成"
                        }
                    }
                }

                stage('Build server_job') {
                    steps {
                        script {
                            echo "☕ 构建 server_job（Spring Boot）..."
                            def noCacheFlag = params.NO_CACHE ? '--no-cache' : ''
                            sh """
                                docker build ${noCacheFlag} \
                                    -t ${env.DOCKER_REGISTRY}server_job:${env.IMAGE_TAG} \
                                    -t ${env.DOCKER_REGISTRY}server_job:latest \
                                    -f ${PROJECT_ROOT}/server_job/Dockerfile \
                                    ${PROJECT_ROOT}/server_job
                            """
                            echo "✅ server_job 镜像构建完成"
                        }
                    }
                }

                stage('Build web_job') {
                    steps {
                        script {
                            echo "🎨 构建 web_job（Vue + Nginx）..."
                            def noCacheFlag = params.NO_CACHE ? '--no-cache' : ''
                            sh """
                                docker build ${noCacheFlag} \
                                    -t ${env.DOCKER_REGISTRY}web_job:${env.IMAGE_TAG} \
                                    -t ${env.DOCKER_REGISTRY}web_job:latest \
                                    -f ${PROJECT_ROOT}/web_job/Dockerfile \
                                    ${PROJECT_ROOT}
                            """
                            echo "✅ web_job 镜像构建完成"
                        }
                    }
                }
            }
        }

        // ========== Stage 3：快速验证 ==========
        stage('Quick Verify') {
            steps {
                script {
                    echo "🔍 检查构建好的镜像..."
                    sh """
                        echo "=== 本地镜像 ==="
                        docker images | grep -E 'ai_job|server_job|web_job' | grep "${env.IMAGE_TAG}" || echo "⚠️ 未找到标签 ${env.IMAGE_TAG} 的镜像"
                    """

                    echo "🔍 Docker Compose 配置语法检查..."
                    sh """
                        docker compose -f ${PROJECT_ROOT}/docker-compose.prod.yml config --quiet 2>&1 || true
                    """
                }
            }
        }

        // ========== Stage 4：部署 ==========
        stage('Deploy') {
            when {
                expression { params.DEPLOY_MODE == 'full-deploy' }
            }
            steps {
                script {
                    echo "🚀 开始部署..."

                    // 检查中间件网络是否存在
                    def networkCheck = sh(
                        script: 'docker network ls --format "{{.Name}}" | grep -q "^docker_app-network$" && echo "exists" || echo "missing"',
                        returnStdout: true
                    ).trim()

                    if (networkCheck == 'missing') {
                        echo "⚠️ Docker 中间件网络 'docker_app-network' 不存在，请先启动中间件："
                        echo "   cd ${INFRA_COMPOSE_DIR} && docker compose up -d"
                        error("中间件网络缺失，部署中止。请先启动中间件层。")
                    }

                    // 滚动更新应用容器
                    echo "🔄 滚动更新应用容器（IMAGE_TAG=${env.IMAGE_TAG}）..."
                    sh """
                        cd ${PROJECT_ROOT} && \
                        IMAGE_TAG=${env.IMAGE_TAG} \
                        docker compose -f docker-compose.prod.yml up -d --remove-orphans
                    """

                    echo "🧹 清理旧镜像（保留最新 3 个标签）..."
                    sh """
                        for svc in ai_job server_job web_job; do
                            docker images \${svc} --format '{{.Tag}}' | sort -r | tail -n +4 | while read tag; do
                                docker rmi \${svc}:\${tag} 2>/dev/null || true
                            done
                        done
                    """

                    echo "✅ 部署完成"
                }
            }
        }

        // ========== Stage 5：部署后健康检查 ==========
        stage('Health Check') {
            when {
                expression { params.DEPLOY_MODE == 'full-deploy' }
            }
            steps {
                script {
                    echo "🏥 等待服务就绪..."

                    // 等待 ai_job
                    timeout(time: 3, unit: 'MINUTES') {
                        script {
                            def retries = 0
                            while (retries < 12) {
                                def status = sh(
                                    script: 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/internal/health || echo "000"',
                                    returnStdout: true
                                ).trim()
                                if (status == '200') break
                                echo "⏳ ai_job (${retries + 1}/12): HTTP ${status}"
                                sleep(15)
                                retries++
                            }
                            if (retries >= 12) error("ai_job 健康检查超时")
                            echo "✅ ai_job 就绪"
                        }
                    }

                    // 等待 web_job
                    timeout(time: 1, unit: 'MINUTES') {
                        script {
                            def retries = 0
                            while (retries < 6) {
                                def status = sh(
                                    script: 'curl -s -o /dev/null -w "%{http_code}" http://localhost:80/ || echo "000"',
                                    returnStdout: true
                                ).trim()
                                if (status == '200') break
                                echo "⏳ web_job (${retries + 1}/6): HTTP ${status}"
                                sleep(10)
                                retries++
                            }
                            if (retries >= 6) error("web_job 健康检查超时")
                            echo "✅ web_job 就绪"
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                echo "========== Pipeline 结束 =========="
                echo "分支：${env.BRANCH_NAME}"
                echo "镜像标签：${env.IMAGE_TAG}"
                echo "构建结果：${currentBuild.result ?: 'SUCCESS'}"
            }
        }
        success {
            echo "🎉 CI/CD 流水线成功完成"
        }
        failure {
            echo "❌ CI/CD 流水线失败，请检查日志"
        }
    }
}
