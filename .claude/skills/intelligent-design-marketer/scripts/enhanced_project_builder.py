#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版项目构建器 - 智能设计营销自动化系统高级版本
支持Docker容器化、Web界面、数据可视化等高级功能
"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import subprocess


class EnhancedProjectBuilder:
    """增强版项目构建器"""

    def __init__(self, project_name: str, project_type: str = "enhanced", features: List[str] = None):
        self.project_name = project_name
        self.project_type = project_type.lower()
        self.features = features or []
        self.project_root = Path.cwd() / project_name

        # 支持的功能特性
        self.available_features = {
            'docker': 'Docker容器化支持',
            'web_interface': 'Web管理界面',
            'data_visualization': '数据可视化面板',
            'api_service': 'RESTful API服务',
            'monitoring': '性能监控和告警',
            'redis_cache': 'Redis缓存支持',
            'database_migration': '数据库迁移工具',
            'ci_cd': 'CI/CD自动化流程',
            'testing': '完整测试套件',
            'documentation': 'API文档生成'
        }

        # 验证项目类型
        if self.project_type not in ["basic", "comprehensive", "enhanced", "enterprise"]:
            raise ValueError(f"不支持的项目类型: {project_type}")

        # 验证功能特性
        for feature in self.features:
            if feature not in self.available_features:
                print(f"⚠️ 警告: 未知功能特性 '{feature}'，将被忽略")

    def create_enhanced_project_structure(self):
        """创建增强版项目结构"""
        print("🏗️ 创建增强版项目结构...")

        # 基础目录结构
        base_directories = [
            "src/scrapers",
            "src/extractors",
            "src/email_marketing",
            "src/data_processing",
            "src/utils",
            "src/api",          # API服务模块
            "src/web",          # Web界面模块
            "src/monitoring",   # 监控模块
            "config",
            "config/environments",  # 环境配置
            "tests",
            "tests/integration",
            "tests/performance",
            "tests/api",
            "templates/emails",
            "templates/web",
            "data/raw",
            "data/processed",
            "logs",
            "docs",
            "docs/api",
            "scripts",
            "docker",           # Docker相关文件
            "deployments",      # 部署配置
            "monitoring",       # 监控配置
            ".github/workflows" # CI/CD工作流
        ]

        for directory in base_directories:
            (self.project_root / directory).mkdir(parents=True, exist_ok=True)
            print(f"✓ 创建目录: {directory}")

        # 功能特定目录
        if 'docker' in self.features:
            docker_dirs = ["docker/nginx", "docker/postgres", "docker/redis"]
            for directory in docker_dirs:
                (self.project_root / directory).mkdir(parents=True, exist_ok=True)

        if 'monitoring' in self.features:
            monitoring_dirs = ["monitoring/prometheus", "monitoring/grafana"]
            for directory in monitoring_dirs:
                (self.project_root / directory).mkdir(parents=True, exist_ok=True)

    def create_enhanced_config(self):
        """创建增强版配置文件"""
        print("⚙️ 创建增强版配置文件...")

        # 主配置文件
        main_config = {
            "project_info": {
                "name": self.project_name,
                "type": self.project_type,
                "created_at": datetime.now().isoformat(),
                "version": "2.0.0",
                "features": self.features,
                "environment": "development"
            },
            "scraping": {
                "user_agents": self._load_user_agents(),
                "delay_range": [1, 3],
                "timeout": 30,
                "max_retries": 3,
                "concurrent_requests": 10,
                "proxy_rotation": True,
                "respect_robots": True
            },
            "data_sources": {
                "government": {
                    "enabled": True,
                    "sources": [
                        "ccgp.gov.cn",
                        "chinabidding.com.cn",
                        "bidcenter.com.cn"
                    ],
                    "search_keywords": ["弱电", "智能化", "安防", "网络建设", "系统集成"]
                },
                "education": {
                    "enabled": True if 'web_interface' in self.features else False,
                    "sources": [
                        "edu.cn",
                        "university.edu.cn"
                    ]
                },
                "enterprise": {
                    "enabled": True if 'comprehensive' in self.features else False,
                    "sources": [
                        "tenders.com",
                        "globaltenders.com"
                    ]
                }
            },
            "extraction": {
                "enabled_fields": ["phone", "email", "name", "department", "company", "budget", "deadline"],
                "ml_models": {
                    "enabled": True if self.project_type in ["comprehensive", "enhanced", "enterprise"] else False,
                    "confidence_threshold": 0.7,
                    "model_path": "models/extraction_model.pkl"
                },
                "validation_rules": {
                    "email_domains": ["qq.com", "163.com", "126.com", "gmail.com", "outlook.com"],
                    "phone_min_length": 11
                }
            },
            "email": {
                "smtp_providers": {
                    "qq": {
                        "smtp_server": "smtp.qq.com",
                        "smtp_port": 587,
                        "use_tls": True
                    },
                    "gmail": {
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "use_tls": True
                    }
                },
                "sending": {
                    "batch_size": 50,
                    "delay_between_emails": 5,
                    "delay_between_batches": 300,
                    "tracking_enabled": True
                },
                "templates": {
                    "default_template": "default",
                    "industry_templates": ["government", "education", "enterprise"]
                }
            },
            "database": {
                "type": "postgresql" if 'enterprise' in self.features else "sqlite",
                "postgresql": {
                    "host": "localhost",
                    "port": 5432,
                    "database": f"{self.project_name}_db",
                    "username": f"{self.project_name}_user",
                    "password": "change_me"
                },
                "sqlite": {
                    "path": "data/marketing_data.db"
                }
            },
            "cache": {
                "enabled": 'redis_cache' in self.features,
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "db": 0,
                    "ttl": 3600
                }
            },
            "api": {
                "enabled": 'api_service' in self.features,
                "host": "0.0.0.0",
                "port": 8000,
                "auth_required": True,
                "rate_limiting": True,
                "cors_origins": ["http://localhost:3000"]
            },
            "web_interface": {
                "enabled": 'web_interface' in self.features,
                "host": "0.0.0.0",
                "port": 3000,
                "debug": True
            },
            "monitoring": {
                "enabled": 'monitoring' in self.features,
                "prometheus": {
                    "port": 9090,
                    "metrics_path": "/metrics"
                },
                "grafana": {
                    "port": 3001,
                    "admin_password": "admin123"
                }
            }
        }

        # 保存主配置文件
        config_file = self.project_root / "config" / "project_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(main_config, f, ensure_ascii=False, indent=2)
        print(f"✓ 创建主配置文件: config/project_config.json")

        # 环境配置文件
        self._create_environment_configs()

        # Docker配置
        if 'docker' in self.features:
            self._create_docker_configs()

        # 监控配置
        if 'monitoring' in self.features:
            self._create_monitoring_configs()

    def _load_user_agents(self) -> List[str]:
        """加载User-Agent列表"""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]

    def _create_environment_configs(self):
        """创建环境配置文件"""
        environments = ['development', 'staging', 'production']

        for env in environments:
            env_config = {
                "environment": env,
                "debug": env == 'development',
                "log_level": "DEBUG" if env == 'development' else "INFO",
                "database": {
                    "echo": env == 'development'
                }
            }

            env_file = self.project_root / "config" / "environments" / f"{env}.yaml"
            with open(env_file, 'w', encoding='utf-8') as f:
                yaml.dump(env_config, f, default_flow_style=False, allow_unicode=True)

        print(f"✓ 创建环境配置文件: config/environments/")

    def _create_docker_configs(self):
        """创建Docker配置"""
        # Dockerfile
        dockerfile_content = '''FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# 暴露端口
EXPOSE 8000 3000

# 启动命令
CMD ["python", "src/main.py"]
'''

        dockerfile_path = self.project_root / "Dockerfile"
        with open(dockerfile_path, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)

        # docker-compose.yml
        docker_compose_content = f'''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/{self.project_name}_db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB={self.project_name}_db
      - POSTGRES_USER={self.project_name}_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./docker/nginx/ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
'''

        docker_compose_path = self.project_root / "docker-compose.yml"
        with open(docker_compose_path, 'w', encoding='utf-8') as f:
            f.write(docker_compose_content)

        print("✓ 创建Docker配置文件: Dockerfile, docker-compose.yml")

    def _create_monitoring_configs(self):
        """创建监控配置"""
        # Prometheus配置
        prometheus_config = {
            "global": {
                "scrape_interval": "15s"
            },
            "scrape_configs": [
                {
                    "job_name": f"{self.project_name}",
                    "static_configs": [
                        {
                            "targets": ["app:8000"]
                        }
                    ]
                }
            ]
        }

        prometheus_file = self.project_root / "monitoring" / "prometheus.yml"
        with open(prometheus_file, 'w', encoding='utf-8') as f:
            yaml.dump(prometheus_config, f, default_flow_style=False)

        # Grafana配置
        grafana_config = {
            "apiVersion": 1,
            "datasources": [
                {
                    "name": "Prometheus",
                    "type": "prometheus",
                    "url": "http://prometheus:9090",
                    "access": "proxy",
                    "isDefault": True
                }
            ]
        }

        grafana_file = self.project_root / "monitoring" / "grafana" / "datasources.yml"
        grafana_file.parent.mkdir(exist_ok=True)
        with open(grafana_file, 'w', encoding='utf-8') as f:
            yaml.dump(grafana_config, f, default_flow_style=False)

        print("✓ 创建监控配置文件")

    def create_enhanced_main_module(self):
        """创建增强版主程序模块"""
        print("🚀 创建增强版主程序模块...")

        main_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{self.project_name} - 增强版智能设计营销自动化系统
