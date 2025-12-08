#!/bin/bash

# 智能设计营销自动化系统 - 零感知部署脚本
# 使用方法: ./deploy.sh [环境] [选项]
# 环境: dev, test, prod (默认: dev)

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取参数
ENV=${1:-dev}
PROJECT_NAME=${PROJECT_NAME:-智能设计营销系统}
COMPOSE_FILE="docker-compose.yml"

# 根据环境设置变量
case $ENV in
    dev|development)
        ENV_FILE=".env"
        COMPOSE_FILE="docker-compose.yml"
        ;;
    test|testing)
        ENV_FILE=".env.test"
        COMPOSE_FILE="docker-compose.yml"
        ;;
    prod|production)
        ENV_FILE=".env.prod"
        COMPOSE_FILE="docker-compose.yml"
        ;;
    *)
        log_error "未知的环境: $ENV"
        echo "使用方法: $0 [dev|test|prod]"
        exit 1
        ;;
esac

log_info "开始部署 $PROJECT_NAME 到 $ENV 环境..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 检查环境文件
if [ ! -f "$ENV_FILE" ]; then
    if [ -f ".env.template" ]; then
        log_warning "环境文件 $ENV_FILE 不存在，将从模板创建..."
        cp .env.template $ENV_FILE
        log_warning "请编辑 $ENV_FILE 文件，配置必要的环境变量"
        log_info "编辑完成后，重新运行此脚本"
        exit 1
    else
        log_error "环境文件模板 .env.template 不存在"
        exit 1
    fi
fi

# 加载环境变量
export $(grep -v '^#' $ENV_FILE | xargs)

# 创建必要的目录
log_info "创建必要的目录..."
mkdir -p data logs config

# 构建镜像
log_info "构建 Docker 镜像..."
docker build -t $PROJECT_NAME:$APP_VERSION .
docker tag $PROJECT_NAME:$APP_VERSION $PROJECT_NAME:latest

# 停止旧容器
log_info "停止旧容器..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down || true

# 启动服务
log_info "启动服务..."
if [ "$ENV" = "prod" ]; then
    # 生产环境启动所有服务包括监控
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE --profile metrics up -d
else
    # 开发/测试环境只启动必要服务
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d app redis
fi

# 等待服务启动
log_info "等待服务启动..."
sleep 10

# 检查服务状态
log_info "检查服务状态..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE ps

# 显示服务日志
log_info "显示应用日志..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE logs --tail=20 app

# 显示访问信息
PORT=${PORT:-8000}
log_success "部署完成！"
echo "================================"
echo "应用访问地址: http://localhost:$PORT"
echo "Redis 地址: redis://localhost:6379"

if [ "$ENV" = "prod" ]; then
    METRICS_PORT=${METRICS_PORT:-9090}
    echo "Prometheus 监控: http://localhost:$METRICS_PORT"
fi

echo "================================"
echo ""
echo "查看日志: docker-compose -f $COMPOSE_FILE logs -f app"
echo "停止服务: docker-compose -f $COMPOSE_FILE down"
echo "重启服务: docker-compose -f $COMPOSE_FILE restart app"
echo ""
log_success "部署成功！"