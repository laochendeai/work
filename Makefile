# Makefile for 智能设计营销自动化系统
# 实现零感知、零修改的容器化部署

.PHONY: help build run stop clean test logs shell deploy-dev deploy-test deploy-prod

# 默认目标
help:
	@echo "智能设计营销自动化系统 - Docker命令"
	@echo ""
	@echo "基础命令:"
	@echo "  build          构建Docker镜像"
	@echo "  run            运行容器（开发模式）"
	@echo "  stop           停止所有容器"
	@echo "  restart        重启服务"
	@echo "  clean          清理容器和镜像"
	@echo "  logs           查看应用日志"
	@echo "  shell          进入容器shell"
	@echo "  test           运行测试"
	@echo ""
	@echo "部署命令:"
	@echo "  deploy-dev     部署到开发环境"
	@echo "  deploy-test    部署到测试环境"
	@echo "  deploy-prod    部署到生产环境"
	@echo ""
	@echo "其他命令:"
	@echo "  status         查看服务状态"
	@echo "  pull           拉取最新基础镜像"
	@echo "  backup         备份数据"

# 变量定义
PROJECT_NAME ?= 智能设计营销系统
VERSION ?= 3.0
ENV_FILE ?= .env
COMPOSE_FILE ?= docker-compose.yml
DOCKER_COMPOSE ?= docker-compose

# 基础命令
build:
	@echo "构建 Docker 镜像..."
	docker build -t $(PROJECT_NAME):$(VERSION) .
	docker tag $(PROJECT_NAME):$(VERSION) $(PROJECT_NAME):latest

run: start
	@echo "启动应用服务..."

start:
	$(DOCKER_COMPOSE) up --build -d

stop:
	@echo "停止所有服务..."
	$(DOCKER_COMPOSE) down

restart: stop start

clean:
	@echo "清理容器和镜像..."
	$(DOCKER_COMPOSE) down -v || true
	docker rmi $(PROJECT_NAME):$(VERSION) || true
	docker rmi $(PROJECT_NAME):latest || true
	docker system prune -f

logs:
	$(DOCKER_COMPOSE) logs -f app

shell:
	$(DOCKER_COMPOSE) exec app /bin/bash

test:
	$(DOCKER_COMPOSE) exec app python test_actions.py

status:
	@echo "服务状态:"
	$(DOCKER_COMPOSE) ps

pull:
	@echo "拉取最新基础镜像..."
	docker pull mcr.microsoft.com/playwright/python:v1.44.0
	docker pull redis:7-alpine
	docker pull prom/prometheus:latest

# 部署命令
deploy-dev:
	@echo "部署到开发环境..."
	./deploy.sh dev

deploy-test:
	@echo "部署到测试环境..."
	./deploy.sh test

deploy-prod:
	@echo "部署到生产环境..."
	./deploy.sh prod

# 数据备份
backup:
	@echo "备份数据..."
	mkdir -p backups
	docker run --rm -v $(PWD)/data:/data -v $(PWD)/backups:/backup alpine \
		tar czf /backup/data-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .

# 数据恢复
restore:
	@echo "请指定备份文件: make restore BACKUP=backup-file.tar.gz"
	@if [ -z "$(BACKUP)" ]; then exit 1; fi
	docker run --rm -v $(PWD)/data:/data -v $(PWD)/backups:/backup alpine \
		tar xzf /backup/$(BACKUP) -C /data

# 开发环境快速启动
dev:
	@if [ ! -f .env ]; then \
		echo "创建 .env 文件..."; \
		cp .env.template .env; \
	fi
	$(MAKE) build
	$(MAKE) run
	@echo ""
	@echo "开发环境已启动！"
	@echo "应用地址: http://localhost:8000"
	@echo "查看日志: make logs"
	@echo "停止服务: make stop"

# 生产环境发布
release: clean
	@echo "发布新版本 $(VERSION)..."
	$(MAKE) build
	./deploy.sh prod
	@echo "发布完成！"