支持Web界面、API服务、监控等高级功能
"""

import asyncio
import json
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("⚠️ FastAPI未安装，API功能将不可用")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis未安装，缓存功能将不可用")

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger
from src.monitoring.metrics import MetricsCollector
from src.scrapers.enhanced_scraper_manager import EnhancedScraperManager
from src.extractors.enhanced_contact_extractor import EnhancedContactExtractor
from src.email_marketing.enhanced_email_sender import EnhancedEmailSender


class EnhancedMarketingSystem:
    """增强版营销自动化系统"""

    def __init__(self, config_path: str = "config/project_config.json"):
        """初始化系统"""
        self.config = ConfigLoader(config_path).load_config()
        self.logger = setup_logger("enhanced_system", "logs/enhanced_system.log")

        # 初始化组件
        self.scraper_manager = None
        self.extractor = None
        self.email_sender = None
        self.metrics_collector = None
        self.redis_client = None

        # API应用
        self.app = None
        self.server = None

        self._initialize_components()

    def _initialize_components(self):
        """初始化系统组件"""
        try:
            # 初始化监控
            if self.config.get('monitoring', {}).get('enabled', False):
                self.metrics_collector = MetricsCollector()
                self.logger.info("监控组件初始化完成")

            # 初始化Redis缓存
            if self.config.get('cache', {}).get('enabled', False) and REDIS_AVAILABLE:
                redis_config = self.config['cache']['redis']
                self.redis_client = redis.Redis(
                    host=redis_config['host'],
                    port=redis_config['port'],
                    db=redis_config['db'],
                    decode_responses=True
                )
                self.logger.info("Redis缓存初始化完成")

            # 初始化爬虫管理器
            self.scraper_manager = EnhancedScraperManager(self.config['scraping'])

            # 初始化信息提取器
            self.extractor = EnhancedContactExtractor(self.config['extraction'])

            # 初始化邮件发送器
            self.email_sender = EnhancedEmailSender(self.config['email'])

            self.logger.info("增强版系统初始化完成")

        except Exception as e:
            self.logger.error(f"系统组件初始化失败: {{e}}")
            raise

    async def start_api_server(self):
        """启动API服务器"""
        if not API_AVAILABLE or not self.config.get('api', {}).get('enabled', False):
            return

        @asynccontextmanager
        async def lifespan(app):
            # 启动时执行
            self.logger.info("API服务器启动")
            yield
            # 关闭时执行
            self.logger.info("API服务器关闭")

        # 创建FastAPI应用
        self.app = FastAPI(
            title=f"{self.project_name} API",
            description="智能设计营销自动化系统API",
            version="2.0.0",
            lifespan=lifespan
        )

        # 添加CORS中间件
        if self.config.get('api', {}).get('cors_origins'):
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config['api']['cors_origins'],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # 注册API路由
        self._register_api_routes()

        # 启动服务器
        api_config = self.config['api']
        self.server = uvicorn.Server(
            uvicorn.Config(
                self.app,
                host=api_config['host'],
                port=api_config['port'],
                log_level="info"
            )
        )

        await self.server.serve()

    def _register_api_routes(self):
        """注册API路由"""
        from src.api.routes.scraping import router as scraping_router
        from src.api.routes.extraction import router as extraction_router
        from src.api.routes.email import router as email_router
        from src.api.routes.monitoring import router as monitoring_router

        # 注册路由模块
        if Path("src/api/routes/scraping.py").exists():
            self.app.include_router(scraping_router, prefix="/api/v1/scraping")
        if Path("src/api/routes/extraction.py").exists():
            self.app.include_router(extraction_router, prefix="/api/v1/extraction")
        if Path("src/api/routes/email.py").exists():
            self.app.include_router(email_router, prefix="/api/v1/email")
        if Path("src/api/routes/monitoring.py").exists():
            self.app.include_router(monitoring_router, prefix="/api/v1/monitoring")

    async def run_scraping_task(self):
        """执行增强版爬取任务"""
        try:
            self.logger.info("开始执行增强版爬取任务")

            # 执行爬取
            results = await self.scraper_manager.run_all_scrapers()

            # 更新指标
            if self.metrics_collector:
                self.metrics_collector.record_scraping_results(results)

            # 缓存结果
            if self.redis_client:
                await self._cache_scraping_results(results)

            self.logger.info(f"增强版爬取任务完成，获取 {{len(results)}} 条数据")
            return results

        except Exception as e:
            self.logger.error(f"增强版爬取任务失败: {{e}}")
            raise

    async def run_extraction_task(self):
        """执行增强版信息提取任务"""
        try:
            self.logger.info("开始执行增强版信息提取任务")

            # 获取待处理数据
            unprocessed_data = await self._get_unprocessed_data()

            # 执行信息提取
            extracted_contacts = []
            for data in unprocessed_data:
                contacts = await self.extractor.extract_contacts_enhanced(data['content'])
                extracted_contacts.extend(contacts)

            # 更新指标
            if self.metrics_collector:
                self.metrics_collector.record_extraction_results(extracted_contacts)

            self.logger.info(f"增强版信息提取任务完成，提取 {{len(extracted_contacts)}} 个联系人")
            return extracted_contacts

        except Exception as e:
            self.logger.error(f"增强版信息提取任务失败: {{e}}")
            raise

    async def run_email_marketing_task(self):
        """执行增强版邮件营销任务"""
        try:
            self.logger.info("开始执行增强版邮件营销任务")

            # 获取联系人列表
            contacts = await self._get_contacts_for_email()

            # 发送个性化邮件
            results = await self.email_sender.send_batch_emails_enhanced(contacts)

            # 更新指标
            if self.metrics_collector:
                self.metrics_collector.record_email_results(results)

            self.logger.info(f"增强版邮件营销任务完成，发送 {{len(contacts)}} 封邮件")
            return results

        except Exception as e:
            self.logger.error(f"增强版邮件营销任务失败: {{e}}")
            raise

    async def _cache_scraping_results(self, results):
        """缓存爬取结果"""
        if not self.redis_client:
            return

        try:
            cache_key = f"scraping_results:{{datetime.now().strftime('%Y%m%d_%H%M%S')}}"
            self.redis_client.setex(
                cache_key,
                3600,  # 1小时过期
                json.dumps(results, ensure_ascii=False)
            )
        except Exception as e:
            self.logger.warning(f"缓存爬取结果失败: {{e}}")

    async def run_system(self):
        """运行增强版系统"""
        self.logger.info("启动增强版智能设计营销自动化系统")

        # 创建任务列表
        tasks = []

        # API服务任务
        if self.config.get('api', {}).get('enabled', False):
            tasks.append(self.start_api_server())

        # 爬取任务
        tasks.append(self.run_scraping_task())

        # 信息提取任务
        tasks.append(self.run_extraction_task())

        # 邮件营销任务
        tasks.append(self.run_email_marketing_task())

        try:
            # 并行执行任务
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            self.logger.info("系统被用户中断")
        except Exception as e:
            self.logger.error(f"系统运行出错: {{e}}")
        finally:
            # 清理资源
            await self._cleanup()

    async def _cleanup(self):
        """清理资源"""
        self.logger.info("正在清理系统资源...")

        if self.redis_client:
            self.redis_client.close()

        if self.server:
            await self.server.shutdown()

    async def _get_unprocessed_data(self):
        """获取未处理的数据"""
        # 这里应该从数据库获取未处理的数据
        # 暂时返回空列表
        return []

    async def _get_contacts_for_email(self):
        """获取待发送邮件的联系人"""
        # 这里应该从数据库获取待发送邮件的联系人
        # 暂时返回空列表
        return []


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="增强版智能设计营销自动化系统")
    parser.add_argument("--config", default="config/project_config.json", help="配置文件路径")
    parser.add_argument("--api-only", action="store_true", help="仅启动API服务")
    parser.add_argument("--scraping-only", action="store_true", help="仅执行爬取任务")
    parser.add_argument("--email-only", action="store_true", help="仅执行邮件营销任务")

    args = parser.parse_args()

    try:
        system = EnhancedMarketingSystem(args.config)

        if args.api_only:
            await system.start_api_server()
        elif args.scraping_only:
            await system.run_scraping_task()
        elif args.email_only:
            await system.run_email_marketing_task()
        else:
            await system.run_system()

    except KeyboardInterrupt:
        print("\\n系统已停止")
    except Exception as e:
        print(f"系统启动失败: {{e}}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
'''

        main_file = self.project_root / "src" / "main.py"
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(main_content)

        print(f"✓ 创建增强版主程序: src/main.py")

    def create_enhanced_requirements(self):
        """创建增强版依赖文件"""
        print("📦 创建增强版依赖文件...")

        basic_requirements = [
            "requests>=2.28.0",
            "beautifulsoup4>=4.11.0",
            "lxml>=4.9.0",
            "pandas>=1.5.0",
            "python-dotenv>=0.19.0",
            "schedule>=1.2.0",
            "email-validator>=2.0.0",
            "jinja2>=3.1.0",
            "pyyaml>=6.0"
        ]

        enhanced_requirements = [
            "fastapi>=0.95.0",
            "uvicorn[standard]>=0.20.0",
            "sqlalchemy>=2.0.0",
            "alembic>=1.10.0",
            "asyncpg>=0.28.0",
            "redis>=4.5.0",
            "celery>=5.2.0",
            "prometheus-client>=0.16.0",
            "aiofiles>=23.0.0",
            "python-multipart>=0.0.6",
            "python-jose[cryptography]>=3.3.0",
            "passlib[bcrypt]>=1.7.4",
            "streamlit>=1.25.0",  # 用于Web界面
            "plotly>=5.15.0",      # 用于数据可视化
            "dash>=2.10.0",        # 另一个Web框架选项
            "pytest>=7.2.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.3.0"
        ]

        enterprise_requirements = [
            "psycopg2-binary>=2.9.0",
            "elasticsearch>=8.8.0",
            "kafka-python>=2.0.0",
            "boto3>=1.26.0",        # AWS SDK
            "google-cloud-storage>=2.8.0",  # Google Cloud
            "azure-storage-blob>=12.14.0",  # Azure
            "celery[redis]>=5.2.0",
            "flower>=2.0.0",        # Celery监控
            "sentry-sdk>=1.24.0"    # 错误监控
        ]

        # 根据项目类型和功能选择依赖
        requirements = basic_requirements.copy()

        if self.project_type in ["comprehensive", "enhanced", "enterprise"]:
            requirements.extend(enhanced_requirements)

        if self.project_type == "enterprise":
            requirements.extend(enterprise_requirements)

        # 根据功能特性添加特定依赖
        if 'web_interface' in self.features:
            requirements.extend([
                "streamlit>=1.25.0",
                "plotly>=5.15.0",
                "dash>=2.10.0"
            ])

        if 'data_visualization' in self.features:
            requirements.extend([
                "matplotlib>=3.7.0",
                "seaborn>=0.12.0",
                "dash>=2.10.0"
            ])

        if 'testing' in self.features:
            requirements.extend([
                "pytest>=7.2.0",
                "pytest-asyncio>=0.21.0",
                "pytest-cov>=4.0.0",
                "factory-boy>=3.2.0"
            ])

        if 'api_service' in self.features:
            requirements.extend([
                "fastapi>=0.95.0",
                "uvicorn[standard]>=0.20.0",
                "python-multipart>=0.0.6"
            ])

        # 去重并排序
        requirements = sorted(list(set(requirements)))

        req_file = self.project_root / "requirements.txt"
        with open(req_file, 'w', encoding='utf-8') as f:
            for req in requirements:
                f.write(f"{req}\n")

        print(f"✓ 创建增强版依赖文件: requirements.txt ({len(requirements)} 个依赖)")

    def create_deployment_scripts(self):
        """创建部署脚本"""
        print("🚀 创建部署脚本...")

        # 开发环境启动脚本
        dev_script = '''#!/bin/bash
# 开发环境启动脚本

echo "🚀 启动开发环境..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📦 安装依赖..."
pip install -r requirements.txt

# 运行数据库迁移
if [ -f "scripts/migrate.py" ]; then
    echo "🗄️ 运行数据库迁移..."
    python scripts/migrate.py
fi

# 启动应用
echo "🎯 启动应用..."
if [ "$1" = "api" ]; then
    python src/main.py --api-only
elif [ "$1" = "scraping" ]; then
    python src/main.py --scraping-only
elif [ "$1" = "email" ]; then
    python src/main.py --email-only
else
    python src/main.py
fi
'''

        # Docker部署脚本
        docker_script = '''#!/bin/bash
# Docker部署脚本

echo "🐳 Docker部署..."

# 构建镜像
echo "🏗️ 构建Docker镜像..."
docker-compose build

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 显示日志
echo "📝 显示日志..."
docker-compose logs -f
'''

        # 生产环境部署脚本
        prod_script = '''#!/bin/bash
# 生产环境部署脚本

echo "🚀 生产环境部署..."

# 设置环境变量
export NODE_ENV=production
export PYTHONPATH=$PWD:$PYTHONPATH

# 创建必要目录
mkdir -p logs data data/raw data/processed

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
if [ -f "scripts/migrate.py" ]; then
    python scripts/migrate.py
fi

# 启动应用（使用gunicorn）
if command -v gunicorn &> /dev/null; then
    echo "🎯 使用Gunicorn启动应用..."
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 src.main:app
else
    echo "🎯 启动应用..."
    python src/main.py
fi
'''

        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # 保存脚本文件
        with open(scripts_dir / "start_dev.sh", 'w') as f:
            f.write(dev_script)
        os.chmod(scripts_dir / "start_dev.sh", 0o755)

        if 'docker' in self.features:
            with open(scripts_dir / "deploy_docker.sh", 'w') as f:
                f.write(docker_script)
            os.chmod(scripts_dir / "deploy_docker.sh", 0o755)

        with open(scripts_dir / "deploy_prod.sh", 'w') as f:
            f.write(prod_script)
        os.chmod(scripts_dir / "deploy_prod.sh", 0o755)

        print("✓ 创建部署脚本: start_dev.sh, deploy_docker.sh, deploy_prod.sh")

    def create_ci_cd_configs(self):
        """创建CI/CD配置"""
        if 'ci_cd' not in self.features:
            return

        print("🔄 创建CI/CD配置...")

        # GitHub Actions工作流
        github_workflow = {
            "name": "CI/CD Pipeline",
            "on": {
                "push": {
                    "branches": ["main", "develop"]
                },
                "pull_request": {
                    "branches": ["main"]
                }
            },
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "strategy": {
                        "matrix": {
                            "python-version": ["3.9", "3.10", "3.11"]
                        }
                    },
                    "steps": [
                        {
                            "uses": "actions/checkout@v3"
                        },
                        {
                            "name": "Set up Python ${{ matrix.python-version }}",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "${{ matrix.python-version }}"
                            }
                        },
                        {
                            "name": "Install dependencies",
                            "run": |
                                python -m pip install --upgrade pip
                                pip install -r requirements.txt
                                pip install pytest pytest-cov
                        },
                        {
                            "name": "Run tests",
                            "run": |
                                pytest tests/ --cov=./src --cov-report=xml
                        },
                        {
                            "name": "Upload coverage to Codecov",
                            "uses": "codecov/codecov-action@v3"
                        }
                    ]
                },
                "deploy": {
                    "needs": "test",
                    "runs-on": "ubuntu-latest",
                    "if": "github.ref == 'refs/heads/main'",
                    "steps": [
                        {
                            "uses": "actions/checkout@v3"
                        },
                        {
                            "name": "Deploy to production",
                            "run": |
                                echo "Deploying to production..."
                                # 这里添加实际的部署命令
                        }
                    ]
                }
            }
        }

        workflows_dir = self.project_root / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        with open(workflows_dir / "ci_cd.yml", 'w') as f:
            yaml.dump(github_workflow, f, default_flow_style=False)

        print("✓ 创建CI/CD配置: .github/workflows/ci_cd.yml")

    def build_enhanced_project(self):
        """构建增强版项目"""
        try:
            print(f"开始构建增强版项目: {self.project_name}")
            print(f"项目类型: {self.project_type}")
            print(f"启用功能: {', '.join(self.features) if self.features else '无'}")
            print("-" * 60)

            # 创建项目结构
            self.create_enhanced_project_structure()

            # 创建配置文件
            self.create_enhanced_config()

            # 创建主程序
            self.create_enhanced_main_module()

            # 创建依赖文件
            self.create_enhanced_requirements()

            # 创建部署脚本
            self.create_deployment_scripts()

            # 创建CI/CD配置
            self.create_ci_cd_configs()

            # 创建其他必要文件
            self._create_additional_files()

            print("-" * 60)
            print("✅ 增强版项目构建完成！")
            print()
            print("🎯 项目特色:")
            for feature in self.features:
                print(f"  • {self.available_features.get(feature, feature)}")

            print()
            print("📋 下一步操作:")
            print(f"1. cd {self.project_name}")
            print("2. pip install -r requirements.txt")
            print("3. 编辑 config/project_config.json 配置文件")
            print("4. 运行开发环境: ./scripts/start_dev.sh")

            if 'docker' in self.features:
                print("5. 或使用Docker: ./scripts/deploy_docker.sh")

            print()
            print("🔧 高级功能:")
            if 'api_service' in self.features:
                print("  • API服务: http://localhost:8000/docs")
            if 'web_interface' in self.features:
                print("  • Web界面: http://localhost:3000")
            if 'monitoring' in self.features:
                print("  • 监控面板: http://localhost:3001")

        except Exception as e:
            print(f"❌ 项目构建失败: {e}")
            raise

    def _create_additional_files(self):
        """创建其他必要文件"""
        # .gitignore
        gitignore_content = '''
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
logs/
data/*.db
data/*.sqlite
data/*.sqlite3
.env
.env.local
.env.production
models/
*.pkl
*.joblib

# Docker
.dockerignore

# Monitoring
prometheus_data/
grafana_data/
'''

        gitignore_file = self.project_root / ".gitignore"
        with open(gitignore_file, 'w') as f:
            f.write(gitignore_content)

        # LICENSE文件
        license_content = '''MIT License

Copyright (c) 2024 智能设计营销自动化系统

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

        license_file = self.project_root / "LICENSE"
        with open(license_file, 'w') as f:
            f.write(license_content)

        # 更新README.md
        self._update_readme()

        print("✓ 创建其他必要文件: .gitignore, LICENSE, README.md")

    def _update_readme(self):
        """更新README文件"""
        readme_content = f'''# {self.project_name}

增强版智能设计营销自动化系统 - 专为智能化设计工程师打造的企业级营销自动化工具

## 🚀 项目特性

### 核心功能
- 🔍 **智能爬虫系统**: 支持政府采购、高校、企业多数据源
- 🧠 **增强信息提取**: AI驱动的联系人信息智能识别
- 📧 **邮件营销自动化**: 个性化模板和批量发送管理
- 📊 **数据可视化**: 实时数据统计和趋势分析
- 🌐 **Web管理界面**: 直观的操作和管理平台

### 企业级功能
'''

        # 添加功能特性描述
        for feature in self.features:
            if feature in self.available_features:
                readme_content += f'- {self.available_features[feature]}\n'

        readme_content += f'''
## 🛠️ 技术栈

- **后端**: Python 3.9+, FastAPI, SQLAlchemy, AsyncPG
- **数据库**: PostgreSQL, Redis缓存
- **前端**: Streamlit, Plotly, Dash
- **部署**: Docker, Docker Compose
- **监控**: Prometheus, Grafana
- **CI/CD**: GitHub Actions

## 📋 系统要求

- Python 3.9+
- PostgreSQL (企业版) / SQLite (基础版)
- Redis (可选，用于缓存)
- Docker (可选，用于容器化部署)

## 🚀 快速开始

### 方式一：Docker部署 (推荐)

```bash
# 1. 克隆项目
git clone <repository-url>
cd {self.project_name}

# 2. 启动服务
./scripts/deploy_docker.sh
```

### 方式二：本地开发

```bash
# 1. 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\\Scripts\\activate     # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp config/environments/development.yaml.example config/environments/development.yaml
# 编辑配置文件...

# 4. 运行数据库迁移
python scripts/migrate.py

# 5. 启动应用
./scripts/start_dev.sh
```

## 📖 使用指南

### API文档
启动服务后访问: http://localhost:8000/docs

### Web界面
访问: http://localhost:3000

### 监控面板
访问: http://localhost:3001 (admin/admin123)

## 🔧 配置说明

主要配置文件:
- `config/project_config.json` - 主配置文件
- `config/environments/` - 环境特定配置
- `config/email_config.json` - 邮件配置

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 📊 监控和日志

- 应用日志: `logs/` 目录
- 监控指标: Prometheus + Grafana
- 错误监控: Sentry (企业版)

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 支持

如有问题，请通过以下方式联系:
- 提交 Issue: [GitHub Issues](链接)
- 邮件支持: support@example.com

---

**创建时间**: {datetime.now().strftime('%Y年%m月%d日')}
**项目类型**: {self.project_type}
**版本**: 2.0.0
**功能特性**: {len(self.features)} 个高级功能
'''

        readme_file = self.project_root / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="增强版智能设计营销自动化项目构建器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
功能特性:
{chr(10).join([f'  {k}: {v}' for k, v in {
    'docker': 'Docker容器化支持',
    'web_interface': 'Web管理界面',
    'data_visualization': '数据可视化面板',
    'api_service': 'RESTful API服务',
    'monitoring': '性能监控和告警',
    'redis_cache': 'Redis缓存支持',
    'ci_cd': 'CI/CD自动化流程',
    'testing': '完整测试套件'
}.items()])}

示例用法:
  python enhanced_project_builder.py --name "advanced-marketing" --type enhanced --features docker,web_interface,api_service
  python enhanced_project_builder.py --name "enterprise-system" --type enterprise --features all
  python enhanced_project_builder.py --name "basic-project" --type comprehensive --features testing,monitoring
        """
    )

    parser.add_argument(
        "--name",
        required=True,
        help="项目名称"
    )

    parser.add_argument(
        "--type",
        choices=["basic", "comprehensive", "enhanced", "enterprise"],
        default="enhanced",
        help="项目类型 (默认: enhanced)"
    )

    parser.add_argument(
        "--features",
        help="功能特性列表，用逗号分隔 (如: docker,web_interface,api_service) 或使用 'all' 启用所有功能"
    )

    args = parser.parse_args()

    try:
        # 解析功能特性
        features = []
        if args.features:
            if args.features.lower() == 'all':
                features = list(EnhancedProjectBuilder('', '').available_features.keys())
            else:
                features = [f.strip() for f in args.features.split(',')]

        # 创建项目构建器
        builder = EnhancedProjectBuilder(args.name, args.type, features)

        # 构建项目
        builder.build_enhanced_project()

    except Exception as e:
        print(f"❌ 项目构建失败: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()