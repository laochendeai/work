#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试工具
对系统的各个组件进行性能测试和基准测试
"""

import asyncio
import time
import statistics
import json
import csv
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import concurrent.futures
import psutil
import requests

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.config_loader import ConfigLoader
    from src.utils.database_manager import DatabaseManager
    from src.monitoring.metrics import MetricsCollector
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    test_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    samples: List[float] = None


class PerformanceBenchmark:
    """性能基准测试器"""

    def __init__(self, config_path: str = "config/project_config.json"):
        self.config = ConfigLoader(config_path).load_config()
        self.results = []
        self.output_dir = Path("benchmark_results")
        self.output_dir.mkdir(exist_ok=True)

    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """运行所有基准测试"""
        print("🚀 开始性能基准测试...")
        print("=" * 60)

        # API基准测试
        api_results = self.benchmark_api()
        self.results.extend(api_results)

        # 数据库基准测试
        db_results = self.benchmark_database()
        self.results.extend(db_results)

        # 爬虫基准测试
        scraper_results = self.benchmark_scraper()
        self.results.extend(scraper_results)

        # 邮件发送基准测试
        email_results = self.benchmark_email()
        self.results.extend(email_results)

        # 系统资源基准测试
        system_results = self.benchmark_system()
        self.results.extend(system_results)

        # 生成报告
        self.generate_report()

        print("=" * 60)
        self.print_summary()

        return self.results

    def benchmark_api(self) -> List[BenchmarkResult]:
        """API性能基准测试"""
        print("🔍 API性能基准测试...")
        results = []

        # API响应时间测试
        api_time_result = self.benchmark_api_response_time()
        results.append(api_time_result)

        # API并发测试
        api_concurrent_result = self.benchmark_api_concurrency()
        results.append(api_concurrent_result)

        # API负载测试
        api_load_result = self.benchmark_api_load()
        results.append(api_load_result)

        return results

    def benchmark_api_response_time(self) -> BenchmarkResult:
        """测试API响应时间"""
        test_name = "API响应时间"
        samples = []
        iterations = 100

        try:
            # 预热
            for _ in range(10):
                self._make_api_request("/health")

            # 正式测试
            start_time = time.time()
            for i in range(iterations):
                request_start = time.time()
                response = self._make_api_request("/stats")
                request_end = time.time()

                samples.append(request_end - request_start)

                if i % 20 == 0:
                    print(f"  完成第 {i+1}/{iterations} 次请求")

            end_time = time.time()
            duration = end_time - start_time

            metrics = {
                'iterations': iterations,
                'min_time': min(samples),
                'max_time': max(samples),
                'avg_time': statistics.mean(samples),
                'median_time': statistics.median(samples),
                'p95_time': sorted(samples)[int(len(samples) * 0.95)],
                'p99_time': sorted(samples)[int(len(samples) * 0.99)],
                'std_dev': statistics.stdev(samples) if len(samples) > 1 else 0
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics,
                samples=samples
            )

            print(f"  ✅ {test_name}: 平均响应时间 {metrics['avg_time']:.3f}ms")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_api_concurrency(self) -> BenchmarkResult:
        """测试API并发性能"""
        test_name = "API并发测试"
        concurrent_users = [10, 20, 50, 100]
        results = []

        for users in concurrent_users:
            print(f"  测试并发用户数: {users}")
            start_time = time.time()

            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
                    futures = []
                    for i in range(50):  # 每个并发级别发送50个请求
                        future = executor.submit(self._make_api_request, "/stats")
                        futures.append(future)

                    # 等待所有请求完成
                    completed_futures = concurrent.futures.as_completed(futures)
                    request_times = []

                    for future in completed_futures:
                        request_start = time.time()
                        try:
                            future.result()
                            request_end = time.time()
                            request_times.append(request_end - request_start)
                        except Exception:
                            request_times.append(float('inf'))

                end_time = time.time()
                duration = end_time - start_time

                success_rate = sum(1 for t in request_times if t != float('inf')) / len(request_times)
                avg_time = statistics.mean([t for t in request_times if t != float('inf')])

                results.append({
                    'concurrent_users': users,
                    'requests': 50,
                    'duration': duration,
                    'success_rate': success_rate,
                    'avg_response_time': avg_time
                })

            except Exception as e:
                print(f"  ❌ 并发测试失败 (用户数: {users}): {e}")

        # 计算总体指标
        avg_success_rate = statistics.mean([r['success_rate'] for r in results])
        avg_response_time = statistics.mean([r['avg_response_time'] for r in results])

        metrics = {
            'concurrent_users': concurrent_users,
            'results': results,
            'avg_success_rate': avg_success_rate,
            'avg_response_time': avg_response_time
        }

        result = BenchmarkResult(
            test_name=test_name,
            start_time=0,
            end_time=0,
            duration=0,
            success=True,
            metrics=metrics
        )

        print(f"  ✅ {test_name}: 平均成功率 {avg_success_rate:.1%}, 平均响应时间 {avg_response_time:.3f}ms")
        return result

    def benchmark_api_load(self) -> BenchmarkResult:
        """测试API负载能力"""
        test_name = "API负载测试"
        duration_seconds = 60
        requests_per_second = 10

        try:
            start_time = time.time()
            end_time = start_time + duration_seconds
            request_times = []
            success_count = 0
            total_requests = 0

            while time.time() < end_time:
                # 在指定时间内发送请求
                request_start = time.time()
                response = self._make_api_request("/stats")
                request_end = time.time()

                if response and response.status_code == 200:
                    success_count += 1

                request_times.append(request_end - request_start)
                total_requests += 1

                # 控制请求频率
                time.sleep(1.0 / requests_per_second)

            actual_duration = time.time() - start_time
            success_rate = success_count / total_requests
            throughput = total_requests / actual_duration

            metrics = {
                'duration_seconds': actual_duration,
                'total_requests': total_requests,
                'success_count': success_count,
                'success_rate': success_rate,
                'throughput_rps': throughput,
                'avg_response_time': statistics.mean(request_times),
                'requests_per_second_target': requests_per_second
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=time.time(),
                duration=actual_duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 吞吐量 {throughput:.1f} req/s, 成功率 {success_rate:.1%}")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def _make_api_request(self, endpoint: str) -> requests.Response:
        """发送API请求"""
        try:
            base_url = "http://localhost:8000"
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            return response
        except Exception:
            return None

    def benchmark_database(self) -> List[BenchmarkResult]:
        """数据库性能基准测试"""
        print("🗄️ 数据库性能基准测试...")
        results = []

        # 连接测试
        conn_result = self.benchmark_database_connection()
        results.append(conn_result)

        # 查询性能测试
        query_result = self.benchmark_database_queries()
        results.append(query_result)

        # 写入性能测试
        write_result = self.benchmark_database_writes()
        results.append(write_result)

        # 批量操作测试
        bulk_result = self.benchmark_database_bulk_operations()
        results.append(bulk_result)

        return results

    def benchmark_database_connection(self) -> BenchmarkResult:
        """测试数据库连接性能"""
        test_name = "数据库连接"
        samples = []
        iterations = 100

        try:
            # 获取数据库管理器
            db_manager = DatabaseManager(self.config['database'])

            # 连接测试
            start_time = time.time()
            for i in range(iterations):
                conn_start = time.time()
                connection = db_manager.get_connection()
                conn_end = time.time()

                if connection:
                    connection.close()

                samples.append(conn_end - conn_start)

                if i % 20 == 0:
                    print(f"  完成第 {i+1}/{iterations} 次连接")

            end_time = time.time()
            duration = end_time - start_time

            metrics = {
                'iterations': iterations,
                'min_time': min(samples),
                'max_time': max(samples),
                'avg_time': statistics.mean(samples),
                'median_time': statistics.median(samples)
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics,
                samples=samples
            )

            print(f"  ✅ {test_name}: 平均连接时间 {metrics['avg_time']:.3f}ms")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_database_queries(self) -> BenchmarkResult:
        """测试数据库查询性能"""
        test_name = "数据库查询"

        try:
            db_manager = DatabaseManager(self.config['database'])
            samples = []

            # 测试不同类型的查询
            queries = [
                ("SELECT COUNT(*) FROM contacts", "计数查询"),
                ("SELECT * FROM contacts LIMIT 10", "简单查询"),
                ("SELECT * FROM contacts WHERE email LIKE '%@%' LIMIT 10", "条件查询"),
                ("SELECT c.*, s.status FROM contacts c LEFT JOIN scrapers s ON c.scraper_id = s.id LIMIT 20", "联表查询")
            ]

            for query, query_name in queries:
                query_start = time.time()
                db_manager.execute_query(query)
                query_end = time.time()

                samples.append({
                    'query_type': query_name,
                    'duration': query_end - query_start
                })

            # 计算统计信息
            durations = [s['duration'] for s in samples]

            metrics = {
                'queries_tested': len(queries),
                'avg_duration': statistics.mean(durations),
                'max_duration': max(durations),
                'total_duration': sum(durations)
            }

            end_time = time.time()

            result = BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=end_time,
                duration=end_time,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 平均查询时间 {metrics['avg_duration']:.3f}s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_database_writes(self) -> BenchmarkResult:
        """测试数据库写入性能"""
        test_name = "数据库写入"

        try:
            db_manager = DatabaseManager(self.config['database'])
            samples = []
            iterations = 100

            # 测试插入操作
            start_time = time.time()
            for i in range(iterations):
                insert_start = time.time()
                db_manager.save_contact({
                    'name': f'Test Contact {i}',
                    'email': f'test{i}@example.com',
                    'phone': f'1234567890{i:03}',
                    'company': 'Test Company',
                    'created_at': datetime.now()
                })
                insert_end = time.time()

                samples.append(insert_end - insert_start)

                if i % 20 == 0:
                    print(f"  完成第 {i+1}/{iterations} 次插入")

            end_time = time.time()
            duration = end_time - start_time

            metrics = {
                'iterations': iterations,
                'min_time': min(samples),
                'max_time': max(samples),
                'avg_time': statistics.mean(samples),
                'total_time': duration,
                'throughput_ops': iterations / duration
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 吞吐量 {metrics['throughput_ops']:.1f} ops/s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_database_bulk_operations(self) -> BenchmarkResult:
        """测试数据库批量操作性能"""
        test_name = "批量操作"

        try:
            db_manager = DatabaseManager(self.config['database'])
            batch_size = 100
            total_records = 1000

            # 准备测试数据
            test_data = []
            for i in range(total_records):
                test_data.append({
                    'name': f'Bulk Contact {i}',
                    'email': f'bulk{i}@example.com',
                    'phone': f'98765432{i:03}',
                    'company': f'Bulk Company {i}',
                    'created_at': datetime.now()
                })

            # 批量插入测试
            start_time = time.time()

            for i in range(0, total_records, batch_size):
                batch = test_data[i:i+batch_size]
                db_manager.save_contacts_batch(batch)
                print(f"  完成批量插入 {i+len(batch)}/{total_records}")

            end_time = time.time()
            duration = end_time - start_time

            metrics = {
                'total_records': total_records,
                'batch_size': batch_size,
                'duration': duration,
                'throughput_ops': total_records / duration
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 吞吐量 {metrics['throughput_ops']:.1f} ops/s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_scraper(self) -> List[BenchmarkResult]:
        """爬虫性能基准测试"""
        print("🕷️ 爬虫性能基准测试...")
        results = []

        # 爬取速度测试
        speed_result = self.benchmark_scraper_speed()
        results.append(speed_result)

        # 内存使用测试
        memory_result = self.benchmark_scraper_memory()
        results.append(memory_result)

        # 并发爬取测试
        concurrent_result = self.benchmark_scraper_concurrent()
        results.append(concurrent_result)

        return results

    def benchmark_scraper_speed(self) -> BenchmarkResult:
        """测试爬虫速度"""
        test_name = "爬虫速度"

        try:
            # 模拟爬虫操作
            items_per_page = 100
            pages = 10
            total_items = items_per_page * pages

            times = []
            start_time = time.time()

            for page in range(pages):
                page_start = time.time()

                # 模拟页面爬取
                items = []
                for i in range(items_per_page):
                    items.append({
                        'id': f'item_{page}_{i}',
                        'title': f'Item {page}-{i}',
                        'url': f'http://example.com/page{page}/item{i}'
                    })

                time.sleep(0.01)  # 模拟网络延迟

                page_end = time.time()
                times.append(page_end - page_start)

            end_time = time.time()
            duration = end_time - start_time

            metrics = {
                'total_pages': pages,
                'items_per_page': items_per_page,
                'total_items': total_items,
                'duration': duration,
                'pages_per_second': pages / duration,
                'items_per_second': total_items / duration,
                'avg_page_time': statistics.mean(times)
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 爬取速度 {metrics['items_per_second']:.1f} items/s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_scraper_memory(self) -> Benchmark_result:
        """测试爬虫内存使用"""
        test_name = "爬虫内存使用"

        try:
            # 记录初始内存
            initial_memory = psutil.Process().memory_info().rss

            # 模拟内存密集的爬取操作
            large_data = []
            for i in range(10000):
                large_data.append({
                    'id': f'id_{i}',
                    'title': f'Title {i}' * 100,  # 长标题占用内存
                    'description': f'Description {i}' * 200,
                    'content': f'Content {i}' * 300
                })

                if i % 1000 == 0:
                    current_memory = psutil.Process().memory_info().rss
                    print(f"  内存使用: {(current_memory - initial_memory) / 1024 / 1024:.1f}MB")

            final_memory = psutil.Process().memory_info().rss
            end_time = time.time()

            metrics = {
                'initial_memory_mb': initial_memory / (1024 * 1024),
                'final_memory_mb': final_memory / (1024 * 1024),
                'memory_increase_mb': (final_memory - initial_memory) / (1024 * 1024),
                'data_items': len(large_data)
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=end_time,
                duration=end_time - time.time(),
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 内存增长 {metrics['memory_increase_mb']:.1f}MB")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_scraper_concurrent(self) -> Benchmark_result:
        """测试并发爬取性能"""
        test_name = "并发爬取"

        try:
            max_workers = 10
            sites = [
                'http://example.com/site1',
                'http://example.com/site2',
                'http://example.com/site3',
                'http://example.com/site4',
                'http://example.com/site5'
            ]

            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []

                for site in sites:
                    for worker in range(2):  # 每个站点2个工作线程
                        future = executor.submit(self._scrape_site, site, 10)
                        futures.append(future)

                # 等待所有爬取完成
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            end_time = time.time()
            duration = end_time - start_time

            total_sites = len(sites)
            total_requests = total_sites * 2 * 10  # 2个线程，每个站点10页

            metrics = {
                'max_workers': max_workers,
                'total_sites': total_sites,
                'total_requests': total_requests,
                'duration': duration,
                'throughput_rps': total_requests / duration,
                'success_rate': len([r for r in results if r]) / len(results)
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 吞吐量 {metrics['throughput_rps']:.1f} req/s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def _scrape_site(self, site: str, pages: int) -> bool:
        """模拟站点爬取"""
        try:
            for page in range(pages):
                # 模拟网络请求
                time.sleep(0.1)
                # 模拟页面处理
                time.sleep(0.05)
            return True
        except Exception:
            return False

    def benchmark_email(self) -> List[BenchmarkResult]:
        """邮件发送性能基准测试"""
        print("📧 邮件发送性能基准测试...")
        results = []

        # 单封邮件发送测试
        single_result = self.benchmark_email_single()
        results.append(single_result)

        # 批量邮件发送测试
        bulk_result = self.benchmark_email_bulk()
        results.append(bulk_result)

        return results

    def benchmark_email_single(self) -> BenchmarkResult:
        """测试单封邮件发送性能"""
        test_name = "单封邮件发送"
        samples = []
        iterations = 50

        try:
            start_time = time.time()
            for i in range(iterations):
                email_start = time.time()

                # 模拟邮件发送
                self._send_email({
                    'to': f'test{i}@example.com',
                    'subject': f'Test Email {i}',
                    'content': f'This is test email {i}'
                })

                email_end = time.time()
                samples.append(email_end - email_start)

                if i % 10 == 0:
                    print(f"  完成第 {i+1}/{iterations} 封邮件")

            end_time = time.time()
            duration = end_time - start_time

            metrics = {
                'iterations': iterations,
                'min_time': min(samples),
                'max_time': max(samples),
                'avg_time': statistics.mean(samples),
                'total_time': duration,
                'emails_per_second': iterations / duration
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics,
                samples=samples
            )

            print(f"  ✅ {test_name}: 发送速度 {metrics['emails_per_second']:.1f} emails/s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_email_bulk(self) -> BenchmarkResult:
        """测试批量邮件发送性能"""
        test_name = "批量邮件发送"

        try:
            batch_sizes = [10, 50, 100]
            results = []

            for batch_size in batch_sizes:
                print(f"  测试批量大小: {batch_size}")

                batch_start = time.time()

                # 准备邮件数据
                emails = []
                for i in range(batch_size):
                    emails.append({
                        'to': f'batch_test{i}@example.com',
                        'subject': f'Bulk Test Email {i}',
                        'content': f'This is bulk test email {i}'
                    })

                # 模拟批量发送
                for email in emails:
                    self._send_email(email)
                    time.sleep(0.01)  # 模拟发送延迟

                batch_end = time.time()
                duration = batch_end - batch_start

                results.append({
                    'batch_size': batch_size,
                    'duration': duration,
                    'throughput_emails_per_second': batch_size / duration
                })

            # 计算总体指标
            total_emails = sum(r['batch_size'] for r in results)
            total_duration = sum(r['duration'] for r in results)
            avg_throughput = total_emails / total_duration

            metrics = {
                'batch_sizes': batch_sizes,
                'results': results,
                'total_emails': total_emails,
                'total_duration': total_duration,
                'avg_throughput': avg_throughput
            }

            end_time = time.time()

            result = BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=end_time,
                duration=total_duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 平均吞吐量 {avg_throughput:.1f} emails/s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def _send_email(self, email_data: Dict[str, Any]):
        """模拟邮件发送"""
        # 这里应该调用实际的邮件发送逻辑
        time.sleep(0.05)  # 模拟发送时间

    def benchmark_system(self) -> List[BenchmarkResult]:
        """系统资源基准测试"""
        print("💻 系统资源基准测试...")
        results = []

        # CPU性能测试
        cpu_result = self.benchmark_cpu()
        results.append(cpu_result)

        # 内存性能测试
        memory_result = self.benchmark_memory()
        results.append(memory_result)

        # 磁盘I/O测试
        io_result = self.benchmark_io()
        results.append(io_result)

        return results

    def benchmark_cpu(self) -> BenchmarkResult:
        """测试CPU性能"""
        test_name = "CPU性能测试"

        try:
            # CPU密集型任务
            duration = 30  # 测试30秒
            start_time = time.time()

            # 执行CPU密集型计算
            result = sum(i * i for i in range(1000000))

            end_time = time.time()
            actual_duration = end_time - start_time

            # 计算CPU性能指标
            cpu_percent = psutil.cpu_percent(interval=1)

            metrics = {
                'computation_result': result,
                'duration': actual_duration,
                'cpu_percent': cpu_percent,
                'performance_ops_per_second': 1000000 / actual_duration
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=actual_duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: CPU性能 {metrics['performance_ops_per_second']:.0f} ops/s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_memory(self) -> BenchmarkResult:
        """测试内存性能"""
        test_name = "内存性能测试"

        try:
            # 内存密集型任务
            large_list = []

            start_time = time.time()

            # 分配大量内存
            for i in range(100000):
                large_list.append([{
                    'id': i,
                    'data': list(range(100)),
                    'nested': {'a': list(range(50)), 'b': list(range(30))}
                }])

            end_time = time.time()
            duration = end_time - start_time

            # 内存使用情况
            memory_info = psutil.virtual_memory()
            process_info = psutil.Process().memory_info()

            metrics = {
                'duration': duration,
                'list_size': len(large_list),
                'system_memory_used_gb': memory_info.used / (1024**3),
                'process_memory_mb': process_info.rss / (1024**2),
                'memory_efficiency': len(large_list) / (process_info.rss / 1024)
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 内存效率 {metrics['memory_efficiency']:.1f} items/MB")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def benchmark_io(self) -> BenchmarkResult:
        """测试I/O性能"""
        test_name = "I/O性能测试"

        try:
            # I/O密集型任务
            temp_file = self.output_dir / f"benchmark_io_{int(time.time())}.tmp"

            start_time = time.time()

            # 写入测试
            write_times = []
            for i in range(1000):
                write_start = time.time()
                with open(temp_file, 'a') as f:
                    f.write(f"Test line {i}\n" * 100)
                write_end = time.time()
                write_times.append(write_end - write_start)

            # 读取测试
            read_times = []
            for i in range(1000):
                read_start = time.time()
                with open(temp_file, 'r') as f:
                    f.read()
                read_end = time.time()
                read_times.append(read_end - read_start)

            end_time = time.time()
            duration = end_time - start_time

            # 删除临时文件
            temp_file.unlink()

            metrics = {
                'duration': duration,
                'write_iterations': len(write_times),
                'read_iterations': len(read_times),
                'avg_write_time': statistics.mean(write_times),
                'avg_read_time': statistics.mean(read_times),
                'write_speed_mb_s': 0.1 * len(write_times) / duration,  # 假设每行100字节
                'read_speed_mb_s': 0.1 * len(read_times) / duration
            }

            result = BenchmarkResult(
                test_name=test_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metrics=metrics
            )

            print(f"  ✅ {test_name}: 写入速度 {metrics['write_speed_mb_s']:.1f} MB/s")
            return result

        except Exception as e:
            return BenchmarkResult(
                test_name=test_name,
                start_time=0,
                end_time=0,
                duration=0,
                success=False,
                error_message=str(e)
            )

    def generate_report(self) -> None:
        """生成基准测试报告"""
        report = {
            'test_time': datetime.now().isoformat(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'disk_total_gb': psutil.disk_usage('/').total / (1024**3),
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            'results_summary': {
                'total_tests': len(self.results),
                'successful_tests': len([r for r in self.results if r.success]),
                'failed_tests': len([r for r in self.results if not r.success]),
                'success_rate': len([r for r in self.results if r.success]) / len(self.results) * 100 if self.results else 0
            },
            'results': []
        }

        for result in self.results:
            report_result = {
                'test_name': result.test_name,
                'start_time': result.start_time,
                'end_time': result.end_time,
                'duration': result.duration,
                'success': result.success,
                'error_message': result.error_message,
                'metrics': result.metrics
            }

            if result.samples:
                report_result['sample_stats'] = {
                    'count': len(result.samples),
                    'min': min(result.samples),
                    'max': max(result.samples),
                    'avg': statistics.mean(result.samples),
                    'median': statistics.median(result.samples),
                    'std_dev': statistics.stdev(result.samples) if len(result.samples) > 1 else 0
                }

            report['results'].append(report_result)

        # 生成HTML报告
        self._generate_html_report(report)

        # 生成JSON报告
        json_file = self.output_dir / "benchmark_report.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 生成CSV报告
        self._generate_csv_report(report)

        print(f"📊 基准测试报告已生成: {self.output_dir}")

    def _generate_html_report(self, report: Dict[str, Any]):
        """生成HTML格式的基准测试报告"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>性能基准测试报告</title>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background-color: #333;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px;
                }}
                .summary {{
                    background: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .test-result {{
                    margin: 20px 0;
                    padding: 20px;
                    border-radius: 8px;
                    background: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .success {{
                    border-left: 4px solid #28a745;
                }}
                .failed {{
                    border-left: 4px solid #dc3545;
                }}
                .metric {{
                    margin: 10px 0;
                    padding: 5px 10px;
                    background: #f8f9fa;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }}
                th, td {{
                    padding: 8px 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>性能基准测试报告</h1>
                <p>生成时间: {report['test_time']}</p>
            </div>

            <div class="summary">
                <h2>测试摘要</h2>
                <div class="metric">总测试数: {report['results_summary']['total_tests']}</div>
                <div class="metric">成功测试数: {report['results_summary']['successful_tests']}</div>
                <div class="metric">失败测试数: {report['results_summary']['failed_tests']}</div>
                <div class="metric">成功率: {report['results_summary']['success_rate']:.1f}%</div>
            </div>

            <div class="test-results">
                <h2>测试结果详情</h2>
                {self._generate_results_html(report['results'])}
            </div>

            <div class="system-info">
                <h2>系统信息</h2>
                <div class="metric">CPU核心数: {report['system_info']['cpu_count']}</div>
                <div class="metric">总内存: {report['system_info']['memory_total_gb']:.1f} GB</div>
                <div class="metric">总磁盘: {report['system_info']['disk_total_gb']:.1f} GB</div>
                <div class="metric">Python版本: {report['system_info']['python_version']}</div>
            </div>
        </body>
        </html>
        """

        html_file = self.output_dir / "benchmark_report.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _generate_results_html(self, results: List[Dict[str, Any]]) -> str:
        """生成测试结果的HTML"""
        html_parts = []

        for result in results:
            status_class = "success" if result['success'] else "failed"
            status_text = "成功" if result['success'] else "失败"

            html_parts.append(f"""
                <div class="test-result {status_class}">
                    <h3>{result['test_name']}</h3>
                    <div class="metric">状态: {status_text}</div>
                    <div class="metric">持续时间: {result['duration']:.3f}s</div>
                    {self._generate_metrics_html(result['metrics']) if result['metrics'] else ''}
                    {self._generate_samples_html(result.get('sample_stats')) if 'sample_stats' in result else ''}
                </div>
            """)

        return "".join(html_parts)

    def _generate_metrics_html(self, metrics: Dict[str, Any]) -> str:
        """生成指标详情的HTML"""
        if not metrics:
            return ""

        html_parts = []
        for key, value in metrics.items():
            html_parts.append(f"<div class='metric'>{key}: {value}</div>")

        return "".join(html_parts)

    def _generate_samples_html(self, sample_stats: Dict[str, Any]) -> str:
        """生成样本统计的HTML"""
        if not sample_stats:
            return ""

        return f"""
            <div class="metric">样本数: {sample_stats['count']}</div>
            <div class="metric">最小值: {sample_stats['min']:.3f}</div>
            <div class="metric">最大值: {sample_stats['max']:.3f}</div>
            <div class="metric">平均值: {sample_stats['avg']:.3f}</div>
            <div class="metric">中位数: {sample_stats['median']:.3f}</div>
        """

    def _generate_csv_report(self, report: Dict[str, Any]) -> None:
        """生成CSV格式的基准测试报告"""
        csv_file = self.output_dir / "benchmark_results.csv"

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 写入标题行
            writer.writerow([
                '测试名称', '开始时间', '结束时间', '持续时间', '成功状态', '错误消息'
            ])

            # 写入结果数据
            for result in report['results']:
                writer.writerow([
                    result['test_name'],
                    result['start_time'],
                    result['end_time'],
                    result['duration'],
                    result['success'],
                    result.get('error_message', '')
                ])

        print(f"CSV报告已生成: {csv_file}")

    def print_summary(self):
        """打印测试摘要"""
        print(f"\n📊 基准测试报告摘要")
        print("=" * 50)

        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r.success])
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"总测试数: {total_tests}")
        print(f"成功测试数: {successful_tests}")
        print(f"失败测试数: {failed_tests}")
        print(f"成功率: {success_rate:.1f}%")

        # 按类别统计
        categories = {}
        for result in self.results:
            if result.success:
                category = result.test_name.split()[0]
                categories[category] = categories.get(category, 0) + 1

        print(f"\n📊 按类别统计:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count} 个测试")

        # 性能摘要
        print(f"\n⚡ 性能摘要:")

        # API性能
        api_results = [r for r in self.results if 'API' in r.test_name]
        if api_results:
            api_times = [r.metrics.get('avg_time', 0) for r in api_results if r.metrics]
            if api_times:
                avg_api_time = statistics.mean(api_times)
                print(f"  API平均响应时间: {avg_api_time:.3f}ms")

        # 数据库性能
        db_results = [r for r in self.results if '数据库' in r.test_name]
        if db_results:
            db_throughputs = [r.metrics.get('throughput_ops_per_second', 0) for r in db_results if r.metrics]
            if db_throughputs:
                avg_db_throughput = statistics.mean(db_throughputs)
                print(f"  数据库平均吞吐量: {avg_db_throughput:.1f} ops/s")

        # 爬虫性能
        scraper_results = [r for r in self.results if '爬虫' in r.test_name]
        if scraper_results:
            scraper_speeds = [r.metrics.get('items_per_second', 0) for r in scraper_results if r.metrics]
            if scraper_speeds:
                avg_scraper_speed = statistics.mean(scraper_speeds)
                print(f"  爬虫平均速度: {avg_scraper_speed:.1f} items/s")

        # 系统性能
        system_results = [r for r in self.results if '系统' in r.test_name]
        if system_results:
            cpu_metrics = [r.metrics.get('performance_ops_per_second', 0) for r in system_results if r.metrics]
            if cpu_metrics:
                avg_cpu_performance = statistics.mean(cpu_metrics)
                print(f"  CPU平均性能: {avg_cpu_performance:.0f} ops/s")

        print("\n🔧 建议:")
        self._generate_recommendations()

    def _generate_recommendations(self):
        """生成优化建议"""
        recommendations = []

        # 基于测试结果生成建议
        for result in self.results:
            if not result.success:
                recommendations.append(f"修复 {result.test_name} 失败的原因: {result.error_message}")
                continue

            if result.metrics:
                    # API性能建议
                    if 'avg_time' in result.metrics and result.metrics['avg_time'] > 100:  # 100ms
                        recommendations.append("优化API响应时间，考虑添加缓存或数据库优化")

                    # 数据库性能建议
                    if 'throughput_ops_per_second' in result.metrics and result.metrics['throughput_per_second'] < 100:
                        recommendations.append("优化数据库查询性能，考虑添加索引或查询优化")

                    # 系统资源建议
                    if 'memory_increase_mb' in result.metrics and result.metrics['memory_increase_mb'] > 100:
                        recommendations.append("优化内存使用，考虑内存泄漏检测和优化")

        # 去重建议
        if recommendations:
            print("  " + "\n  ".join(set(recommendations)))
        else:
            print("  所有测试性能表现良好")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="性能基准测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python performance_benchmark.py --all
  python performance_benchmark.py --component api
  python performance_benchmark.py --report-format html
        """
    )

    parser.add_argument(
        "--component",
        choices=["api", "database", "scraper", "email", "system", "all"],
        default="all",
        help="测试组件 (默认: all)"
    )

    parser.add_argument(
        "--report-format",
        choices=["json", "html", "csv"],
        default="all",
        help="报告格式 (默认: all)"
    )

    args = parser.parse_args()

    try:
        benchmark = PerformanceBenchmark()

        if args.component == "all":
            results = benchmark.run_all_benchmarks()
        else:
            if args.component == "api":
                results = benchmark.benchmark_api()
            elif args.component == "database":
                results = benchmark.benchmark_database()
            elif args.component == "scraper":
                results = benchmark.benchmark_scraper()
            elif args.component == "email":
                results = benchmark.benchmark_email()
            elif args.component == "system":
                results = benchmark.benchmark_system()

        # 生成报告
        if args.report_format == "all" or "html" in args.report_format:
            benchmark.generate_report()

        if "json" in args.report_format:
            # JSON报告已在generate_report中生成
            pass

        if "csv" in args.report_format:
            # CSV报告已在generate_report中生成
            pass

        print("\n🎉 基准测试完成！")

        return 0 if results else 1

    except KeyboardInterrupt:
        print("\n⏹️ 基准测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 基准测试失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())