"""
数据导出模块
导出为Excel、CSV等格式
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import pandas as pd

from config.settings import EXPORT_DIR, EXPORT_FORMATS

logger = logging.getLogger(__name__)


class DataExporter:
    """数据导出器"""

    def __init__(self, export_dir: str = None):
        """
        初始化导出器

        Args:
            export_dir: 导出目录，默认使用配置中的路径
        """
        self.export_dir = Path(export_dir or EXPORT_DIR)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_announcements(self, announcements: List[Dict], format: str = 'excel') -> str:
        """
        导出公告数据

        Args:
            announcements: 公告列表
            format: 导出格式 (excel, csv)

        Returns:
            导出文件路径
        """
        if not announcements:
            logger.warning("没有数据可导出")
            return ""

        # 转换为DataFrame
        df = pd.DataFrame(announcements)

        # 选择需要的列
        columns = ['title', 'url', 'publish_date', 'source', 'scraped_at']
        df = df[[c for c in columns if c in df.columns]]

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format == 'excel':
            file_path = self.export_dir / f"announcements_{timestamp}.xlsx"
            df.to_excel(file_path, index=False, engine='openpyxl')
        elif format == 'csv':
            file_path = self.export_dir / f"announcements_{timestamp}.csv"
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            logger.error(f"不支持的导出格式: {format}")
            return ""

        logger.info(f"导出 {len(announcements)} 条公告到: {file_path}")
        return str(file_path)

    def export_contacts(self, contacts: List[Dict], format: str = 'excel') -> str:
        """
        导出联系人数据

        Args:
            contacts: 联系人列表
            format: 导出格式 (excel, csv)

        Returns:
            导出文件路径
        """
        if not contacts:
            logger.warning("没有联系人可导出")
            return ""

        # 转换为DataFrame
        df = pd.DataFrame(contacts)

        # 选择需要的列
        columns = ['company', 'contact_name', 'phone', 'email']
        df = df[[c for c in columns if c in df.columns]]

        # 去重
        df = df.drop_duplicates()

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format == 'excel':
            file_path = self.export_dir / f"contacts_{timestamp}.xlsx"
            df.to_excel(file_path, index=False, engine='openpyxl')
        elif format == 'csv':
            file_path = self.export_dir / f"contacts_{timestamp}.csv"
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            logger.error(f"不支持的导出格式: {format}")
            return ""

        logger.info(f"导出 {len(df)} 条联系人到: {file_path}")
        return str(file_path)

    def export_summary(self, stats: Dict, format: str = 'excel') -> str:
        """
        导出统计摘要

        Args:
            stats: 统计信息字典
            format: 导出格式 (excel, csv)

        Returns:
            导出文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 创建多个工作表的数据
        summary_data = {
            '总览': [
                {'项目': '公告总数', '数量': stats.get('total_announcements', 0)},
                {'项目': '联系人总数', '数量': stats.get('total_contacts', 0)},
            ],
            '按数据源': [
                {'数据源': k, '数量': v}
                for k, v in stats.get('by_source', {}).items()
            ],
            '热门公司': [
                {'公司': k, '数量': v}
                for k, v in stats.get('top_companies', {}).items()
            ],
        }

        if format == 'excel':
            file_path = self.export_dir / f"summary_{timestamp}.xlsx"

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for sheet_name, data in summary_data.items():
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

        elif format == 'csv':
            # CSV只能导出一个工作表，导出总览
            file_path = self.export_dir / f"summary_{timestamp}.csv"
            df = pd.DataFrame(summary_data['总览'])
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            logger.error(f"不支持的导出格式: {format}")
            return ""

        logger.info(f"导出统计摘要到: {file_path}")
        return str(file_path)

    def export_all(self, db, format: str = 'excel') -> Dict[str, str]:
        """
        导出所有数据

        Args:
            db: 数据库实例
            format: 导出格式

        Returns:
            各类数据的导出文件路径
        """
        results = {}

        # 导出公告
        announcements = db.get_announcements(limit=10000)
        if announcements:
            results['announcements'] = self.export_announcements(announcements, format)

        # 导出联系人
        contacts = db.get_contacts(limit=10000)
        if contacts:
            results['contacts'] = self.export_contacts(contacts, format)

        # 导出统计摘要
        stats = db.get_stats()
        results['summary'] = self.export_summary(stats, format)

        return results
