"""
代理池模块 - 功能完善的代理IP管理解决方案

功能特性:
- 多源代理IP自动抓取
- 多维度代理验证（速度、匿名级别、协议支持）
- 高效的存储结构（SQLite）
- 动态更新机制（定时抓取和验证）
- 简洁易用的API接口
- 完善的日志记录
- 线程安全设计

快速开始:
    from proxy_pool import ProxyPoolAPI, get_proxy
    
    # 获取一个代理
    proxy = get_proxy('http')
    print(f"代理: {proxy.ip}:{proxy.port}")
    
    # 使用API
    api = ProxyPoolAPI()
    proxy = api.get('https')
    proxies = api.get_multi('http', count=5)
"""
from .models import (
    Proxy,
    ProtocolType,
    AnonymityLevel,
    ProxyStatus,
    ProxyPoolConfig
)
from .storage import ProxyStorage
from .fetcher import ProxyFetcherManager, SyncProxyFetcher
from .verifier import ProxyVerifier, SyncProxyVerifier
from .pool import ProxyPool, ProxyPoolManager, get_default_pool, create_pool
from .api import ProxyPoolAPI, ProxySession, create_proxy_api, get_proxy, get_best_proxy
from .logger import setup_logger, get_logger, get_pool_logger


__version__ = "1.0.0"

__all__ = [
    # 数据模型
    "Proxy",
    "ProtocolType",
    "AnonymityLevel",
    "ProxyStatus",
    "ProxyPoolConfig",
    # 存储
    "ProxyStorage",
    # 抓取器
    "ProxyFetcherManager",
    "SyncProxyFetcher",
    # 验证器
    "ProxyVerifier",
    "SyncProxyVerifier",
    # 核心类
    "ProxyPool",
    "ProxyPoolManager",
    "ProxyPoolAPI",
    "ProxySession",
    # 工厂函数
    "create_pool",
    "create_proxy_api",
    # 便捷函数
    "get_proxy",
    "get_best_proxy",
    "get_default_pool",
    # 日志
    "setup_logger",
    "get_logger",
    "get_pool_logger",
]
