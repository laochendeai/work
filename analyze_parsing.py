import sqlite3
import random
import json
import logging
import sys
import os
from datetime import datetime

# 确保能导入项目模块
sys.path.append(os.getcwd())

from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_parser import CCGPAnnouncementParser
from main import _iter_business_cards

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'data/gp.db'

def get_sample_urls(percentage=0.03, min_samples=10):
    """抽取无电话名片的源URL样本"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 查找无电话的名片
    query = """
    SELECT bc.id, bc.company, bc.contact_name, a.url, a.title
    FROM business_cards bc
    JOIN business_card_mentions bcm ON bc.id = bcm.business_card_id
    JOIN announcements a ON bcm.announcement_id = a.id
    WHERE (bc.phones_json IS NULL OR bc.phones_json = '[]' OR bc.phones_json = '')
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    total = len(rows)
    sample_size = max(int(total * percentage), min_samples)
    sample_size = min(sample_size, total) # 不能超过总数
    
    logger.info(f"无电话名片总数: {total}, 计划采样: {sample_size}")
    
    return random.sample(rows, sample_size) if rows else []

def analyze_parsing():
    samples = get_sample_urls()
    if not samples:
        logger.warning("未找到符合条件的样本")
        return

    fetcher = PlaywrightFetcher()
    parser = CCGPAnnouncementParser()
    
    results = {
        'total': len(samples),
        'fixed': 0,
        'still_empty': 0,
        'errors': 0,
        'details': []
    }

    try:
        fetcher.start()
        
        for i, row in enumerate(samples, 1):
            url = row['url']
            company = row['company']
            name = row['contact_name']
            
            logger.info(f"[{i}/{len(samples)}] 分析: {name} @ {company}")
            logger.info(f"  URL: {url}")
            
            try:
                # 重新抓取
                html = fetcher.get_page(url)
                if not html:
                    logger.error("  获取页面失败")
                    results['errors'] += 1
                    continue
                
                # 重新解析
                parsed = parser.parse(html, url)
                formatted = parser.format_for_storage(parsed)
                
                # 提取联系人
                cards = _iter_business_cards(formatted)
                
                # 寻找匹配当前公司和名字的提取结果
                found_match = False
                extracted_phones = []
                
                for card in cards:
                    # 简单的模糊匹配，因为提取的公司名可能略有不同
                    c_company = card.get('company', '')
                    c_name = card.get('contact_name', '')
                    c_phones = card.get('phones', [])
                    
                    if (c_company in company or company in c_company) and \
                       (c_name in name or name in c_name):
                        found_match = True
                        extracted_phones = c_phones
                        # 详细对比
                        logger.info(f"  重新解析结果: {c_name} | {c_company} | 电话: {c_phones}")
                        
                        if c_phones:
                            logger.info(f"  ==> 成功提取到电话! {c_phones}")
                        else:
                            logger.warning(f"  ==> 依然没有电话。")
                        break
                
                if found_match and extracted_phones:
                    results['fixed'] += 1
                    results['details'].append({'url': url, 'status': 'fixed', 'phones': extracted_phones})
                else:
                    results['still_empty'] += 1
                    results['details'].append({'url': url, 'status': 'empty'})
                    # 这里可以保存 HTML 以便后续深度调试
                    # with open(f"debug_{i}.html", "w", encoding="utf-8") as f:
                    #     f.write(html)
                    
            except Exception as e:
                logger.error(f"  处理异常: {e}")
                results['errors'] += 1

    finally:
        fetcher.stop()
        
    logger.info("="*50)
    logger.info("分析完成")
    logger.info(f"总样本: {results['total']}")
    logger.info(f"成功提取电话: {results['fixed']} ({(results['fixed']/results['total'])*100:.1f}%)")
    logger.info(f"仍无电话: {results['still_empty']}")
    logger.info(f"错误: {results['errors']}")
    logger.info("="*50)

if __name__ == "__main__":
    analyze_parsing()
