"""
智能表格解析器
支持复杂表格结构的解析（包括colspan和rowspan）
"""
import logging
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class SmartTableParser:
    """智能表格解析器"""

    def parse_table(self, table: Tag) -> Dict:
        """
        解析表格，正确处理colspan和rowspan

        Args:
            table: BeautifulSoup的table元素

        Returns:
            解析结果字典
        """
        # 1. 构建二维网格，处理colspan和rowspan
        grid = self._build_table_grid(table)

        # 2. 解析为键值对
        kv_data = self._parse_as_key_value(grid)

        # 3. 提取结构化信息
        structured = self._extract_structured_data(grid, kv_data)

        return {
            'grid': grid,
            'key_value': kv_data,
            'structured': structured,
        }

    def _build_table_grid(self, table: Tag) -> List[List[Dict]]:
        """
        构建表格二维网格

        处理colspan和rowspan，确保每个单元格在正确的位置

        Returns:
            二维列表，每个元素是单元格信息字典
        """
        rows = table.find_all('tr')
        if not rows:
            return []

        # 首先确定网格的列数
        max_cols = 0
        for row in rows:
            cells = row.find_all(['td', 'th'], recursive=False)
            col_count = sum(int(cell.get('colspan', 1)) for cell in cells)
            max_cols = max(max_cols, col_count)

        # 初始化网格
        grid = [[None for _ in range(max_cols)] for _ in range(len(rows))]

        # 填充网格
        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'], recursive=False)
            col_idx = 0

            for cell in cells:
                # 找到第一个空位置
                while col_idx < max_cols and grid[row_idx][col_idx] is not None:
                    col_idx += 1

                if col_idx >= max_cols:
                    break

                # 获取单元格属性
                colspan = int(cell.get('colspan', 1))
                rowspan = int(cell.get('rowspan', 1))
                text = cell.get_text(strip=True)

                # 创建单元格信息
                cell_info = {
                    'text': text,
                    'row': row_idx,
                    'col': col_idx,
                    'colspan': colspan,
                    'rowspan': rowspan,
                    'is_header': cell.name == 'th' or 'title' in cell.get('class', []),
                    'raw_element': cell,
                }

                # 填充到网格（考虑colspan和rowspan）
                for r in range(row_idx, min(row_idx + rowspan, len(grid))):
                    for c in range(col_idx, min(col_idx + colspan, max_cols)):
                        if grid[r][c] is None:
                            grid[r][c] = cell_info

                col_idx += colspan

        return grid

    def _parse_as_key_value(self, grid: List[List[Dict]]) -> Dict:
        """
        将表格解析为键值对

        策略：
        - 第一列通常是键（标题）
        - 第二列（或后续列）是值
        - 跨行合并的单元格可能是分组标题
        """
        result = {}

        for row in grid:
            if not row:
                continue

            # 找到第一个非空单元格作为键
            key_cell = None
            key_col = -1
            for col_idx, cell in enumerate(row):
                if cell and cell['text'] and cell['row'] == row[0]['row'] if row else True:
                    key_cell = cell
                    key_col = col_idx
                    break

            if not key_cell:
                continue

            key = key_cell['text'].rstrip('：:')

            # 判断是否是分组标题（跨多列）
            if key_cell['colspan'] > 2 or not key_cell.get('is_header', False):
                # 这可能是分组标题，跳过
                continue

            # 获取值（下一列或后续列），避免重复
            value_parts = []
            seen_values = set()
            for col_idx in range(key_col + 1, len(row)):
                cell = row[col_idx]
                if cell and cell['text'] and cell['row'] == row[0]['row']:
                    # 避免重复（相同内容只添加一次）
                    if cell['text'] not in seen_values:
                        value_parts.append(cell['text'])
                        seen_values.add(cell['text'])

            value = ' '.join(value_parts).strip()

            if value:
                result[key] = value

        return result

    def _extract_structured_data(self, grid: List[List[Dict]], kv_data: Dict) -> Dict:
        """
        从表格中提取结构化数据

        识别常见字段并分类
        """
        structured = {
            'project_info': {},
            'buyer': {},
            'agent': {},
            'supplier': {},
            'contacts': {},
            'amount': {},
            'experts': '',
            'attachments': [],
        }

        # 字段映射规则
        field_mappings = {
            # 项目信息
            '采购项目名称': ('project_info', 'name'),
            '项目名称': ('project_info', 'name'),
            '品目': ('project_info', 'category'),
            '行政区域': ('project_info', 'region'),
            '公告时间': ('project_info', 'publish_date'),
            '公告日期': ('project_info', 'publish_date'),

            # 采购人
            '采购单位': ('buyer', 'name'),
            '采购人': ('buyer', 'name'),
            '采购单位地址': ('buyer', 'address'),
            '采购人地址': ('buyer', 'address'),
            '采购单位联系方式': ('buyer', 'contact'),
            '采购人联系方式': ('buyer', 'contact'),

            # 代理机构
            '代理机构名称': ('agent', 'name'),
            '代理机构': ('agent', 'name'),
            '代理机构地址': ('agent', 'address'),
            '代理机构联系方式': ('agent', 'contact'),

            # 供应商（中标人）
            '供应商名称': ('supplier', 'name'),
            '中标人': ('supplier', 'name'),
            '中标单位': ('supplier', 'name'),
            '供应商地址': ('supplier', 'address'),
            '中标人地址': ('supplier', 'address'),

            # 金额
            '总中标金额': ('amount', 'total'),
            '中标金额': ('amount', 'bid'),
            '成交金额': ('amount', 'bid'),

            # 专家
            '评审专家名单': ('experts', ''),
            '评审专家': ('experts', ''),

            # 联系人
            '项目联系人': ('contacts', 'name'),
            '项目联系电话': ('contacts', 'phone'),
            '联系人': ('contacts', 'name'),
            '联系电话': ('contacts', 'phone'),
        }

        # 应用映射
        for key, value in kv_data.items():
            # 精确匹配
            if key in field_mappings:
                category, field = field_mappings[key]
                if category == 'experts':
                    structured[category] = value
                elif category == 'attachments':
                    structured[category].append({'name': value})
                else:
                    structured[category][field] = value
            else:
                # 模糊匹配
                for pattern, (category, field) in field_mappings.items():
                    if pattern in key or key in pattern:
                        if category == 'experts':
                            structured[category] = value
                        elif category == 'attachments':
                            structured[category].append({'name': value})
                        else:
                            structured[category][field] = value
                        break

        return structured

    def analyze_table_structure(self, table: Tag) -> Dict:
        """
        分析表格结构

        Returns:
            表格结构信息
        """
        rows = table.find_all('tr')
        if not rows:
            return {}

        # 统计
        total_rows = len(rows)
        max_cols = 0
        has_colspan = False
        has_rowspan = False
        header_rows = 0

        for row in rows:
            cells = row.find_all(['td', 'th'], recursive=False)
            for cell in cells:
                colspan = int(cell.get('colspan', 1))
                rowspan = int(cell.get('rowspan', 1))
                max_cols = max(max_cols, colspan)

                if colspan > 1:
                    has_colspan = True
                if rowspan > 1:
                    has_rowspan = True

                if cell.name == 'th' or 'title' in cell.get('class', []):
                    header_rows += 1

        return {
            'total_rows': total_rows,
            'max_cols': max_cols,
            'has_colspan': has_colspan,
            'has_rowspan': has_rowspan,
            'header_rows': header_rows,
            'complexity': 'high' if (has_colspan and has_rowspan) else 'medium' if (has_colspan or has_rowspan) else 'simple',
        }

    def visualize_grid(self, grid: List[List[Dict]]) -> str:
        """
        可视化表格网格（用于调试）

        Returns:
            表格的文本表示
        """
        lines = []
        for row in grid:
            row_text = []
            for cell in row:
                if cell:
                    # 显示单元格信息
                    marker = '*' if cell.get('is_header') else ''
                    colspan = f"[{cell['colspan']}]" if cell['colspan'] > 1 else ''
                    text = cell['text'][:20]
                    row_text.append(f"{marker}{text}{colspan}")
                else:
                    row_text.append("空")
            lines.append(" | ".join(row_text))
        return "\n".join(lines)
