"""
代理池模块 - 数据模型定义
"""
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import threading


class ProtocolType(Enum):
    """支持的代理协议类型"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
    HTTP_HTTPS = "http/https"


class AnonymityLevel(Enum):
    """代理匿名级别"""
    TRANSPARENT = "transparent"    # 透明代理 - 会暴露真实IP
    ANONYMOUS = "anonymous"        # 普通匿名 - 会暴露使用代理
    HIGH_ANONYMOUS = "high_anonymous"  # 高匿名 - 完全隐藏


class ProxyStatus(Enum):
    """代理状态"""
    untested = "untested"
    valid = "valid"
    invalid = "invalid"
    slow = "slow"


@dataclass
class Proxy:
    """代理对象"""
    ip: str
    port: int
    protocol: ProtocolType = ProtocolType.HTTP
    anonymity: AnonymityLevel = AnonymityLevel.TRANSPARENT
    status: ProxyStatus = ProxyStatus.untested
    response_time: float = 0.0  # 响应时间（秒）
    success_count: int = 0     # 成功次数
    fail_count: int = 0        # 失败次数
    last_checked: Optional[datetime] = None
    last_success: Optional[datetime] = None
    source: str = ""           # 来源网站
    country: str = ""          # 国家
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def proxy_url(self) -> str:
        """获取代理URL"""
        if self.protocol == ProtocolType.SOCKS5:
            return f"socks5://{self.ip}:{self.port}"
        return f"{self.protocol.value}://{self.ip}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol.value,
            "anonymity": self.anonymity.value,
            "status": self.status.value,
            "response_time": self.response_time,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "success_rate": self.success_rate,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "source": self.source,
            "country": self.country,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class ProxyPoolConfig:
    """代理池配置"""
    # 验证设置
    verify_timeout: int = 10          # 验证超时时间（秒）
    verify_concurrency: int = 50      # 验证并发数
    min_response_time: float = 3.0   # 最大响应时间（秒）
    min_success_rate: float = 0.5    # 最低成功率
    
    # 更新设置
    fetch_interval: int = 3600       # 抓取间隔（秒）
    verify_interval: int = 1800      # 验证间隔（秒）
    max_pool_size: int = 1000        # 最大代理池大小
    
    # 存储设置
    db_path: str = "proxies.db"      # 数据库路径
    enable_memory_cache: bool = True # 启用内存缓存
    
    # 验证URL列表
    verify_urls: list = field(default_factory=lambda: [
        "http://httpbin.org/ip",
        "https://httpbin.org/ip",
    ])
    
    # 匿名检测URL
    check_anonymity_url: str = "http://httpbin.org/headers"
