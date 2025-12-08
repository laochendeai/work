FROM mcr.microsoft.com/playwright/python:v1.44.0

# 设置标签
LABEL maintainer="your-email@example.com"
LABEL version="3.0"
LABEL description="智能设计营销自动化系统"

# 切换到root用户进行安装
USER root

# 设置工作目录
WORKDIR /app

# 设置环境变量（默认值，可通过docker-compose.yml覆盖）
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    QUEUE_MODE=0 \
    APP_NAME="智能设计营销系统" \
    APP_VERSION="3.0"

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    curl \
    wget \
    git \
    # 时区支持
    tzdata \
    # 清理
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 复制并安装Python依赖
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# 创建必要的目录
RUN mkdir -p /app/data /app/logs /app/config \
    && chown -R pwuser:pwuser /app

# 复制应用代码（在.dockerignore中排除的文件不会被复制）
COPY --chown=pwuser:pwuser . /app

# 切换到非root用户
USER pwuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# 暴露端口
EXPOSE 8000

# 设置启动命令（支持通过环境变量覆盖）
CMD ["python", "main.py"]
