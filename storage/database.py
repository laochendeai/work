"""
数据库操作模块
使用SQLite存储公告和联系人数据
"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import DB_PATH

logger = logging.getLogger(__name__)


class Database:
    """数据库操作类"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径，默认使用配置中的路径
        """
        self.db_path = db_path or DB_PATH
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        # 确保目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self.connect()

        # 创建公告表
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content TEXT,
                publish_date TEXT,
                source TEXT,
                scraped_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建联系人表
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                announcement_id INTEGER,
                company TEXT,
                contact_name TEXT,
                phone TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (announcement_id) REFERENCES announcements (id)
            )
        ''')

        # 聚合名片表（按 company + contact_name 合并联系方式）
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS business_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                phones_json TEXT NOT NULL DEFAULT '[]',
                emails_json TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company, contact_name)
            )
        ''')

        # 名片与公告的关联（用于统计“出现于多少项目/公告”）
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS business_card_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_card_id INTEGER NOT NULL,
                announcement_id INTEGER NOT NULL,
                role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(business_card_id, announcement_id, role),
                FOREIGN KEY (business_card_id) REFERENCES business_cards (id),
                FOREIGN KEY (announcement_id) REFERENCES announcements (id)
            )
        ''')

        # 创建索引
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_announcements_url
            ON announcements (url)
        ''')

        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_announcements_source
            ON announcements (source)
        ''')

        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_contacts_company
            ON contacts (company)
        ''')

        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_business_cards_company
            ON business_cards (company)
        ''')

        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_business_cards_company_contact
            ON business_cards (company, contact_name)
        ''')

        self.conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    def connect(self):
        """连接数据库"""
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_announcement_id_by_url(self, url: str) -> Optional[int]:
        """按URL查询公告ID（用于跨多次搜索的去重）"""
        if not url:
            return None
        try:
            self.connect()
            row = self.conn.execute(
                'SELECT id FROM announcements WHERE url = ? LIMIT 1',
                (url,),
            ).fetchone()
            return int(row[0]) if row else None
        except Exception as e:
            logger.error(f"按URL查询公告失败: {e}")
            return None

    def insert_announcement(self, announcement: Dict) -> Optional[int]:
        """
        插入公告

        Args:
            announcement: 公告数据

        Returns:
            插入的记录ID，失败返回None
        """
        try:
            self.connect()

            cursor = self.conn.execute('''
                INSERT OR IGNORE INTO announcements
                (title, url, content, publish_date, source, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                announcement.get('title'),
                announcement.get('url'),
                announcement.get('content'),
                announcement.get('publish_date'),
                announcement.get('source'),
                announcement.get('scraped_at'),
            ))

            self.conn.commit()

            if cursor.rowcount > 0:
                announcement_id = cursor.lastrowid
                logger.info(f"插入公告: {announcement.get('title', '')[:30]}...")
                return announcement_id
            else:
                logger.debug(f"公告已存在: {announcement.get('url')}")
                return None

        except Exception as e:
            logger.error(f"插入公告失败: {e}")
            return None

    def upsert_business_card(
        self,
        company: str,
        contact_name: str,
        phones: Optional[List[str]] = None,
        emails: Optional[List[str]] = None,
    ) -> Optional[int]:
        """
        写入/更新名片（合并 phones/emails）

        名片唯一键：company + contact_name
        """
        company = (company or "").strip()
        contact_name = (contact_name or "").strip()
        if not company or not contact_name:
            return None

        phones_set = {p.strip() for p in (phones or []) if p and p.strip()}
        emails_set = {e.strip().lower() for e in (emails or []) if e and e.strip()}

        try:
            self.connect()

            row = self.conn.execute(
                '''
                SELECT id, phones_json, emails_json
                FROM business_cards
                WHERE company = ? AND contact_name = ?
                LIMIT 1
                ''',
                (company, contact_name),
            ).fetchone()

            if not row:
                cursor = self.conn.execute(
                    '''
                    INSERT INTO business_cards (company, contact_name, phones_json, emails_json)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        company,
                        contact_name,
                        json.dumps(sorted(phones_set), ensure_ascii=False),
                        json.dumps(sorted(emails_set), ensure_ascii=False),
                    ),
                )
                self.conn.commit()
                return int(cursor.lastrowid) if cursor.lastrowid else None

            card_id = int(row["id"])
            existing_phones = set(json.loads(row["phones_json"] or "[]"))
            existing_emails = set(json.loads(row["emails_json"] or "[]"))

            merged_phones = sorted(existing_phones | phones_set)
            merged_emails = sorted(existing_emails | emails_set)

            self.conn.execute(
                '''
                UPDATE business_cards
                SET phones_json = ?, emails_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''',
                (
                    json.dumps(merged_phones, ensure_ascii=False),
                    json.dumps(merged_emails, ensure_ascii=False),
                    card_id,
                ),
            )
            self.conn.commit()
            return card_id

        except Exception as e:
            logger.error(f"写入名片失败: {e}")
            return None

    def add_business_card_mention(self, business_card_id: int, announcement_id: int, role: str = "") -> bool:
        """记录名片出现在某个公告中（用于统计）"""
        if not business_card_id or not announcement_id:
            return False
        role = (role or "").strip()

        try:
            self.connect()
            self.conn.execute(
                '''
                INSERT OR IGNORE INTO business_card_mentions
                (business_card_id, announcement_id, role)
                VALUES (?, ?, ?)
                ''',
                (business_card_id, announcement_id, role),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"写入名片关联失败: {e}")
            return False

    def get_business_cards(self, company: str, like: bool = False, limit: int = 200) -> List[Dict]:
        """查询名片（支持精确/模糊匹配公司名）"""
        company = (company or "").strip()
        if not company:
            return []

        try:
            self.connect()

            if like:
                cursor = self.conn.execute(
                    '''
                    SELECT
                        bc.id,
                        bc.company,
                        bc.contact_name,
                        bc.phones_json,
                        bc.emails_json,
                        COUNT(DISTINCT bcm.announcement_id) AS projects_count,
                        bc.updated_at
                    FROM business_cards bc
                    LEFT JOIN business_card_mentions bcm
                        ON bcm.business_card_id = bc.id
                    WHERE bc.company LIKE ?
                    GROUP BY bc.id
                    ORDER BY projects_count DESC, bc.updated_at DESC
                    LIMIT ?
                    ''',
                    (f"%{company}%", limit),
                )
            else:
                cursor = self.conn.execute(
                    '''
                    SELECT
                        bc.id,
                        bc.company,
                        bc.contact_name,
                        bc.phones_json,
                        bc.emails_json,
                        COUNT(DISTINCT bcm.announcement_id) AS projects_count,
                        bc.updated_at
                    FROM business_cards bc
                    LEFT JOIN business_card_mentions bcm
                        ON bcm.business_card_id = bc.id
                    WHERE bc.company = ?
                    GROUP BY bc.id
                    ORDER BY projects_count DESC, bc.updated_at DESC
                    LIMIT ?
                    ''',
                    (company, limit),
                )

            rows = [dict(r) for r in cursor.fetchall()]
            for r in rows:
                try:
                    r["phones"] = json.loads(r.get("phones_json") or "[]")
                except Exception:
                    r["phones"] = []
                try:
                    r["emails"] = json.loads(r.get("emails_json") or "[]")
                except Exception:
                    r["emails"] = []
            return rows

        except Exception as e:
            logger.error(f"查询名片失败: {e}")
            return []

    def insert_contacts(self, announcement_id: int, contacts: Dict) -> int:
        """
        插入联系人

        Args:
            announcement_id: 公告ID
            contacts: 联系人数据

        Returns:
            插入的联系人数量
        """
        count = 0

        try:
            self.connect()

            # 提取所有联系人组合
            companies = [contacts.get('company')] if contacts.get('company') else ['']
            contact_names = contacts.get('contacts') or ['']
            phones = contacts.get('phones') or ['']
            emails = contacts.get('emails') or ['']

            # 如果没有公司名称，使用所有组合
            if not companies[0]:
                companies = ['']

            # 生成组合并插入
            for company in companies:
                for name in contact_names:
                    for phone in phones:
                        for email in emails:
                            # 至少要有一种联系方式
                            if not phone and not email:
                                continue

                            try:
                                self.conn.execute('''
                                    INSERT INTO contacts
                                    (announcement_id, company, contact_name, phone, email)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (
                                    announcement_id,
                                    company,
                                    name,
                                    phone,
                                    email,
                                ))
                                count += 1
                            except sqlite3.IntegrityError:
                                pass  # 忽略重复

            self.conn.commit()
            logger.info(f"插入 {count} 个联系人")

        except Exception as e:
            logger.error(f"插入联系人失败: {e}")

        return count

    def get_announcements(self, source: str = None, limit: int = 100) -> List[Dict]:
        """
        获取公告列表

        Args:
            source: 数据源名称，None表示所有源
            limit: 返回数量限制

        Returns:
            公告列表
        """
        try:
            self.connect()

            if source:
                cursor = self.conn.execute('''
                    SELECT * FROM announcements
                    WHERE source = ?
                    ORDER BY id DESC
                    LIMIT ?
                ''', (source, limit))
            else:
                cursor = self.conn.execute('''
                    SELECT * FROM announcements
                    ORDER BY id DESC
                    LIMIT ?
                ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"获取公告失败: {e}")
            return []

    def get_contacts(self, company: str = None, limit: int = 100) -> List[Dict]:
        """
        获取联系人列表

        Args:
            company: 公司名称，None表示所有公司
            limit: 返回数量限制

        Returns:
            联系人列表
        """
        try:
            self.connect()

            if company:
                cursor = self.conn.execute('''
                    SELECT * FROM contacts
                    WHERE company = ?
                    ORDER BY id DESC
                    LIMIT ?
                ''', (company, limit))
            else:
                cursor = self.conn.execute('''
                    SELECT * FROM contacts
                    ORDER BY id DESC
                    LIMIT ?
                ''', (limit,))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"获取联系人失败: {e}")
            return []

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        try:
            self.connect()

            # 公告总数
            total_announcements = self.conn.execute(
                'SELECT COUNT(*) FROM announcements'
            ).fetchone()[0]

            # 联系人总数
            total_contacts = self.conn.execute(
                'SELECT COUNT(*) FROM contacts'
            ).fetchone()[0]

            # 按源统计
            by_source = self.conn.execute('''
                SELECT source, COUNT(*) as count
                FROM announcements
                GROUP BY source
            ''').fetchall()

            # 按公司统计
            by_company = self.conn.execute('''
                SELECT company, COUNT(*) as count
                FROM contacts
                WHERE company IS NOT NULL AND company != ''
                GROUP BY company
                ORDER BY count DESC
                LIMIT 20
            ''').fetchall()

            return {
                'total_announcements': total_announcements,
                'total_contacts': total_contacts,
                'by_source': dict(by_source),
                'top_companies': dict(by_company),
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
