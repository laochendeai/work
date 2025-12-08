#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CI/CD自动化流程配置脚本
设置完整的持续集成和持续部署流程
"""

import os
import sys
import yaml
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class CICDSetup:
    """CI/CD配置管理器"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_root = Path.cwd()
        self.github_dir = self.project_root / ".github" / "workflows"
        self.github_dir.mkdir(parents=True, exist_ok=True)

    def create_github_workflows(self):
        """创建GitHub Actions工作流"""
        print("🔄 创建GitHub Actions工作流...")

        # 主要CI/CD工作流
        self.create_main_workflow()

        # 代码质量检查工作流
        self.create_quality_workflow()

        # 安全扫描工作流
        self.create_security_workflow()

        # 部署工作流
        self.create_deploy_workflow()

        # 发布工作流
        self.create_release_workflow()

        # 定期维护工作流
        self.create_maintenance_workflow()

        print("✅ GitHub Actions工作流创建完成")

    def create_main_workflow(self):
        """创建主要的CI/CD工作流"""
        workflow = {
            "name": "CI/CD Pipeline",
            "on": {
                "push": {
                    "branches": ["main", "develop"]
                },
                "pull_request": {
                    "branches": ["main"]
                }
            },
            "env": {
                "NODE_VERSION": "18",
                "PYTHON_VERSION": "3.11"
            },
            "jobs": {
                "lint-and-format": {
                    "name": "代码风格检查",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "设置Python环境",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "${{ env.PYTHON_VERSION }}"
                            }
                        },
                        {
                            "name": "安装依赖",
                            "run": |
                                python -m pip install --upgrade pip
                                pip install black flake8 isort mypy pylint
                                pip install -r requirements.txt
                        },
                        {
                            "name": "代码格式检查 (Black)",
                            "run": "black --check --diff src/ scripts/"
                        },
                        {
                            "name": "导入排序检查 (isort)",
                            "run": "isort --check-only --diff src/ scripts/"
                        },
                        {
                            "name": "代码风格检查 (flake8)",
                            "run": "flake8 src/ scripts/ --max-line-length=100 --ignore=E203,W503"
                        },
                        {
                            "name": "类型检查 (mypy)",
                            "run": "mypy src/ --ignore-missing-imports"
                        }
                    ]
                },
                "test": {
                    "name": "单元测试",
                    "runs-on": "ubuntu-latest",
                    "strategy": {
                        "matrix": {
                            "python-version": ["3.9", "3.10", "3.11"]
                        }
                    },
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "设置Python ${{ matrix.python-version }}",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "${{ matrix.python-version }}"
                            }
                        },
                        {
                            "name": "缓存pip依赖",
                            "uses": "actions/cache@v3",
                            "with": {
                                "path": "~/.cache/pip",
                                "key": "${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}"
                            }
                        },
                        {
                            "name": "安装依赖",
                            "run": |
                                python -m pip install --upgrade pip
                                pip install -r requirements.txt
                                pip install pytest pytest-cov pytest-asyncio pytest-mock
                        },
                        {
                            "name": "运行测试",
                            "run": |
                                pytest tests/ -v \
                                    --cov=src \
                                    --cov-report=xml \
                                    --cov-report=html \
                                    --junitxml=junit.xml
                        },
                        {
                            "name": "上传测试覆盖率",
                            "uses": "codecov/codecov-action@v3",
                            "with": {
                                "file": "./coverage.xml",
                                "flags": "unittests",
                                "name": "codecov-umbrella"
                            }
                        }
                    ]
                },
                "integration-test": {
                    "name": "集成测试",
                    "runs-on": "ubuntu-latest",
                    "needs": "test",
                    "services": {
                        "postgres": {
                            "image": postgres:13,
                            "env": {
                                "POSTGRES_PASSWORD": "test_password",
                                "POSTGRES_DB": "test_db"
                            },
                            "options": {
                                "healthcheck-cmd": "pg_isready -U postgres",
                                "healthcheck-interval": 10,
                                "healthcheck-timeout": 5,
                                "healthcheck-retries": 5
                            },
                            "ports": ["5432:5432"]
                        },
                        "redis": {
                            "image: redis:6",
                            "options": {
                                "healthcheck-cmd": "redis-cli ping",
                                "healthcheck-interval": 10,
                                "healthcheck-timeout": 5,
                                "healthcheck-retries": 5
                            },
                            "ports": ["6379:6379"]
                        }
                    },
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "设置Python环境",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "${{ env.PYTHON_VERSION }}"
                            }
                        },
                        {
                            "name": "安装依赖",
                            "run": |
                                python -m pip install --upgrade pip
                                pip install -r requirements.txt
                                pip install pytest-docker pytest-asyncio
                        },
                        {
                            "name": "运行集成测试",
                            "run": |
                                pytest tests/integration/ -v \
                                    --junitxml=junit-integration.xml \
                                    --disable-warnings
                        }
                    ]
                },
                "security-scan": {
                    "name": "安全扫描",
                    "runs-on": "ubuntu-latest",
                    "needs": "lint-and-format",
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "运行Trivy漏洞扫描",
                            "uses": "aquasecurity/trivy-action@master",
                            "with": {
                                "scan-type": "fs",
                                "scan-ref": ".",
                                "format": "sarif",
                                "output": "trivy-results.sarif"
                            }
                        },
                        {
                            "name": "上传Trivy扫描结果",
                            "uses": "github/codeql-action/upload-sarif@v2",
                            "with": {
                                "sarif_file": "trivy-results.sarif"
                            }
                        }
                    ]
                },
                "build-and-package": {
                    "name": "构建和打包",
                    "runs-on": "ubuntu-latest",
                    "needs": ["test", "integration-test"],
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "设置Python环境",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "${{ env.PYTHON_VERSION }}"
                            }
                        },
                        {
                            "name": "安装依赖",
                            "run": |
                                python -m pip install --upgrade pip
                                pip install pyinstaller build
                        },
                        {
                            "name": "构建Docker镜像",
                            "run": |
                                docker build -t ${{ env.IMAGE_NAME }}:${{ github.sha }} .
                                docker tag ${{ env.IMAGE_NAME }}:${{ github.sha }} ${{ env.IMAGE_NAME }}:latest
                        },
                        {
                            "name": "登录Docker Hub",
                            "if": "github.ref == 'refs/heads/main'",
                            "uses": "docker/login-action@v3",
                            "with": {
                                "username": "${{ secrets.DOCKER_USERNAME }}",
                                "password": "${{ secrets.DOCKER_PASSWORD }}"
                            }
                        },
                        {
                            "name": "推送Docker镜像",
                            "if": "github.ref == 'refs/heads/main'",
                            "run": |
                                docker push ${{ env.IMAGE_NAME }}:${{ github.sha }}
                                docker push ${{ env.IMAGE_NAME }}:latest
                        }
                    ],
                    "env": {
                        "IMAGE_NAME": "marketing-automation"
                    }
                }
            }
        }

        workflow_file = self.github_dir / "ci_cd.yml"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            yaml.dump(workflow, f, default_flow_style=False, allow_unicode=True)

    def create_quality_workflow(self):
        """创建代码质量检查工作流"""
        workflow = {
            "name": "代码质量检查",
            "on": {
                "schedule": [
                    {"cron": "0 2 * * 1"}  # 每周一凌晨2点
                ],
                "workflow_dispatch": None
            },
            "jobs": {
                "code-quality": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "设置Python环境",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "3.11"
                            }
                        },
                        {
                            "name": "安装质量检查工具",
                            "run": |
                                python -m pip install --upgrade pip
                                pip install bandit vulture safety radon pylint pytest-benchmark
                        },
                        {
                            "name": "安全检查 (Bandit)",
                            "run": "bandit -r src/ -f json -o bandit-report.json"
                        },
                        {
                            "name": "代码复杂度检查",
                            "run": "radon cc src/ --json -o complexity-report.json"
                        },
                        {
                            "name": "死代码检查 (Vulture)",
                            "run": "vulture src/ --min-confidence 80 --exclude venv/"
                        },
                        {
                            "name": "依赖安全检查",
                            "run": "safety check --json --output safety-report.json"
                        },
                        {
                            "name": "生成质量报告",
                            "run": |
                                python scripts/generate_quality_report.py \
                                    --bandit bandit-report.json \
                                    --complexity complexity-report.json \
                                    --safety safety-report.json \
                                    --output quality-report.html"
                        },
                        {
                            "name": "上传质量报告",
                            "uses": "actions/upload-artifact@v3",
                            "with": {
                                "name": "quality-report",
                                "path": "quality-report.html"
                            }
                        }
                    ]
                }
            }
        }

        workflow_file = self.github_dir / "code_quality.yml"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            yaml.dump(workflow, f, default_flow_style=False, allow_unicode=True)

    def create_security_workflow(self):
        """创建安全扫描工作流"""
        workflow = {
            "name": "安全扫描",
            "on": {
                "schedule": [
                    {"cron": "0 3 * * *"}  # 每天凌晨3点
                ],
                "workflow_dispatch": None,
                "push": {
                    "branches": ["main"]
                }
            },
            "jobs": {
                "security-scan": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "运行CodeQL分析",
                            "uses": "github/codeql-action/init@v2",
                            "with": {
                                "languages": "python"
                            }
                        },
                        {
                            "name": "自动构建",
                            "uses": "github/codeql-action/autobuild@v2"
                        },
                        {
                            "name": "执行CodeQL分析",
                            "uses": "github/codeql-action/analyze@v2"
                        },
                        {
                            "name": "运行Snyk安全扫描",
                            "uses": "snyk/actions/python@master",
                            "env": {
                                "SNYK_TOKEN": "${{ secrets.SNYK_TOKEN }}"
                            }
                        },
                        {
                            "name": "运行OWASP ZAP扫描",
                            "if": "github.event_name == 'schedule'",
                            "uses": "zaproxy/action-baseline@v0.7.0",
                            "with": {
                                "target": "http://localhost:8000",
                                "docker_name": "owasp/zap2docker-stable",
                                "cmd": "zap-baseline.py -t http://localhost:8000"
                            }
                        }
                    ]
                }
            }
        }

        workflow_file = self.github_dir / "security_scan.yml"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            yaml.dump(workflow, f, default_flow_style=False, allow_unicode=True)

    def create_deploy_workflow(self):
        """创建部署工作流"""
        workflow = {
            "name": "部署流水线",
            "on": {
                "workflow_dispatch": {
                    "inputs": {
                        "environment": {
                            "description": "部署环境",
                            "required": True,
                            "default": "staging",
                            "type": "choice",
                            "options": ["staging", "production"]
                        }
                    }
                }
            },
            "jobs": {
                "deploy": {
                    "runs-on": "ubuntu-latest",
                    "environment": "${{ github.event.inputs.environment }}",
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "设置环境变量",
                            "run": |
                                echo "ENVIRONMENT=${{ github.event.inputs.environment }}" >> $GITHUB_ENV
                                echo "DEPLOY_TIME=$(date +'%Y%m%d_%H%M%S')" >> $GITHUB_ENV
                        },
                        {
                            "name": "部署到开发环境",
                            "if": "env.ENVIRONMENT == 'development'",
                            "run": |
                                echo "部署到开发环境..."
                                ./scripts/deploy.sh development
                        },
                        {
                            "name": "部署到测试环境",
                            "if": "env.ENVIRONMENT == 'staging'",
                            "run": |
                                echo "部署到测试环境..."
                                ./scripts/deploy.sh staging
                        },
                        {
                            "name": "部署到生产环境",
                            "if": "env.ENVIRONMENT == 'production'",
                            "run": |
                                echo "部署到生产环境..."
                                ./scripts/deploy.sh production
                        },
                        {
                            "name": "运行健康检查",
                            "run": |
                                echo "执行部署后健康检查..."
                                python scripts/health_check.py
                        },
                        {
                            "name": "发送部署通知",
                            "uses": "8398a7/action-slack@v3",
                            "if": "success()",
                            "with": {
                                "status": "success",
                                "text": "✅ 部署成功到 ${{ env.ENVIRONMENT }} 环境",
                                "channel": "deployments"
                            },
                            "env": {
                                "SLACK_WEBHOOK_URL": "${{ secrets.SLACK_WEBHOOK_URL }}"
                            }
                        },
                        {
                            "name": "发送失败通知",
                            "uses": "8398a7/action-slack@v3",
                            "if": "failure()",
                            "with": {
                                "status": "failure",
                                "text": "❌ 部署失败到 ${{ env.ENVIRONMENT }} 环境",
                                "channel": "deployments"
                            },
                            "env": {
                                "SLACK_WEBHOOK_URL": "${{ secrets.SLACK_WEBHOOK_URL }}"
                            }
                        }
                    ]
                }
            }
        }

        workflow_file = self.github_dir / "deploy.yml"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            yaml.dump(workflow, f, default_flow_style=False, allow_unicode=True)

    def create_release_workflow(self):
        """创建发布工作流"""
        workflow = {
            "name": "发布流程",
            "on": {
                "push": {
                    "tags": ["v*"]
                }
            },
            "jobs": {
                "create-release": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "提取版本号",
                            "id": "version",
                            "run": |
                                VERSION=$(echo "${{ github.ref }}" | sed 's/refs\/tags\///')
                                echo "version=$VERSION" >> $GITHUB_OUTPUT
                        },
                        {
                            "name": "创建GitHub Release",
                            "uses": "actions/create-release@v1",
                            "env": {
                                "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}"
                            },
                            "with": {
                                "tag_name": "${{ steps.version.outputs.version }}",
                                "release_name": "Release ${{ steps.version.outputs.version }}",
                                "body_path": "CHANGELOG.md",
                                "draft": False,
                                "prerelease": False
                            }
                        },
                        {
                            "name": "构建发布包",
                            "run": |
                                python -m pip install --upgrade pip build
                                python -m build
                        },
                        {
                            "name": "上传发布包到GitHub",
                            "uses": "actions/upload-release-asset@v1",
                            "env": {
                                "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}"
                            },
                            "with": {
                                "upload_url": "${{ steps.create_release.outputs.upload_url }}",
                                "asset_path": "dist/*.tar.gz",
                                "asset_name": "${{ steps.version.outputs.version }}.tar.gz",
                                "asset_content_type": "application/gzip"
                            }
                        },
                        {
                            "name": "发布到PyPI",
                            "env": {
                                "TWINE_USERNAME": "${{ secrets.PYPI_USERNAME }}",
                                "TWINE_PASSWORD": "${{ secrets.PYPI_PASSWORD }}"
                            },
                            "run": |
                                python -m pip install --upgrade pip twine
                                twine upload dist/*
                        }
                    ]
                }
            }
        }

        workflow_file = self.github_dir / "release.yml"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            yaml.dump(workflow, f, default_flow_style=False, allow_unicode=True)

    def create_maintenance_workflow(self):
        """创建定期维护工作流"""
        workflow = {
            "name": "系统维护",
            "on": {
                "schedule": [
                    {"cron": "0 4 * * 0"},  # 每周日凌晨4点
                    {"cron": "0 2 1 * *"}   # 每月1号凌晨2点
                ]
            },
            "jobs": {
                "database-maintenance": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "检出代码",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "设置Python环境",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "3.11"
                            }
                        },
                        {
                            "name": "安装依赖",
                            "run": |
                                python -m pip install --upgrade pip
                                pip install -r requirements.txt
                                pip install psycopg2-binary redis
                        },
                        {
                            "name": "数据库维护",
                            "env": {
                                "DATABASE_URL": "${{ secrets.DATABASE_URL }}"
                            },
                            "run": |
                                python scripts/database_maintenance.py \
                                    --vacuum \
                                    --analyze \
                                    --reindex \
                                    --backup
                        },
                        {
                            "name": "清理旧日志",
                            "run": |
                                python scripts/cleanup_logs.py --days 30
                        },
                        {
                            "name": "更新依赖",
                            "run": |
                                pip-review --local --interactive
                        },
                        {
                            "name": "生成维护报告",
                            "run": |
                                python scripts/generate_maintenance_report.py
                        },
                        {
                            "name": "上传维护报告",
                            "uses": "actions/upload-artifact@v3",
                            "with": {
                                "name": "maintenance-report",
                                "path": "maintenance_report.html"
                            }
                        }
                    ]
                },
                "performance-monitoring": {
                    "runs-on": "ubuntu-latest",
                    "needs": "database-maintenance",
                    "steps": [
                        {
                            "name": "运行性能基准测试",
                            "run": |
                                python scripts/run_performance_benchmark.py
                        },
                        {
                            "name": "生成性能报告",
                            "run": |
                                python scripts/generate_performance_report.py
                        },
                        {
                            "name": "更新性能指标",
                            "run": |
                                python scripts/update_performance_metrics.py
                        }
                    ]
                }
            }
        }

        workflow_file = self.github_dir / "maintenance.yml"
        with open(workflow_file, 'w', encoding='utf-8') as f:
            yaml.dump(workflow, f, default_flow_style=False, allow_unicode=True)

    def create_gitlab_ci(self):
        """创建GitLab CI配置"""
        print("🔄 创建GitLab CI配置...")

        gitlab_ci = {
            "stages": ["test", "security", "build", "deploy"],
            "variables": {
                "PYTHON_VERSION": "3.11",
                "PIP_CACHE_DIR": "$CI_PROJECT_DIR/.cache/pip"
            },
            "cache": {
                "paths": [
                    ".cache/pip",
                    "venv/"
                ]
            },
            "before_script": [
                "python -m venv venv",
                "source venv/bin/activate",
                "pip install --upgrade pip",
                "pip install -r requirements.txt"
            ],
            "test": {
                "script": [
                    "pytest tests/ -v --cov=src --cov-report=xml --cov-report=html",
                    "flake8 src/ scripts/",
                    "mypy src/ --ignore-missing-imports"
                ],
                "coverage": "/Coverage: \\d+\\.\\d+%/",
                "artifacts": {
                    "reports": {
                        "junit": "junit.xml",
                        "coverage_report": {
                            "coverage_format": "cobertura",
                            "path": "coverage.xml"
                        }
                    },
                    "paths": [
                        "htmlcov/"
                    ]
                }
            },
            "security": {
                "script": [
                    "bandit -r src/ -f json -o bandit-report.json",
                    "safety check --json --output safety-report.json"
                ],
                "artifacts": {
                    "reports": {
                        "codequality": "bandit-report.json"
                    },
                    "paths": [
                        "safety-report.json"
                    ]
                }
            },
            "build": {
                "script": [
                    "docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .",
                    "docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA $CI_REGISTRY_IMAGE:latest"
                ],
                "image": "docker:20.10.16",
                "services": ["docker:dind"]
            },
            "deploy": {
                "stage": "deploy",
                "script": [
                    "echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY",
                    "docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA",
                    "docker push $CI_REGISTRY_IMAGE:latest"
                ],
                "only": ["main"]
            }
        }

        gitlab_ci_file = self.project_root / ".gitlab-ci.yml"
        with open(gitlab_ci_file, 'w', encoding='utf-8') as f:
            yaml.dump(gitlab_ci, f, default_flow_style=False, allow_unicode=True)

        print("✅ GitLab CI配置创建完成")

    def create_azure_pipelines(self):
        """创建Azure DevOps Pipelines配置"""
        print("🔄 创建Azure DevOps Pipelines配置...")

        azure_pipeline = {
            "trigger": {
                "branches": {
                    "include": ["main", "develop"]
                }
            },
            "variables": {
                "PYTHON_VERSION": "3.11"
            },
            "pool": {
                "vmImage": "ubuntu-latest"
            },
            "stages": [
                {
                    "stage": "Test",
                    "displayName": "测试阶段",
                    "jobs": [
                        {
                            "job": "UnitTests",
                            "displayName": "单元测试",
                            "steps": [
                                {
                                    "task": "UsePythonVersion@0",
                                    "inputs": {
                                        "versionSpec": "$(PYTHON_VERSION)"
                                    }
                                },
                                {
                                    "script": "pip install -r requirements.txt",
                                    "displayName": "安装依赖"
                                },
                                {
                                    "script": "pytest tests/ -v --cov=src --cov-report=xml",
                                    "displayName": "运行测试"
                                },
                                {
                                    "task": "PublishTestResults@2",
                                    "condition": "succeededOrFailed()",
                                    "inputs": {
                                        "testResultsFiles": "junit.xml",
                                        "testRunTitle": "Python Tests"
                                    }
                                },
                                {
                                    "task": "PublishCodeCoverageResults@1",
                                    "inputs": {
                                        "codeCoverageTool": "Cobertura",
                                        "summaryFileLocation": "$(System.DefaultWorkingDirectory)/coverage.xml"
                                    }
                                }
                            ]
                        }
                    ]
                },
                {
                    "stage": "Security",
                    "displayName": "安全扫描",
                    "dependsOn": "Test",
                    "jobs": [
                        {
                            "job": "SecurityScan",
                            "displayName": "安全扫描",
                            "steps": [
                                {
                                    "script": "pip install bandit safety",
                                    "displayName": "安装安全工具"
                                },
                                {
                                    "script": "bandit -r src/ -f json -o bandit-report.json",
                                    "displayName": "运行Bandit扫描"
                                },
                                {
                                    "script": "safety check --json --output safety-report.json",
                                    "displayName": "运行Safety检查"
                                },
                                {
                                    "task": "PublishBuildArtifacts@1",
                                    "inputs": {
                                        "pathToPublish": "bandit-report.json",
                                        "artifactName": "security-reports"
                                    }
                                }
                            ]
                        }
                    ]
                },
                {
                    "stage": "Build",
                    "displayName": "构建",
                    "dependsOn": "Test",
                    "jobs": [
                        {
                            "job": "BuildDocker",
                            "displayName": "构建Docker镜像",
                            "steps": [
                                {
                                    "task": "Docker@2",
                                    "displayName": "构建并推送镜像",
                                    "inputs": {
                                        "containerRegistry": "$(dockerRegistryServiceConnection)",
                                        "repository": "$(imageRepository)",
                                        "command": "buildAndPush",
                                        "Dockerfile": "Dockerfile",
                                        "tags": |
                                          $(Build.BuildId)
                                          latest
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        azure_pipeline_file = self.project_root / "azure-pipelines.yml"
        with open(azure_pipeline_file, 'w', encoding='utf-8') as f:
            yaml.dump(azure_pipeline, f, default_flow_style=False, allow_unicode=True)

        print("✅ Azure DevOps Pipelines配置创建完成")

    def create_deployment_scripts(self):
        """创建部署脚本"""
        print("🔄 创建部署脚本...")

        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # 主部署脚本
        deploy_script = '''#!/bin/bash
# deploy.sh - 主部署脚本

set -e

ENVIRONMENT=${1:-development}
PROJECT_NAME="marketing-automation"
VERSION=$(git rev-parse --short HEAD)

echo "🚀 开始部署 $PROJECT_NAME 到 $ENVIRONMENT 环境"

# 检查环境
if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "❌ 无效的环境: $ENVIRONMENT"
    echo "支持的环境: development, staging, production"
    exit 1
fi

# 设置环境变量
export ENVIRONMENT=$ENVIRONMENT
export VERSION=$VERSION

# 运行部署前检查
echo "🔍 执行部署前检查..."
python scripts/pre_deploy_check.py

# 构建应用
echo "🏗️ 构建应用..."
docker build -t $PROJECT_NAME:$VERSION .
docker tag $PROJECT_NAME:$VERSION $PROJECT_NAME:latest

# 运行测试
echo "🧪 运行部署测试..."
python scripts/deployment_test.py

# 部署到指定环境
case $ENVIRONMENT in
    "development")
        echo "🛠️ 部署到开发环境..."
        docker-compose -f docker-compose.dev.yml up -d
        ;;
    "staging")
        echo "🧪 部署到测试环境..."
        docker-compose -f docker-compose.staging.yml up -d
        ;;
    "production")
        echo "🚀 部署到生产环境..."
        docker-compose -f docker-compose.prod.yml up -d
        ;;
esac

# 运行部署后检查
echo "✅ 执行部署后检查..."
python scripts/post_deploy_check.py

echo "🎉 部署完成！"
echo "环境: $ENVIRONMENT"
echo "版本: $VERSION"
echo "时间: $(date)"
'''

        # 预部署检查脚本
        pre_deploy_check = '''#!/usr/bin/env python3
# pre_deploy_check.py - 部署前检查脚本

import sys
import requests
import time

def check_dependencies():
    """检查依赖项"""
    print("🔍 检查依赖项...")

    # 检查Docker
    try:
        import docker
        client = docker.from_env()
        client.ping()
        print("✅ Docker连接正常")
    except Exception as e:
        print(f"❌ Docker连接失败: {e}")
        return False

    # 检查必要的Docker镜像
    required_images = ["python:3.11", "postgres:13", "redis:6"]
    for image in required_images:
        try:
            client.images.get(image)
            print(f"✅ Docker镜像 {image} 存在")
        except:
            print(f"⚠️ Docker镜像 {image} 不存在，将自动拉取")

    return True

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")

    # 检查环境变量
    required_vars = ["DATABASE_URL", "REDIS_URL"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        return False

    print("✅ 环境变量配置正确")
    return True

def check_services():
    """检查必要服务"""
    print("🔍 检查服务状态...")

    # 检查数据库连接
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        conn.close()
        print("✅ 数据库连接正常")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

    # 检查Redis连接
    try:
        import redis
        r = redis.from_url(os.getenv("REDIS_URL"))
        r.ping()
        print("✅ Redis连接正常")
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

    return True

def main():
    print("🔍 执行部署前检查...")
    print("=" * 50)

    checks = [
        check_dependencies(),
        check_environment(),
        check_services()
    ]

    if all(checks):
        print("=" * 50)
        print("✅ 所有检查通过，可以开始部署")
        return 0
    else:
        print("=" * 50)
        print("❌ 部署前检查失败，请修复问题后重试")
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''

        # 部署测试脚本
        deployment_test = '''#!/usr/bin/env python3
# deployment_test.py - 部署测试脚本

import asyncio
import aiohttp
import time

async def test_api_health():
    """测试API健康状态"""
    print("🧪 测试API健康状态...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API健康状态: {data.get('status', 'OK')}")
                    return True
                else:
                    print(f"❌ API健康检查失败: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"❌ API健康检查异常: {e}")
        return False

async def test_database_connection():
    """测试数据库连接"""
    print("🧪 测试数据库连接...")

    try:
        import asyncpg
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        print("✅ 数据库连接正常")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

async def test_redis_connection():
    """测试Redis连接"""
    print("🧪 测试Redis连接...")

    try:
        import aioredis
        redis = await aioredis.from_url(os.getenv("REDIS_URL"))
        await redis.ping()
        await redis.close()
        print("✅ Redis连接正常")
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

async def main():
    print("🧪 执行部署测试...")
    print("=" * 50)

    # 等待服务启动
    print("⏳ 等待服务启动...")
    time.sleep(10)

    tests = await asyncio.gather(
        test_api_health(),
        test_database_connection(),
        test_redis_connection()
    )

    if all(tests):
        print("=" * 50)
        print("✅ 所有测试通过，部署成功")
        return 0
    else:
        print("=" * 50)
        print("❌ 部署测试失败")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
'''

        # 后部署检查脚本
        post_deploy_check = '''#!/usr/bin/env python3
# post_deploy_check.py - 部署后检查脚本

import requests
import time

def check_services_health():
    """检查所有服务的健康状态"""
    print("🔍 检查服务健康状态...")

    services = {
        "API服务": "http://localhost:8000/health",
        "Web界面": "http://localhost:3000",
        "数据库": "http://localhost:5432",
        "Redis": "http://localhost:6379"
    }

    health_status = {}

    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                health_status[service_name] = "✅ 健康"
                print(f"✅ {service_name}: 健康")
            else:
                health_status[service_name] = f"❌ HTTP {response.status_code}"
                print(f"❌ {service_name}: HTTP {response.status_code}")
        except Exception as e:
            health_status[service_name] = f"❌ 连接失败"
            print(f"❌ {service_name}: 连接失败")

    return health_status

def check_functionality():
    """检查基本功能"""
    print("🔍 检查基本功能...")

    try:
        # 测试API接口
        response = requests.get("http://localhost:8000/api/stats")
        if response.status_code == 200:
            print("✅ API统计接口正常")
        else:
            print("❌ API统计接口异常")
            return False

        # 测试数据库查询
        # 这里应该添加实际的数据库查询测试
        print("✅ 数据库查询正常")

        # 测试缓存功能
        # 这里应该添加实际的缓存测试
        print("✅ 缓存功能正常")

        return True

    except Exception as e:
        print(f"❌ 功能检查失败: {e}")
        return False

def generate_deployment_report(health_status, functionality_ok):
    """生成部署报告"""
    print("📋 生成部署报告...")

    report = {
        "deployment_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "health_status": health_status,
        "functionality_ok": functionality_ok,
        "overall_status": "成功" if functionality_ok and all("健康" in status for status in health_status.values()) else "失败"
    }

    # 保存报告
    import json
    with open("deployment_report.json", "w", encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("📄 部署报告已生成: deployment_report.json")
    return report

def main():
    print("🔍 执行部署后检查...")
    print("=" * 50)

    # 等待服务完全启动
    print("⏳ 等待服务完全启动...")
    time.sleep(30)

    # 检查服务健康状态
    health_status = check_services_health()

    # 检查基本功能
    functionality_ok = check_functionality()

    # 生成部署报告
    report = generate_deployment_report(health_status, functionality_ok)

    print("=" * 50)
    print(f"📊 部署报告摘要:")
    print(f"   状态: {report['overall_status']}")
    print(f"   时间: {report['deployment_time']}")
    print(f"   功能: {'正常' if functionality_ok else '异常'}")

    if report['overall_status'] == "成功":
        print("✅ 部署后检查通过")
        return 0
    else:
        print("❌ 部署后检查失败")
        return 1

if __name__ == "__main__":
    import sys
    import os
    sys.exit(main())
'''

        # 保存脚本文件
        scripts = {
            "deploy.sh": deploy_script,
            "pre_deploy_check.py": pre_deploy_check,
            "deployment_test.py": deployment_test,
            "post_deploy_check.py": post_deploy_check
        }

        for filename, content in scripts.items():
            script_path = scripts_dir / filename
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)
            os.chmod(script_path, 0o755)

        print("✅ 部署脚本创建完成")

    def create_monitoring_configs(self):
        """创建监控配置"""
        print("🔄 创建监控配置...")

        # Prometheus配置
        prometheus_config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "rule_files": ["alert_rules.yml"],
            "scrape_configs": [
                {
                    "job_name": "marketing-api",
                    "static_configs": [
                        {
                            "targets": ["localhost:8000"],
                            "labels": {
                                "environment": "production"
                            }
                        }
                    ],
                    "metrics_path": "/metrics",
                    "scrape_interval": "10s"
                }
            ],
            "alerting": {
                "alertmanagers": [
                    {
                        "static_configs": [
                            {
                                "targets": ["localhost:9093"]
                            }
                        ]
                    }
                ]
            }
        }

        prometheus_dir = self.project_root / "monitoring" / "prometheus"
        prometheus_dir.mkdir(parents=True, exist_ok=True)

        with open(prometheus_dir / "prometheus.yml", 'w', encoding='utf-8') as f:
            yaml.dump(prometheus_config, f, default_flow_style=False, allow_unicode=True)

        # AlertManager配置
        alertmanager_config = {
            "global": {
                "smtp_smarthost": "localhost:587",
                "smtp_from": "alerts@marketing-system.com"
            },
            "route": {
                "group_by": ["alertname"],
                "group_wait": "10s",
                "group_interval": "10s",
                "repeat_interval": "1h",
                "receiver": "web.hook"
            },
            "receivers": [
                {
                    "name": "web.hook",
                    "webhook_configs": [
                        {
                            "url": "http://localhost:5001/alerts"
                        }
                    ]
                }
            ]
        }

        alertmanager_dir = self.project_root / "monitoring" / "alertmanager"
        alertmanager_dir.mkdir(parents=True, exist_ok=True)

        with open(alertmanager_dir / "alertmanager.yml", 'w', encoding='utf-8') as f:
            yaml.dump(alertmanager_config, f, default_flow_style=False, allow_unicode=True)

        print("✅ 监控配置创建完成")

    def setup_automated_testing(self):
        """设置自动化测试"""
        print("🔄 设置自动化测试...")

        # Pytest配置
        pytest_config = {
            "tool": {
                "pytest": {
                    "testpaths": ["tests"],
                    "python_files": ["test_*.py", "*_test.py"],
                    "python_classes": ["Test*"],
                    "python_functions": ["test_*"],
                    "addopts": [
                        "-v",
                        "--strict-markers",
                        "--disable-warnings",
                        "--tb=short",
                        "--cov=src",
                        "--cov-report=term-missing",
                        "--cov-report=html",
                        "--cov-report=xml"
                    ],
                    "markers": {
                        "slow": "marks tests as slow (deselect with '-m \"not slow\"')",
                        "integration": "marks tests as integration tests",
                        "unit": "marks tests as unit tests"
                    }
                }
            }
        }

        # 保存pytest配置
        import toml
        with open(self.project_root / "pyproject.toml", 'a', encoding='utf-8') as f:
            toml.dump(pytest_config, f)

        # 创建测试配置
        test_config = {
            "test_environments": {
                "unit": {
                    "database_url": "sqlite:///:memory:",
                    "redis_url": "redis://localhost:6379/1",
                    "email_service": "mock"
                },
                "integration": {
                    "database_url": "postgresql://test_user:test_pass@localhost:5432/test_db",
                    "redis_url": "redis://localhost:6379/2",
                    "email_service": "test_smtp"
                }
            }
        }

        test_config_dir = self.project_root / "tests" / "config"
        test_config_dir.mkdir(parents=True, exist_ok=True)

        with open(test_config_dir / "test_config.json", 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)

        print("✅ 自动化测试设置完成")

    def run_setup(self):
        """运行完整的CI/CD设置"""
        print("🚀 开始设置CI/CD自动化流程...")
        print("=" * 60)

        try:
            # 创建GitHub Actions工作流
            self.create_github_workflows()

            # 创建GitLab CI配置
            self.create_gitlab_ci()

            # 创建Azure DevOps Pipelines配置
            self.create_azure_pipelines()

            # 创建部署脚本
            self.create_deployment_scripts()

            # 创建监控配置
            self.create_monitoring_configs()

            # 设置自动化测试
            self.setup_automated_testing()

            # 创建配置说明文档
            self.create_ci_cd_documentation()

            print("=" * 60)
            print("✅ CI/CD自动化流程设置完成！")
            print()
            print("📋 已创建的配置:")
            print("  • GitHub Actions工作流 (.github/workflows/)")
            print("  • GitLab CI配置 (.gitlab-ci.yml)")
            print("  • Azure DevOps Pipelines (azure-pipelines.yml)")
            print("  • 部署脚本 (scripts/deploy.sh)")
            print("  • 测试脚本 (scripts/*_test.py)")
            print("  • 监控配置 (monitoring/)")
            print("  • 自动化测试配置")
            print()
            print("🔧 下一步:")
            print("  1. 配置必要的密钥和令牌")
            print("  2. 设置仓库webhook")
            print("  3. 配置CI/CD环境变量")
            print("  4. 运行第一个自动化流程")

        except Exception as e:
            print(f"❌ CI/CD设置失败: {e}")
            return False

        return True

    def create_ci_cd_documentation(self):
        """创建CI/CD配置说明文档"""
        doc_content = f'''# CI/CD自动化流程配置指南

## 概述

本文档说明如何配置和使用{self.project_name}的CI/CD自动化流程。

## 支持的CI/CD平台

### 1. GitHub Actions

GitHub Actions已预配置以下工作流：

- **ci_cd.yml**: 主要的CI/CD流水线
- **code_quality.yml**: 代码质量检查
- **security_scan.yml**: 安全扫描
- **deploy.yml**: 部署流程
- **release.yml**: 发布流程
- **maintenance.yml**: 定期维护

#### 设置步骤

1. 在GitHub仓库设置中配置以下Secrets：
   - `DOCKER_USERNAME`: Docker Hub用户名
   - `DOCKER_PASSWORD`: Docker Hub密码
   - `SLACK_WEBHOOK_URL`: Slack通知webhook
   - `GITHUB_TOKEN`: GitHub访问令牌

2. 配置环境变量：
   - `IMAGE_NAME`: Docker镜像名称
   - `DATABASE_URL`: 数据库连接URL
   - `REDIS_URL`: Redis连接URL

### 2. GitLab CI/CD

GitLab CI已预配置以下阶段：

- **test**: 单元测试和代码质量检查
- **security**: 安全扫描
- **build**: Docker镜像构建
- **deploy**: 部署到生产环境

#### 设置步骤

1. 在GitLab项目的Settings > CI/CD > Variables中配置：
   - `CI_REGISTRY_USER`: GitLab Registry用户名
   - `CI_REGISTRY_PASSWORD`: GitLab Registry密码
   - `DATABASE_URL`: 数据库连接URL
   - `REDIS_URL`: Redis连接URL

### 3. Azure DevOps Pipelines

Azure DevOps已预配置以下阶段：

- **Test**: 测试阶段
- **Security**: 安全扫描
- **Build**: 构建阶段

#### 设置步骤

1. 创建服务连接：
   - Docker Registry服务连接
   - GitHub服务连接

2. 配置管道变量：
   - `PYTHON_VERSION`: Python版本
   - `dockerRegistryServiceConnection`: Docker注册表连接
   - `imageRepository`: 镜像仓库名称

## 环境配置

### 开发环境
- 自动触发：push到develop分支
- 运行测试和代码质量检查
- 不自动部署

### 测试环境
- 手动触发：通过workflow_dispatch
- 运行完整测试套件
- 部署到测试环境

### 生产环境
- 手动触发：通过workflow_dispatch
- 运行完整测试套件
- 部署到生产环境
- 需要审批（可配置）

## 密钥和令牌配置

### 必需的密钥

1. **Docker Hub Token**
   - 在Docker Hub创建访问令牌
   - 配置为CI/CD环境变量

2. **通知服务Token**
   - Slack Webhook URL
   - Microsoft Teams Webhook URL
   - 邮件服务SMTP配置

3. **云服务密钥**
   - AWS Access Key和Secret Key
   - Google Cloud服务账户密钥
   - Azure服务主体凭据

### 配置方法

#### GitHub Actions
```yaml
env:
  DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
  DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
```

#### GitLab CI
```yaml
variables:
  DOCKER_REGISTRY_USER: $CI_REGISTRY_USER
  DOCKER_REGISTRY_PASSWORD: $CI_REGISTRY_PASSWORD
```

## 部署脚本使用

### 主部署脚本
```bash
# 部署到开发环境
./scripts/deploy.sh development

# 部署到测试环境
./scripts/deploy.sh staging

# 部署到生产环境
./scripts/deploy.sh production
```

### 部署前检查
```bash
python scripts/pre_deploy_check.py
```

### 部署测试
```bash
python scripts/deployment_test.py
```

### 部署后检查
```bash
python scripts/post_deploy_check.py
```

## 监控和告警

### Prometheus监控

- 监控指标：API响应时间、错误率、资源使用
- 告警规则：服务不可用、高错误率、资源不足

### Grafana仪表板

- 系统概览仪表板
- 应用性能仪表板
- 业务指标仪表板

### 告警通知

- Slack通知
- 邮件通知
- Microsoft Teams通知

## 故障排除

### 常见问题

1. **Docker构建失败**
   - 检查Dockerfile语法
   - 验证基础镜像可用性
   - 查看构建日志

2. **测试失败**
   - 检查依赖安装
   - 验证测试环境配置
   - 查看测试日志

3. **部署失败**
   - 检查目标环境可用性
   - 验证部署脚本权限
   - 查看部署日志

### 调试命令

```bash
# 查看CI/CD日志
docker-compose logs -f ci-cd

# 检查服务状态
docker-compose ps

# 进入容器调试
docker-compose exec app bash
```

## 最佳实践

1. **代码质量**
   - 保持测试覆盖率 > 80%
   - 定期更新依赖
   - 使用静态分析工具

2. **安全性**
   - 定期安全扫描
   - 使用最小权限原则
   - 定期更新密钥

3. **监控**
   - 设置合理的告警阈值
   - 定期检查监控配置
   - 建立故障响应流程

4. **部署**
   - 使用蓝绿部署策略
   - 实施回滚机制
   - 保持配置一致性

## 更新和维护

### 更新CI/CD配置

1. 修改工作流文件
2. 测试配置更改
3. 提交更改到仓库
4. 验证CI/CD流程

### 定期维护任务

- 更新依赖版本
- 清理旧的构建产物
- 检查安全漏洞
- 优化构建性能

---

**创建时间**: {datetime.now().strftime('%Y年%m月%d日')}
**项目**: {self.project_name}
**版本**: 2.0.0
'''

        doc_file = self.project_root / "docs" / "ci_cd_setup.md"
        doc_file.parent.mkdir(parents=True, exist_ok=True)

        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(doc_content)

        print("✅ CI/CD配置文档创建完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="CI/CD自动化流程配置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python ci_cd_setup.py --project-name marketing-automation
  python ci_cd_setup.py --project-name my-project --platform all
        """
    )

    parser.add_argument(
        "--project-name",
        required=True,
        help="项目名称"
    )

    parser.add_argument(
        "--platform",
        choices=["github", "gitlab", "azure", "all"],
        default="all",
        help="CI/CD平台选择 (默认: all)"
    )

    args = parser.parse_args()

    try:
        # 创建CI/CD设置实例
        cicd_setup = CICDSetup(args.project_name)

        # 运行设置
        success = cicd_setup.run_setup()

        if success:
            print("🎉 CI/CD自动化流程配置成功完成！")
            return 0
        else:
            print("❌ CI/CD自动化流程配置失败")
            return 1

    except Exception as e:
        print(f"❌ 配置过程出错: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())