#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能指标收集器
收集系统性能数据并提供监控指标
"""

import time
import psutil
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
import asyncio
import logging
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️ Prometheus客户端未安装，性能指标收集功能受限")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis未安装，缓存功能不可用")


class MetricsCollector:
    """性能指标收集器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化指标收集器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # 指标存储
        self.metrics_data = defaultdict(deque)
        self.max_history = 1000

        # Prometheus指标
        self.prometheus_metrics = {}
        self.setup_prometheus_metrics() if PROMETHEUS_AVAILABLE else None

        # Redis客户端
        self.redis_client = None
        if self.config.get('redis', {}).get('enabled', False) and REDIS_AVAILABLE:
            try:
                redis_config = self.config['redis']
                self.redis_client = redis.Redis(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 0),
                    decode_responses=True
                )
            except Exception as e:
                self.logger.warning(f"Redis连接失败: {e}")

        # 启动时间
        self.start_time = time.time()

        # 性能监控
        self.performance_monitor = PerformanceMonitor(self)

        # 业务指标
        self.business_metrics = BusinessMetrics(self)

        # 系统指标
        self.system_metrics = SystemMetrics(self)

        # 启动指标收集线程
        self.running = False
        self.metrics_thread = None

    def setup_prometheus_metrics(self):
        """设置Prometheus指标"""
        if not PROMETHEUS_AVAILABLE:
            return

        self.prometheus_metrics['registry'] = CollectorRegistry()
        registry = self.prometheus_metrics['registry']

        # API指标
        self.prometheus_metrics['api_requests_total'] = Counter(
            'api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status'],
            registry=registry
        )

        self.prometheus_metrics['api_request_duration'] = Histogram(
            'api_request_duration_seconds',
            'API request duration',
            ['method', 'endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=registry
        )

        self.prometheus_metrics['api_active_connections'] = Gauge(
            'api_active_connections',
            'Number of active API connections',
            registry=registry
        )

        # 爬虫指标
        self.prometheus_metrics['scraper_runs_total'] = Counter(
            'scraper_runs_total',
            'Total scraper runs',
            ['source', 'status'],
            registry=registry
        )

        self.prometheus_metrics['scraper_duration'] = Histogram(
            'scraper_duration_seconds',
            'Scraper duration',
            ['source'],
            buckets=[10, 30, 60, 120, 300, 600],
            registry=registry
        )

        self.prometheus_metrics['scraper_items_collected'] = Counter(
            'scraper_items_collected_total',
            'Total items collected by scraper',
            ['source', 'type'],
            registry=registry
        )

        # 邮件指标
        self.prometheus_metrics['emails_sent_total'] = Counter(
            'emails_sent_total',
            'Total emails sent',
            ['template', 'status'],
            registry=registry
        )

        self.prometheus_metrics['email_delivery_duration'] = Histogram(
            'email_delivery_duration_seconds',
            'Email delivery duration',
            ['provider'],
            buckets=[1, 5, 10, 30, 60, 120],
            registry=registry
        )

        # 数据库指标
        self.prometheus_metrics['db_connections'] = Gauge(
            'db_connections',
            'Number of database connections',
            registry=registry
        )

        self.prometheus_metrics['db_query_duration'] = Histogram(
            'db_query_duration_seconds',
            'Database query duration',
            ['query_type'],
            buckets=[0.01, 0.1, 0.5, 1.0, 5.0, 10.0],
            registry=registry
        )

        # 系统指标
        self.prometheus_metrics['system_cpu_usage'] = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=registry
        )

        self.prometheus_metrics['system_memory_usage'] = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            registry=registry
        )

        self.prometheus_metrics['system_disk_usage'] = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            registry=registry
        )

    def start_collection(self):
        """启动指标收集"""
        if self.running:
            self.logger.warning("指标收集已在运行中")
            return

        self.running = True
        self.metrics_thread = threading.Thread(target=self._collect_metrics_loop)
        self.metrics_thread.daemon = True
        self.metrics_thread.start()

        self.logger.info("性能指标收集已启动")

    def stop_collection(self):
        """停止指标收集"""
        self.running = False
        if self.metrics_thread:
            self.metrics_thread.join(timeout=5)
        self.logger.info("性能指标收集已停止")

    def _collect_metrics_loop(self):
        """指标收集循环"""
        while self.running:
            try:
                # 收集系统指标
                system_metrics = self.collect_system_metrics()
                self._store_metrics('system', system_metrics)

                # 收集性能指标
                performance_metrics = self.performance_monitor.collect_metrics()
                self._store_metrics('performance', performance_metrics)

                # 收集业务指标
                business_metrics = self.business_metrics.collect_metrics()
                self._store_metrics('business', business_metrics)

                # 缓存指标到Redis
                if self.redis_client:
                    self._cache_metrics()

                time.sleep(10)  # 每10秒收集一次指标

            except Exception as e:
                self.logger.error(f"指标收集异常: {e}")
                time.sleep(30)  # 出错时等待30秒再重试

    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent

            # 网络IO
            network_io = psutil.net_io_counters()

            # 进程信息
            process = psutil.Process()

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_total_gb': memory.total / (1024**3),
                'disk_used_gb': disk.used / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'network_bytes_sent': network_io.bytes_sent,
                'network_bytes_recv': network_io.bytes_recv,
                'process_memory_mb': process.memory_info().rss / (1024**2),
                'process_cpu_percent': process.cpu_percent(),
                'process_threads': process.num_threads(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"系统指标收集失败: {e}")
            return {}

    def _store_metrics(self, category: str, metrics: Dict[str, Any]):
        """存储指标数据"""
        if not metrics:
            return

        timestamp = datetime.now()
        self.metrics_data[category].append({
            'timestamp': timestamp,
            'metrics': metrics
        })

        # 限制历史数据量
        if len(self.metrics_data[category]) > self.max_history:
            self.metrics_data[category].popleft()

        # 更新Prometheus指标
        if PROMETHEUS_AVAILABLE and category == 'system':
            self._update_prometheus_system_metrics(metrics)

    def _update_prometheus_system_metrics(self, metrics: Dict[str, Any]):
        """更新Prometheus系统指标"""
        if not self.prometheus_metrics:
            return

        try:
            self.prometheus_metrics['system_cpu_usage'].set(metrics.get('cpu_percent', 0))
            self.prometheus_metrics['system_memory_usage'].set(metrics.get('memory_percent', 0))
            self.prometheus_metrics['system_disk_usage'].set(metrics.get('disk_percent', 0))
        except Exception as e:
            self.logger.error(f"更新Prometheus指标失败: {e}")

    def _cache_metrics(self):
        """缓存指标到Redis"""
        if not self.redis_client:
            return

        try:
            cache_key = f"metrics:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'system': dict(self.metrics_data['system']) if self.metrics_data['system'] else {},
                'performance': dict(self.metrics_data['performance']) if self.metrics_data['performance'] else {},
                'business': dict(self.metrics_data['business']) if self.metrics_data['business'] else {}
            }

            self.redis_client.setex(
                cache_key,
                3600,  # 缓存1小时
                json.dumps(cache_data, ensure_ascii=False)
            )
        except Exception as e:
            self.logger.error(f"缓存指标到Redis失败: {e}")

    def get_system_uptime(self) -> float:
        """获取系统运行时间"""
        return time.time() - self.start_time

    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """记录API请求指标"""
        if self.prometheus_metrics:
            self.prometheus_metrics['api_requests_total'].labels(
                method=method, endpoint=endpoint, status=str(status_code)
            ).inc()

            self.prometheus_metrics['api_request_duration'].labels(
                method=method, endpoint=endpoint
            ).observe(duration)

        # 记录本地指标
        self._store_metrics('api', {
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })

    def record_scraper_run(self, source: str, status: str, duration: float, items_count: int):
        """记录爬虫运行指标"""
        if self.prometheus_metrics:
            self.prometheus_metrics['scraper_runs_total'].labels(
                source=source, status=status
            ).inc()

            self.prometheus_metrics['scraper_duration'].labels(source=source).observe(duration)

            self.prometheus_metrics['scraper_items_collected'].labels(
                source=source, type='total'
            ).inc(items_count)

        # 记录本地指标
        self._store_metrics('scraper', {
            'source': source,
            'status': status,
            'duration': duration,
            'items_count': items_count,
            'timestamp': datetime.now().isoformat()
        })

    def record_email_sent(self, template: str, status: str, duration: float):
        """记录邮件发送指标"""
        if self.prometheus_metrics:
            self.prometheus_metrics['emails_sent_total'].labels(
                template=template, status=status
            ).inc()

            self.prometheus_metrics['email_delivery_duration'].labels(
                provider='default'
            ).observe(duration)

        # 记录本地指标
        self._store_metrics('email', {
            'template': template,
            'status': status,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })

    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """获取指标摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        summary = {}

        for category, data in self.metrics_data.items():
            if not data:
                continue

            # 过滤指定时间范围内的数据
            recent_data = [
                item for item in data
                if datetime.fromisoformat(item['timestamp']) >= cutoff_time
            ]

            if not recent_data:
                continue

            # 计算统计信息
            summary[category] = {
                'count': len(recent_data),
                'latest': recent_data[-1]['metrics'] if recent_data else {}
            }

            # 计算平均值
            if category == 'system':
                cpu_values = [item['metrics'].get('cpu_percent', 0) for item in recent_data]
                memory_values = [item['metrics'].get('memory_percent', 0) for item in recent_data]

                if cpu_values:
                    summary[category]['avg_cpu'] = sum(cpu_values) / len(cpu_values)
                if memory_values:
                    summary[category]['avg_memory'] = sum(memory_values) / len(memory_values)

        return summary

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """获取实时指标"""
        try:
            current_metrics = self.collect_system_metrics()

            # 添加业务指标
            business_metrics = self.business_metrics.get_real_time_metrics()
            current_metrics.update(business_metrics)

            # 添加性能指标
            performance_metrics = self.performance_monitor.get_real_time_metrics()
            current_metrics.update(performance_metrics)

            return current_metrics
        except Exception as e:
            self.logger.error(f"获取实时指标失败: {e}")
            return {}

    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'uptime_hours': self.get_system_uptime() / 3600,
                'system_metrics': self.get_metrics_summary(24),
                'business_metrics': self.business_metrics.generate_summary(),
                'performance_metrics': self.performance_monitor.generate_summary(),
                'recommendations': self._generate_recommendations()
            }

            return report
        except Exception as e:
            self.logger.error(f"生成性能报告失败: {e}")
            return {}

    def _generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []

        try:
            # 系统指标检查
            recent_metrics = self.get_metrics_summary(1)
            system_metrics = recent_metrics.get('system', {}).get('latest', {})

            # CPU使用率检查
            if system_metrics.get('cpu_percent', 0) > 80:
                recommendations.append("CPU使用率较高，建议优化算法或增加计算资源")

            # 内存使用率检查
            if system_metrics.get('memory_percent', 0) > 85:
                recommendations.append("内存使用率较高，建议优化内存使用或增加内存")

            # 磀查是否有异常值
            for category, data in self.metrics_data.items():
                if len(data) < 10:  # 数据量不足
                    recommendations.append(f"{category}指标数据不足，请检查数据收集")
                    continue

                # 检查异常值
                last_metrics = data[-5:]  # 最近5次的数据
                if category == 'api':
                    error_count = sum(1 for item in last_metrics
                                    if item['metrics'].get('status_code', 200) >= 400)
                    if error_count > 2:
                        recommendations.append(f"API错误率较高({error_count}/5)，建议检查系统状态")

        except Exception as e:
            self.logger.error(f"生成建议失败: {e}")

        return recommendations

    def export_metrics(self, filepath: str, format: str = 'json'):
        """导出指标数据"""
        try:
            data = {
                'export_time': datetime.now().isoformat(),
                'metrics_data': dict(self.metrics_data),
                'prometheus_metrics': str(self.prometheus_metrics.get('registry', '')) if PROMETHEUS_AVAILABLE else None
            }

            if format.lower() == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif format.lower() == 'csv':
                import pandas as pd

                # 转换为DataFrame
                rows = []
                for category, data_list in self.metrics_data.items():
                    for item in data_list:
                        row = {'category': category}
                        row.update(item['metrics'])
                        row['timestamp'] = item['timestamp']
                        rows.append(row)

                df = pd.DataFrame(rows)
                df.to_csv(filepath, index=False)
            else:
                raise ValueError(f"不支持的格式: {format}")

            print(f"指标数据已导出到: {filepath}")
            return True

        except Exception as e:
            self.logger.error(f"导出指标数据失败: {e}")
            return False

    def start_prometheus_server(self, port: int = 8001):
        """启动Prometheus HTTP服务器"""
        if not PROMETHEUS_AVAILABLE:
            print("Prometheus客户端未安装，无法启动HTTP服务器")
            return

        try:
            start_http_server(self.prometheus_metrics['registry'], port)
            print(f"Prometheus HTTP服务器已启动: http://localhost:{port}")
        except Exception as e:
            self.logger.error(f"启动Prometheus服务器失败: {e}")


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)

    def collect_metrics(self) -> Dict[str, Any]:
        """收集性能指标"""
        try:
            # 内存性能
            memory_info = psutil.virtual_memory()

            # CPU性能
            cpu_info = psutil.cpu_times()

            # 进程信息
            process = psutil.Process()
            process_info = process.as_dict([
                'cpu_percent', 'memory_percent', 'memory_info', 'io_counters'
            ])

            # 网络性能
            net_io = psutil.net_io_counters()

            return {
                'memory_total_gb': memory_info.total / (1024**3),
                'memory_used_gb': memory_info.used / (1024**3),
                'memory_available_gb': memory_info.available / (1024**3),
                'memory_percent': memory_info.percent,
                'cpu_user_time': cpu_info.user,
                'cpu_system_time': cpu_info.system,
                'cpu_idle_time': cpu_info.idle,
                'process_cpu_percent': process_info.get('cpu_percent', 0),
                'process_memory_mb': process_info.get('memory_info', {}).get('rss', 0) / (1024**2),
                'process_memory_percent': process_info.get('memory_percent', 0),
                'io_read_bytes': net_io.read_bytes,
                'io_write_bytes': net_io.write_bytes,
                'network_sent_bytes': net_io.bytes_sent,
                'network_recv_bytes': net_io.bytes_recv,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"性能指标收集失败: {e}")
            return {}

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """获取实时性能指标"""
        return self.collect_metrics()

    def generate_summary(self) -> Dict[str, Any]:
        """生成性能摘要"""
        try:
            metrics = self.collect_metrics()

            return {
                'memory_efficiency': (metrics.get('memory_used_gb', 0) / metrics.get('memory_total_gb', 1)) * 100,
                'cpu_usage': metrics.get('process_cpu_percent', 0),
                'io_activity': metrics.get('io_write_bytes', 0) + metrics.get('io_read_bytes', 0),
                'network_activity': metrics.get('network_sent_bytes', 0) + metrics.get('network_recv_bytes', 0)
            }
        except Exception as e:
            self.logger.error(f"生成性能摘要失败: {e}")
            return {}


class BusinessMetrics:
    """业务指标收集器"""

    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)

    def collect_metrics(self) -> Dict[str, Any]:
        """收集业务指标"""
        try:
            # 这里应该从实际的数据库获取业务指标
            # 示例数据
            return {
                'total_contacts': 1500,
                'new_contacts_today': 25,
                'emails_sent_today': 100,
                'emails_success_rate': 95.5,
                'scraping_success_rate': 88.2,
                'data_quality_score': 92.1,
                'user_satisfaction': 4.3,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"业务指标收集失败: {e}")
            return {}

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """获取实时业务指标"""
        return self.collect_metrics()

    def generate_summary(self) -> Dict[str, Any]:
        """生成业务指标摘要"""
        try:
            metrics = self.collect_metrics()

            return {
                'contact_growth_rate': 15.2,  # 示例数据
                'email_engagement_rate': metrics.get('emails_success_rate', 0),
                'data_quality_score': metrics.get('data_quality_score', 0),
                'operational_efficiency': 87.5
            }
        except Exception as e:
            self.logger.error(f"生成业务指标摘要失败: {e}")
            return {}


class SystemMetrics:
    """系统指标收集器"""

    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)

    def collect_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            # 磁盘I/O统计
            disk_io = psutil.disk_io_counters()

            # 网络I/O统计
            net_io = psutil.net_io_counters()

            # 进程统计
            processes = len(psutil.pids())

            # 负载平均
            load_avg = psutil.getloadavg()

            return {
                'disk_read_count': disk_io.read_count,
                'disk_write_count': disk_io.write_count,
                'disk_read_bytes': disk_io.read_bytes,
                'disk_write_bytes': disk_io.write_bytes,
                'network_recv_count': net_io.packets_recv,
                'network_send_count': net_io.packets_sent,
                'network_recv_bytes': net_io.bytes_recv,
                'network_send_bytes': net_io.bytes_sent,
                'process_count': processes,
                'load_avg_1min': load_avg[0],
                'load_avg_5min': load_avg[1],
                'load_avg_15min': load_avg[2],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"系统指标收集失败: {e}")
            return {}

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """获取实时系统指标"""
        return self.collect_metrics()


# 全局指标收集器实例
metrics_collector = None

def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器实例"""
    global metrics_collector
    if metrics_collector is None:
        metrics_collector = MetricsCollector()
    return metrics_collector


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="性能指标收集器")
    parser.add_argument("--start", action="store_true", help="启动指标收集")
    parser.add_argument("--stop", action="store_true", help="停止指标收集")
    parser.add_argument("--summary", action="store_true", help="显示指标摘要")
    parser.add_argument("--export", help="导出指标数据")
    parser.add_argument("--prometheus-port", type=int, default=8001, help="Prometheus HTTP服务器端口")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="导出格式")

    args = parser.parse_args()

    try:
        collector = get_metrics_collector()

        if args.start:
            collector.start_collection()

            if args.prometheus_port:
                collector.start_prometheus_server(args.prometheus_port)

            print("指标收集已启动，按 Ctrl+C 停止")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                collector.stop_collection()
                print("指标收集已停止")

        elif args.stop:
            collector.stop_collection()

        elif args.summary:
            summary = collector.get_metrics_summary()
            print("指标摘要:")
            print(json.dumps(summary, ensure_ascii=False, indent=2))

        elif args.export:
            collector.export_metrics(args.export, args.format)

        else:
            # 显示实时指标
            metrics = collector.get_real_time_metrics()
            print("实时指标:")
            print(json.dumps(metrics, ensure_ascii=False, indent=2))

    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())