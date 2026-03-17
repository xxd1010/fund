"""
代理池存储模块 - 使用SQLite进行持久化存储
"""
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

from .models import Proxy, ProxyStatus, ProtocolType, AnonymityLevel, ProxyPoolConfig


class ProxyStorage:
    """代理存储管理类"""
    
    def __init__(self, config: ProxyPoolConfig):
        self.config = config
        self.db_path = config.db_path
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    protocol TEXT NOT NULL,
                    anonymity TEXT DEFAULT 'transparent',
                    status TEXT DEFAULT 'untested',
                    response_time REAL DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    last_checked TEXT,
                    last_success TEXT,
                    source TEXT,
                    country TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(ip, port, protocol)
                )
            """)
            
            # 创建索引提升查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_protocol ON proxies(protocol)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON proxies(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_anonymity ON proxies(anonymity)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_response_time ON proxies(response_time)
            """)
            
            # 创建抓取源记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fetch_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    last_fetch TEXT,
                    fetch_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            
            # 创建统计信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_proxies INTEGER DEFAULT 0,
                    valid_proxies INTEGER DEFAULT 0,
                    fetch_count INTEGER DEFAULT 0,
                    verify_count INTEGER DEFAULT 0,
                    UNIQUE(date)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（线程安全）"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def add_proxy(self, proxy: Proxy) -> bool:
        """添加代理到数据库"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR IGNORE INTO proxies 
                        (ip, port, protocol, anonymity, status, response_time,
                         success_count, fail_count, last_checked, last_success,
                         source, country, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        proxy.ip, proxy.port, proxy.protocol.value,
                        proxy.anonymity.value, proxy.status.value,
                        proxy.response_time, proxy.success_count,
                        proxy.fail_count,
                        proxy.last_checked.isoformat() if proxy.last_checked else None,
                        proxy.last_success.isoformat() if proxy.last_success else None,
                        proxy.source, proxy.country,
                        proxy.created_at.isoformat() if proxy.created_at else datetime.now().isoformat()
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                return False
    
    def add_proxies_batch(self, proxies: List[Proxy]) -> int:
        """批量添加代理"""
        count = 0
        with self._lock:
            for proxy in proxies:
                if self.add_proxy(proxy):
                    count += 1
        return count
    
    def update_proxy(self, proxy: Proxy) -> bool:
        """更新代理信息"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE proxies SET
                            protocol = ?,
                            anonymity = ?,
                            status = ?,
                            response_time = ?,
                            success_count = ?,
                            fail_count = ?,
                            last_checked = ?,
                            last_success = ?
                        WHERE ip = ? AND port = ?
                    """, (
                        proxy.protocol.value, proxy.anonymity.value,
                        proxy.status.value, proxy.response_time,
                        proxy.success_count, proxy.fail_count,
                        proxy.last_checked.isoformat() if proxy.last_checked else None,
                        proxy.last_success.isoformat() if proxy.last_success else None,
                        proxy.ip, proxy.port
                    ))
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception:
                return False
    
    def delete_proxy(self, ip: str, port: int) -> bool:
        """删除代理"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM proxies WHERE ip = ? AND port = ?",
                        (ip, port)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception:
                return False
    
    def get_proxy(self, ip: str, port: int) -> Optional[Proxy]:
        """获取单个代理"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM proxies WHERE ip = ? AND port = ?",
                    (ip, port)
                )
                row = cursor.fetchone()
                return self._row_to_proxy(row) if row else None
    
    def get_all_proxies(self, limit: Optional[int] = None) -> List[Proxy]:
        """获取所有代理"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM proxies"
                if limit:
                    query += f" LIMIT {limit}"
                cursor.execute(query)
                return [self._row_to_proxy(row) for row in cursor.fetchall()]
    
    def get_proxies_by_protocol(self, protocol: ProtocolType) -> List[Proxy]:
        """按协议类型获取代理"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM proxies WHERE protocol = ?",
                    (protocol.value,)
                )
                return [self._row_to_proxy(row) for row in cursor.fetchall()]
    
    def get_valid_proxies(
        self,
        protocol: Optional[ProtocolType] = None,
        anonymity: Optional[AnonymityLevel] = None,
        max_response_time: Optional[float] = None,
        limit: int = 100
    ) -> List[Proxy]:
        """获取有效代理（支持多条件过滤）"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM proxies WHERE status = 'valid'"
                params = []
                
                if protocol:
                    query += " AND protocol = ?"
                    params.append(protocol.value)
                
                if anonymity:
                    query += " AND anonymity = ?"
                    params.append(anonymity.value)
                
                if max_response_time:
                    query += " AND response_time <= ?"
                    params.append(max_response_time)
                
                query += " ORDER BY response_time ASC, success_count DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                return [self._row_to_proxy(row) for row in cursor.fetchall()]
    
    def get_random_proxy(
        self,
        protocol: Optional[ProtocolType] = None,
        anonymity: Optional[AnonymityLevel] = None,
        max_response_time: Optional[float] = None
    ) -> Optional[Proxy]:
        """随机获取一个有效代理"""
        proxies = self.get_valid_proxies(protocol, anonymity, max_response_time, limit=50)
        if proxies:
            import random
            return random.choice(proxies)
        return None
    
    def delete_invalid_proxies(self, days: int = 7) -> int:
        """删除长期无效的代理"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM proxies 
                    WHERE status = 'invalid' 
                    AND last_checked < datetime('now', '-' || ? || ' days')
                """, (days,))
                conn.commit()
                return cursor.rowcount
    
    def delete_slow_proxies(self, max_response_time: float) -> int:
        """删除响应慢的代理"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM proxies 
                    WHERE response_time > ?
                """, (max_response_time,))
                conn.commit()
                return cursor.rowcount
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 总代理数
                cursor.execute("SELECT COUNT(*) as total FROM proxies")
                total = cursor.fetchone()["total"]
                
                # 有效代理数
                cursor.execute("SELECT COUNT(*) as valid FROM proxies WHERE status = 'valid'")
                valid = cursor.fetchone()["valid"]
                
                # 按协议统计
                cursor.execute("""
                    SELECT protocol, COUNT(*) as count 
                    FROM proxies WHERE status = 'valid'
                    GROUP BY protocol
                """)
                by_protocol = {row["protocol"]: row["count"] for row in cursor.fetchall()}
                
                # 按匿名级别统计
                cursor.execute("""
                    SELECT anonymity, COUNT(*) as count 
                    FROM proxies WHERE status = 'valid'
                    GROUP BY anonymity
                """)
                by_anonymity = {row["anonymity"]: row["count"] for row in cursor.fetchall()}
                
                # 平均响应时间
                cursor.execute("""
                    SELECT AVG(response_time) as avg_time 
                    FROM proxies WHERE status = 'valid'
                """)
                avg_response_time = cursor.fetchone()["avg_time"] or 0
                
                return {
                    "total": total,
                    "valid": valid,
                    "invalid": total - valid,
                    "by_protocol": by_protocol,
                    "by_anonymity": by_anonymity,
                    "avg_response_time": round(avg_response_time, 3)
                }
    
    def clear_all(self) -> bool:
        """清空所有代理"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM proxies")
                    conn.commit()
                    return True
            except Exception:
                return False
    
    def _row_to_proxy(self, row) -> Proxy:
        """将数据库行转换为Proxy对象"""
        return Proxy(
            ip=row["ip"],
            port=row["port"],
            protocol=ProtocolType(row["protocol"]),
            anonymity=AnonymityLevel(row["anonymity"]),
            status=ProxyStatus(row["status"]),
            response_time=row["response_time"],
            success_count=row["success_count"],
            fail_count=row["fail_count"],
            last_checked=datetime.fromisoformat(row["last_checked"]) if row["last_checked"] else None,
            last_success=datetime.fromisoformat(row["last_success"]) if row["last_success"] else None,
            source=row["source"],
            country=row["country"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
        )
