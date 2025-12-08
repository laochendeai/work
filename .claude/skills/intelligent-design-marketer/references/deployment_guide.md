# 企业级部署指南

## 目录
1. [部署架构概览](#部署架构概览)
2. [环境准备](#环境准备)
3. [容器化部署](#容器化部署)
4. [Kubernetes部署](#kubernetes部署)
5. [高可用配置](#高可用配置)
6. [安全配置](#安全配置)
7. [性能优化](#性能优化)
8. [监控和运维](#监控和运维)
9. [故障排除](#故障排除)

## 部署架构概览

### 系统架构图

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │    (Nginx/HAProxy)   │
                    └─────────┬───────┘
                              │
                    ┌─────────┴───────┐
                    │  API Gateway    │
                    │   (FastAPI)      │
                    └─────────┬───────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴───────┐    ┌────────┴────────┐    ┌───────┴───────┐
│   Scraper     │    │  Email Service  │    │   Web UI      │
│   Service     │    │                 │    │ (Streamlit)   │
└───────┬───────┘    └────────┬────────┘    └───────────────┘
        │                     │
        │              ┌──────┴───────┐
        │              │  Message     │
        │              │  Queue       │
        │              │  (Celery)    │
        │              └──────┬───────┘
        │                     │
        │              ┌──────┴───────┐
        │              │  Database    │
        │              │ (PostgreSQL) │
        │              └──────┬───────┘
        │                     │
        │              ┌──────┴───────┐
        │              │   Cache      │
        │              │   (Redis)    │
        │              └──────────────┘
```

### 组件说明

| 组件 | 描述 | 技术栈 | 资源要求 |
|------|------|--------|----------|
| Load Balancer | 负载均衡和SSL终止 | Nginx/HAProxy | 1-2 CPU, 1-2GB RAM |
| API Gateway | API网关和路由 | FastAPI + Uvicorn | 2-4 CPU, 4-8GB RAM |
| Scraper Service | 爬虫服务 | Python + BeautifulSoup | 2-4 CPU, 4-8GB RAM |
| Email Service | 邮件发送服务 | Python + Celery | 1-2 CPU, 2-4GB RAM |
| Database | 主数据库 | PostgreSQL 13+ | 4-8 CPU, 16-32GB RAM |
| Cache | 缓存和消息队列 | Redis 6+ | 2-4 CPU, 8-16GB RAM |
| Monitoring | 监控系统 | Prometheus + Grafana | 1-2 CPU, 4-8GB RAM |

## 环境准备

### 硬件要求

#### 开发环境
- **CPU**: 2核心以上
- **内存**: 8GB以上
- **存储**: 50GB SSD
- **网络**: 100Mbps

#### 测试环境
- **CPU**: 4核心以上
- **内存**: 16GB以上
- **存储**: 100GB SSD
- **网络**: 1Gbps

#### 生产环境
- **CPU**: 8核心以上
- **内存**: 32GB以上
- **存储**: 500GB SSD + 2TB HDD
- **网络**: 10Gbps

### 软件要求

```bash
# 操作系统
Ubuntu 20.04 LTS / CentOS 8 / RHEL 8

# 运行时环境
Python 3.9+
Docker 20.10+
Docker Compose 2.0+

# 数据库
PostgreSQL 13+
Redis 6+

# 监控
Prometheus 2.30+
Grafana 8.0+
```

### 基础环境安装

```bash
#!/bin/bash
# install_dependencies.sh

# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 安装PostgreSQL客户端
sudo apt install -y postgresql-client

# 安装其他工具
sudo apt install -y git htop iotop nginx

# 创建应用目录
sudo mkdir -p /opt/marketing-system
sudo chown $USER:$USER /opt/marketing-system
```

## 容器化部署

### Docker Compose配置

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  # Nginx负载均衡器
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - api-1
      - api-2
    restart: unless-stopped
    networks:
      - marketing-network
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G

  # API服务集群
  api-1:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/marketing_db
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
      - SERVICE_ID=api-1
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - marketing-network
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G

  api-2:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/marketing_db
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
      - SERVICE_ID=api-2
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - marketing-network
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G

  # 爬虫服务
  scraper:
    build:
      context: .
      dockerfile: Dockerfile
    command: python src/main.py --scraping-only
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/marketing_db
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - marketing-network
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G

  # 邮件服务
  email:
    build:
      context: .
      dockerfile: Dockerfile
    command: python src/main.py --email-only
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/marketing_db
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - marketing-network
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  # Celery Worker
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A src.tasks worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/marketing_db
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - marketing-network
    deploy:
      replicas: 4

  # Celery Beat (定时任务)
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A src.tasks beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/marketing_db
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config:ro
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - marketing-network

  # Web界面
  web:
    build:
      context: .
      dockerfile: Dockerfile
    command: streamlit run src/web/app.py --server.port=3000 --server.address=0.0.0.0
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/marketing_db
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
      - ./config:/app/config:ro
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - marketing-network

  # PostgreSQL数据库
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=marketing_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
      - ./database/backups:/backups
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - marketing-network
    deploy:
      resources:
        limits:
          cpus: '8.0'
          memory: 32G
        reservations:
          cpus: '4.0'
          memory: 16G

  # Redis缓存
  redis:
    image: redis:6-alpine
    command: redis-server --appendonly yes --requirepass redis_password
    volumes:
      - redis_data:/data
      - ./redis/redis.conf:/usr/local/etc/redis/redis.conf:ro
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - marketing-network
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 16G
        reservations:
          cpus: '2.0'
          memory: 8G

  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped
    networks:
      - marketing-network

  # Grafana可视化
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus
    restart: unless-stopped
    networks:
      - marketing-network

networks:
  marketing-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
```

### 部署脚本

```bash
#!/bin/bash
# deploy_production.sh

set -e

echo "🚀 开始生产环境部署..."

# 检查环境
check_environment() {
    echo "📋 检查部署环境..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose未安装"
        exit 1
    fi

    # 检查配置文件
    if [ ! -f "config/environments/production.yaml" ]; then
        echo "❌ 生产环境配置文件不存在"
        exit 1
    fi

    echo "✅ 环境检查通过"
}

# 准备配置
prepare_config() {
    echo "⚙️ 准备生产配置..."

    # 创建必要目录
    mkdir -p logs/nginx
    mkdir -p database/backups
    mkdir -p monitoring/grafana/{dashboards,datasources}

    # 生成随机密钥
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -base64 32)
    REDIS_PASSWORD=$(openssl rand -base64 32)

    # 更新配置文件
    sed -i "s/SECRET_KEY_PLACEHOLDER/$SECRET_KEY/g" config/environments/production.yaml
    sed -i "s/DB_PASSWORD_PLACEHOLDER/$DB_PASSWORD/g" config/environments/production.yaml
    sed -i "s/REDIS_PASSWORD_PLACEHOLDER/$REDIS_PASSWORD/g" config/environments/production.yaml

    echo "✅ 配置准备完成"
}

# 构建镜像
build_images() {
    echo "🏗️ 构建Docker镜像..."

    docker-compose -f docker-compose.production.yml build --no-cache

    echo "✅ 镜像构建完成"
}

# 数据库初始化
init_database() {
    echo "🗄️ 初始化数据库..."

    # 启动数据库服务
    docker-compose -f docker-compose.production.yml up -d postgres

    # 等待数据库就绪
    sleep 30

    # 运行数据库迁移
    docker-compose -f docker-compose.production.yml run --rm api python scripts/migrate.py

    echo "✅ 数据库初始化完成"
}

# 启动服务
start_services() {
    echo "🚀 启动所有服务..."

    docker-compose -f docker-compose.production.yml up -d

    echo "✅ 服务启动完成"
}

# 健康检查
health_check() {
    echo "🔍 执行健康检查..."

    # 等待服务启动
    sleep 60

    # 检查API服务
    if curl -f http://localhost/api/health > /dev/null 2>&1; then
        echo "✅ API服务健康"
    else
        echo "❌ API服务异常"
        exit 1
    fi

    # 检查数据库
    if docker-compose -f docker-compose.production.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "✅ 数据库服务健康"
    else
        echo "❌ 数据库服务异常"
        exit 1
    fi

    # 检查Redis
    if docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis服务健康"
    else
        echo "❌ Redis服务异常"
        exit 1
    fi

    echo "✅ 所有服务健康检查通过"
}

# 主函数
main() {
    echo "🎯 智能设计营销自动化系统 - 生产环境部署"
    echo "=================================================="

    check_environment
    prepare_config
    build_images
    init_database
    start_services
    health_check

    echo "=================================================="
    echo "🎉 部署完成！"
    echo ""
    echo "📊 访问地址:"
    echo "  • API服务: http://localhost/api"
    echo "  • Web界面: http://localhost:3000"
    echo "  • 监控面板: http://localhost:3001"
    echo "  • API文档: http://localhost/api/docs"
    echo ""
    echo "🔧 管理命令:"
    echo "  • 查看状态: docker-compose -f docker-compose.production.yml ps"
    echo "  • 查看日志: docker-compose -f docker-compose.production.yml logs -f [service]"
    echo "  • 停止服务: docker-compose -f docker-compose.production.yml down"
    echo "  • 重启服务: docker-compose -f docker-compose.production.yml restart [service]"
}

# 执行主函数
main "$@"
```

## Kubernetes部署

### Kubernetes清单文件

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: marketing-system
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: marketing-config
  namespace: marketing-system
data:
  production.yaml: |
    environment: production
    debug: false
    log_level: INFO
    database:
      host: postgres-service
      port: 5432
      database: marketing_db
      username: postgres
    redis:
      host: redis-service
      port: 6379
      db: 0
    scraping:
      concurrent_requests: 10
      delay_range: [1, 3]
    email:
      batch_size: 100
      delay_between_emails: 10
---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: marketing-secrets
  namespace: marketing-system
type: Opaque
data:
  database-password: <base64-encoded-password>
  redis-password: <base64-encoded-password>
  jwt-secret: <base64-encoded-jwt-secret>
---
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: marketing-system
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:13
        env:
        - name: POSTGRES_DB
          value: marketing_db
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: marketing-secrets
              key: database-password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "16Gi"
            cpu: "4"
          limits:
            memory: "32Gi"
            cpu: "8"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: marketing-system
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
---
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: marketing-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:6-alpine
        command:
        - redis-server
        - --requirepass
        - $(REDIS_PASSWORD)
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: marketing-secrets
              key: redis-password
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            memory: "16Gi"
            cpu: "4"
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: marketing-system
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
---
# k8s/api.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: marketing-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: marketing-system:latest
        command: ["python", "src/main.py", "--api-only"]
        env:
        - name: DATABASE_URL
          value: postgresql://postgres:$(DATABASE_PASSWORD)@postgres-service:5432/marketing_db
        - name: REDIS_URL
          value: redis://:$(REDIS_PASSWORD)@redis-service:6379/0
        envFrom:
        - configMapRef:
            name: marketing-config
        - secretRef:
            name: marketing-secrets
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: marketing-system
spec:
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: marketing-ingress
  namespace: marketing-system
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - marketing.example.com
    secretName: marketing-tls
  rules:
  - host: marketing.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

### Kubernetes部署脚本

```bash
#!/bin/bash
# deploy_k8s.sh

set -e

NAMESPACE="marketing-system"
DOCKER_REGISTRY="your-registry.com"
DOCKER_TAG="latest"

echo "🚀 Kubernetes部署开始..."

# 构建并推送镜像
build_and_push() {
    echo "🏗️ 构建Docker镜像..."

    docker build -t $DOCKER_REGISTRY/marketing-system:$DOCKER_TAG .

    echo "📤 推送镜像到注册表..."
    docker push $DOCKER_REGISTRY/marketing-system:$DOCKER_TAG

    echo "✅ 镜像构建和推送完成"
}

# 创建命名空间
create_namespace() {
    echo "📋 创建Kubernetes命名空间..."

    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

    echo "✅ 命名空间创建完成"
}

# 应用配置
apply_configs() {
    echo "⚙️ 应用Kubernetes配置..."

    # 更新镜像标签
    sed -i "s|marketing-system:latest|$DOCKER_REGISTRY/marketing-system:$DOCKER_TAG|g" k8s/*.yaml

    # 应用配置
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secret.yaml
    kubectl apply -f k8s/postgres.yaml
    kubectl apply -f k8s/redis.yaml

    echo "✅ 配置应用完成"
}

# 部署应用
deploy_app() {
    echo "🚀 部署应用..."

    kubectl apply -f k8s/api.yaml
    kubectl apply -f k8s/web.yaml
    kubectl apply -f k8s/ingress.yaml

    echo "✅ 应用部署完成"
}

# 等待部署完成
wait_for_deployment() {
    echo "⏳ 等待部署完成..."

    kubectl wait --for=condition=available --timeout=300s deployment/api -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=300s deployment/web -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=300s deployment/postgres -n $NAMESPACE
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n $NAMESPACE

    echo "✅ 部署完成"
}

# 验证部署
verify_deployment() {
    echo "🔍 验证部署状态..."

    kubectl get pods -n $NAMESPACE
    kubectl get services -n $NAMESPACE
    kubectl get ingress -n $NAMESPACE

    echo "✅ 验证完成"
}

# 主函数
main() {
    build_and_push
    create_namespace
    apply_configs
    deploy_app
    wait_for_deployment
    verify_deployment

    echo "🎉 Kubernetes部署完成！"
    echo ""
    echo "📊 访问信息:"
    kubectl get ingress -n $NAMESPACE
}

main "$@"
```

## 高可用配置

### 数据库高可用

```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  # PostgreSQL主节点
  postgres-master:
    image: postgres:13
    environment:
      - POSTGRES_DB=marketing_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_REPLICATION_MODE=master
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=repl_password
    volumes:
      - postgres_master_data:/var/lib/postgresql/data
      - ./postgres/master.conf:/etc/postgresql/postgresql.conf
      - ./postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf
    ports:
      - "5432:5432"
    networks:
      - marketing-network

  # PostgreSQL从节点
  postgres-slave:
    image: postgres:13
    environment:
      - POSTGRES_MASTER_SERVICE=postgres-master
      - POSTGRES_REPLICATION_MODE=slave
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=repl_password
      - PGUSER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_slave_data:/var/lib/postgresql/data
    depends_on:
      - postgres-master
    networks:
      - marketing-network

  # Redis哨兵
  redis-sentinel:
    image: redis:6-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./redis/sentinel.conf:/etc/redis/sentinel.conf
    depends_on:
      - redis-master
    networks:
      - marketing-network

networks:
  marketing-network:
    driver: bridge

volumes:
  postgres_master_data:
  postgres_slave_data:
```

### 负载均衡配置

```nginx
# nginx/ha_nginx.conf
upstream api_backend {
    least_conn;
    server api-1:8000 max_fails=3 fail_timeout=30s;
    server api-2:8000 max_fails=3 fail_timeout=30s;
    server api-3:8000 max_fails=3 fail_timeout=30s backup;
}

upstream web_backend {
    least_conn;
    server web-1:3000 max_fails=3 fail_timeout=30s;
    server web-2:3000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name marketing.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name marketing.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # API路由
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 健康检查
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;

        # 超时设置
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Web界面路由
    location / {
        proxy_pass http://web_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态文件
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 健康检查端点
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

## 安全配置

### SSL/TLS配置

```bash
#!/bin/bash
# setup_ssl.sh

DOMAIN="marketing.example.com"
SSL_DIR="/etc/nginx/ssl"

# 创建SSL目录
sudo mkdir -p $SSL_DIR

# 生成私钥
sudo openssl genrsa -out $SSL_DIR/key.pem 2048

# 生成证书签名请求
sudo openssl req -new -key $SSL_DIR/key.pem -out $SSL_DIR/cert.csr -subj "/C=CN/ST=State/L=City/O=Organization/CN=$DOMAIN"

# 生成自签名证书（开发环境）
sudo openssl x509 -req -days 365 -in $SSL_DIR/cert.csr -signkey $SSL_DIR/key.pem -out $SSL_DIR/cert.pem

# 或者使用Let's Encrypt（生产环境）
if [ "$ENVIRONMENT" = "production" ]; then
    sudo apt install certbot python3-certbot-nginx
    sudo certbot --nginx -d $DOMAIN
fi

echo "✅ SSL配置完成"
```

### 防火墙配置

```bash
#!/bin/bash
# setup_firewall.sh

# 启用UFW
sudo ufw enable

# 允许SSH
sudo ufw allow ssh

# 允许HTTP和HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允许数据库访问（仅内部网络）
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 10.0.0.0/8 to any port 6379

# 拒绝其他连接
sudo ufw default deny incoming
sudo ufw default allow outgoing

echo "✅ 防火墙配置完成"
```

### 应用安全配置

```python
# src/security/security_middleware.py
import asyncio
import hashlib
import hmac
import time
from typing import Callable, Dict, Any
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from passlib.context import CryptContext

class SecurityMiddleware:
    """安全中间件"""

    def __init__(self, app):
        self.app = app
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = os.getenv("JWT_SECRET_KEY")

    async def rate_limiting(self, request: Request, call_next: Callable):
        """速率限制"""
        client_ip = request.client.host
        current_time = time.time()

        # 检查是否超过速率限制
        if self._is_rate_limited(client_ip, current_time):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        response = await call_next(request)
        return response

    async def jwt_authentication(self, request: Request, call_next: Callable):
        """JWT认证"""
        if request.url.path.startswith("/api/"):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header missing")

            try:
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
                request.state.user = payload
            except jwt.PyJWTError:
                raise HTTPException(status_code=401, detail="Invalid token")

        response = await call_next(request)
        return response

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """检查是否超过速率限制"""
        # 实现速率限制逻辑
        # 可以使用Redis存储请求计数
        return False

    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return self.pwd_context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(password, hashed_password)

    def create_access_token(self, data: dict) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = time.time() + 3600  # 1小时过期
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm="HS256")
        return encoded_jwt
```

## 性能优化

### 数据库优化

```sql
-- database/optimization.sql

-- 创建索引
CREATE INDEX CONCURRENTLY idx_scraping_results_created_at ON scraping_results(created_at);
CREATE INDEX CONCURRENTLY idx_contacts_email ON contacts(email);
CREATE INDEX CONCURRENTLY idx_contacts_phone ON contacts(phone);
CREATE INDEX CONCURRENTLY idx_email_campaigns_created_at ON email_campaigns(created_at);

-- 分区表（大数据量）
CREATE TABLE scraping_results_2024_01 PARTITION OF scraping_results
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- 物化视图
CREATE MATERIALIZED VIEW contact_stats AS
SELECT
    COUNT(*) as total_contacts,
    COUNT(DISTINCT email) as unique_emails,
    COUNT(DISTINCT phone) as unique_phones,
    DATE(created_at) as date
FROM contacts
GROUP BY DATE(created_at);

-- 创建唯一约束
ALTER TABLE contacts ADD CONSTRAINT unique_email_phone UNIQUE (email, phone) WHERE email IS NOT NULL AND phone IS NOT NULL;

-- 优化配置
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
```

### 缓存策略

```python
# src/cache/cache_manager.py
import json
import pickle
from typing import Any, Optional, Union
import redis
import asyncio
from functools import wraps

class CacheManager:
    """缓存管理器"""

    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url, decode_responses=False)

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            data = self.redis_client.get(key)
            if data:
                return pickle.loads(data)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        try:
            data = pickle.dumps(value)
            return self.redis_client.setex(key, ttl, data)
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache clear pattern error: {e}")
        return 0

def cached(ttl: int = 3600, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator

# 使用示例
@cached(ttl=1800, key_prefix="scraping")
async def get_scraping_results(date: str):
    """获取爬取结果（缓存30分钟）"""
    # 实际的数据获取逻辑
    pass
```

## 监控和运维

### Prometheus监控配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'marketing-api'
    static_configs:
      - targets: ['api-1:8000', 'api-2:8000', 'api-3:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']

  - job_name: 'docker'
    static_configs:
      - targets: ['docker-exporter:9323']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana仪表板

```json
{
  "dashboard": {
    "title": "营销自动化系统监控",
    "panels": [
      {
        "title": "API请求率",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "API响应时间",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "数据库连接数",
        "type": "singlestat",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "Connections"
          }
        ]
      },
      {
        "title": "邮件发送成功率",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(emails_sent_total[5m]) / rate(emails_total[5m]) * 100",
            "legendFormat": "Success Rate"
          }
        ]
      }
    ]
  }
}
```

### 自动化运维脚本

```bash
#!/bin/bash
# maintenance.sh

set -e

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 数据库备份
backup_database() {
    echo "🗄️ 备份数据库..."

    mkdir -p $BACKUP_DIR/database

    docker-compose exec -T postgres pg_dump -U postgres marketing_db | gzip > $BACKUP_DIR/database/backup_$DATE.sql.gz

    echo "✅ 数据库备份完成"
}

# 清理旧日志
cleanup_logs() {
    echo "🧹 清理旧日志..."

    # 删除30天前的日志
    find logs/ -name "*.log" -mtime +30 -delete

    # 清理Docker日志
    docker system prune -f

    echo "✅ 日志清理完成"
}

# 健康检查
health_check() {
    echo "🔍 执行健康检查..."

    # 检查服务状态
    services=("api" "web" "postgres" "redis")
    for service in "${services[@]}"; do
        if docker-compose ps $service | grep -q "Up"; then
            echo "✅ $service 服务正常"
        else
            echo "❌ $service 服务异常"
            # 发送告警
            send_alert "$service 服务异常"
        fi
    done

    # 检查磁盘空间
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $disk_usage -gt 80 ]; then
        echo "⚠️ 磁盘使用率过高: $disk_usage%"
        send_alert "磁盘使用率过高: $disk_usage%"
    fi
}

# 发送告警
send_alert() {
    message="$1"

    # 发送邮件告警
    curl -X POST "https://api.mailgun.net/v3/your-domain/messages" \
        -u "api:your-api-key" \
        -F from="alert@marketing.example.com" \
        -F to="admin@marketing.example.com" \
        -F subject="营销系统告警" \
        -F text="告警信息: $message"

    # 发送Slack通知
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"营销系统告警: $message\"}" \
        "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
}

# 主函数
main() {
    echo "🔧 执行维护任务..."
    echo "时间: $(date)"

    backup_database
    cleanup_logs
    health_check

    echo "✅ 维护任务完成"
}

main "$@"
```

## 故障排除

### 常见问题诊断

```bash
#!/bin/bash
# troubleshoot.sh

echo "🔍 营销系统故障诊断工具"
echo "=========================="

# 检查系统资源
echo "📊 系统资源使用情况:"
echo "CPU使用率:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
echo "内存使用率:"
free | grep Mem | awk '{printf "%.2f%%\n", $3/$2 * 100.0}'
echo "磁盘使用率:"
df -h | awk '$NF=="/"{printf "%s\n", $5}'

# 检查Docker容器状态
echo -e "\n🐳 Docker容器状态:"
docker-compose ps

# 检查服务健康状态
echo -e "\n🔍 服务健康检查:"
services=("api" "web" "postgres" "redis")
for service in "${services[@]}"; do
    health=$(docker-compose exec -T $service curl -f http://localhost/health 2>/dev/null || echo "unhealthy")
    echo "$service: $health"
done

# 检查网络连接
echo -e "\n🌐 网络连接检查:"
ping -c 3 google.com > /dev/null 2>&1 && echo "✅ 外网连接正常" || echo "❌ 外网连接异常"
netstat -tlnp | grep :80 > /dev/null 2>&1 && echo "✅ 80端口监听正常" || echo "❌ 80端口未监听"
netstat -tlnp | grep :443 > /dev/null 2>&1 && echo "✅ 443端口监听正常" || echo "❌ 443端口未监听"

# 检查数据库连接
echo -e "\n🗄️ 数据库连接检查:"
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ PostgreSQL连接正常"
else
    echo "❌ PostgreSQL连接异常"
fi

if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis连接正常"
else
    echo "❌ Redis连接异常"
fi

# 检查日志中的错误
echo -e "\n📝 最近的错误日志:"
echo "API服务错误:"
docker-compose logs --tail=20 api | grep -i error || echo "无错误日志"
echo "数据库错误:"
docker-compose logs --tail=20 postgres | grep -i error || echo "无错误日志"

# 生成诊断报告
echo -e "\n📋 生成诊断报告..."
report_file="diagnostic_report_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "营销系统诊断报告"
    echo "生成时间: $(date)"
    echo "========================"

    echo -e "\n系统信息:"
    uname -a

    echo -e "\nDocker信息:"
    docker version

    echo -e "\n容器状态:"
    docker-compose ps

    echo -e "\n资源使用:"
    docker stats --no-stream

    echo -e "\n网络配置:"
    ip addr show

    echo -e "\n最近的错误日志:"
    docker-compose logs --tail=50 | grep -i error
} > $report_file

echo "✅ 诊断报告已生成: $report_file"

echo -e "\n🔧 建议的修复措施:"
echo "1. 检查容器资源限制"
echo "2. 验证网络配置"
echo "3. 检查磁盘空间"
echo "4. 查看详细错误日志"
echo "5. 重启异常服务"
```

这份企业级部署指南提供了从开发到生产环境的完整部署流程，包括容器化、Kubernetes、高可用配置、安全配置、性能优化、监控运维和故障排除等方面的详细说明。