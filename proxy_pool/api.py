"""
代理池API模块 - 提供简洁易用的接口
"""
import logging
from typing import List, Optional, Dict, Union
from datetime import datetime

from .models import Proxy, ProtocolType, AnonymityLevel, ProxyPoolConfig, ProxyStatus
from .pool import ProxyPool, get_default_pool, create_pool


class ProxyPoolAPI:
    """代理池API - 简洁易用的接口"""
    
    def __init__(self, pool: Optional[ProxyPool] = None):
        self.pool = pool or get_default_pool()
        self.logger = logging.getLogger(__name__)
    
    # ==================== 快速获取代理 ====================
    
    def get(self, protocol: Optional[str] = None) -> Optional[Proxy]:
        """获取一个代理（简单接口）
        
        Args:
            protocol: 协议类型, 支持 'http', 'https', 'socks5'
            
        Returns:
            可用代理对象, 无可用代理返回 None
        """
        protocol_type = None
        if protocol:
            try:
                protocol_type = ProtocolType(protocol.lower())
            except ValueError:
                self.logger.warning(f"未知协议类型: {protocol}")
                return None
        
        return self.pool.get_proxy(protocol=protocol_type)
    
    def get_best(self, protocol: Optional[str] = None) -> Optional[Proxy]:
        """获取最优代理（响应最快）"""
        protocol_type = None
        if protocol:
            try:
                protocol_type = ProtocolType(protocol.lower())
            except ValueError:
                return None
        
        return self.pool.get_best_proxy(protocol=protocol_type)
    
    def get_multi(self, protocol: Optional[str] = None, count: int = 10) -> List[Proxy]:
        """获取多个代理
        
        Args:
            protocol: 协议类型
            count: 获取数量
            
        Returns:
            代理列表
        """
        protocol_type = None
        if protocol:
            try:
                protocol_type = ProtocolType(protocol.lower())
            except ValueError:
                return []
        
        return self.pool.get_proxies(protocol=protocol_type, limit=count)
    
    # ==================== 高级筛选 ====================
    
    def get_by_anonymity(
        self,
        anonymity: str,
        protocol: Optional[str] = None,
        max_response_time: Optional[float] = None
    ) -> Optional[Proxy]:
        """按匿名级别获取代理
        
        Args:
            anonymity: 匿名级别, 支持 'transparent', 'anonymous', 'high_anonymous'
            protocol: 协议类型
            max_response_time: 最大响应时间（秒）
        """
        try:
            anon_level = AnonymityLevel(anonymity.lower())
        except ValueError:
            self.logger.warning(f"未知匿名级别: {anonymity}")
            return None
        
        protocol_type = None
        if protocol:
            try:
                protocol_type = ProtocolType(protocol.lower())
            except ValueError:
                return None
        
        return self.pool.get_proxy(
            protocol=protocol_type,
            anonymity=anon_level,
            max_response_time=max_response_time
        )
    
    def get_by_response_time(
        self,
        max_time: float,
        protocol: Optional[str] = None
    ) -> List[Proxy]:
        """按响应时间筛选代理
        
        Args:
            max_time: 最大响应时间（秒）
            protocol: 协议类型
        """
        protocol_type = None
        if protocol:
            try:
                protocol_type = ProtocolType(protocol.lower())
            except ValueError:
                return []
        
        return self.pool.get_proxies(
            protocol=protocol_type,
            max_response_time=max_time,
            limit=50
        )
    
    # ==================== 代理管理 ====================
    
    def add(self, ip: str, port: int, protocol: str = "http") -> bool:
        """手动添加代理
        
        Args:
            ip: 代理IP
            port: 代理端口
            protocol: 协议类型
            
        Returns:
            是否添加成功
        """
        try:
            protocol_type = ProtocolType(protocol.lower())
        except ValueError:
            protocol_type = ProtocolType.HTTP
        
        proxy = Proxy(
            ip=ip,
            port=port,
            protocol=protocol_type,
            source="manual"
        )
        
        return self.pool.add_proxy(proxy)
    
    def remove(self, ip: str, port: int) -> bool:
        """删除代理"""
        return self.pool.remove_proxy(ip, port)
    
    def list_all(self, limit: int = 100) -> List[Proxy]:
        """列出所有代理"""
        return self.pool.get_all_proxies(limit)
    
    def list_valid(self, limit: int = 100) -> List[Proxy]:
        """列出有效代理"""
        return self.pool.get_valid_proxies(limit)
    
    # ==================== 抓取与验证 ====================
    
    async def fetch(self) -> int:
        """抓取新代理
        
        Returns:
            新增代理数量
        """
        return await self.pool.fetch_proxies()
    
    async def verify(self, max_proxies: int = 100) -> Dict:
        """验证代理
        
        Args:
            max_proxies: 最大验证数量
            
        Returns:
            验证统计信息
        """
        stats = await self.pool.verify_proxies(max_proxies)
        return stats.to_dict()
    
    def verify_sync(self, max_proxies: int = 100) -> Dict:
        """同步验证代理"""
        stats = self.pool.verify_proxies_sync(max_proxies)
        return stats.to_dict()
    
    # ==================== 定时任务 ====================
    
    def start(self, fetch_interval: int = 3600, verify_interval: int = 1800):
        """启动自动更新
        
        Args:
            fetch_interval: 抓取间隔（秒）
            verify_interval: 验证间隔（秒）
        """
        self.pool.start_scheduler(fetch_interval, verify_interval)
    
    def stop(self):
        """停止自动更新"""
        self.pool.stop_scheduler()
    
    # ==================== 统计信息 ====================
    
    def stats(self) -> Dict:
        """获取统计信息"""
        return self.pool.get_statistics()
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.pool.get_statistics().get("scheduler_running", False)
    
    # ==================== 清理维护 ====================
    
    def cleanup(self) -> Dict:
        """清理无效代理"""
        return self.pool.cleanup()
    
    def clear(self) -> bool:
        """清空代理池"""
        return self.pool.clear()
    
    # ==================== 便捷方法 ====================
    
    def __repr__(self):
        stats = self.stats()
        return (
            f"ProxyPoolAPI(total={stats.get('total', 0)}, "
            f"valid={stats.get('valid', 0)}, "
            f"running={self.is_running()})"
        )


class ProxySession:
    """代理会话 - 简化HTTP请求使用代理"""
    
    def __init__(self, api: Optional[ProxyPoolAPI] = None):
        self.api = api or ProxyPoolAPI()
        self._current_proxy: Optional[Proxy] = None
    
    def get_proxy(self, protocol: Optional[str] = None) -> Optional[Proxy]:
        """获取代理"""
        self._current_proxy = self.api.get(protocol)
        return self._current_proxy
    
    def rotate(self, protocol: Optional[str] = None) -> Optional[Proxy]:
        """轮换代理"""
        return self.get_proxy(protocol)
    
    @property
    def proxy_url(self) -> Optional[str]:
        """获取当前代理URL"""
        return self._current_proxy.proxy_url if self._current_proxy else None
    
    def get_session_config(self) -> Optional[Dict]:
        """获取用于requests库的session配置"""
        if not self._current_proxy:
            return None
        
        return {
            "http": self._current_proxy.proxy_url,
            "https": self._current_proxy.proxy_url
        }


def create_proxy_api(config: Optional[ProxyPoolConfig] = None) -> ProxyPoolAPI:
    """创建代理池API"""
    pool = create_pool(config)
    return ProxyPoolAPI(pool)


# 便捷函数
def get_proxy(protocol: Optional[str] = None) -> Optional[Proxy]:
    """快速获取一个代理"""
    return ProxyPoolAPI().get(protocol)


def get_best_proxy(protocol: Optional[str] = None) -> Optional[Proxy]:
    """快速获取最优代理"""
    return ProxyPoolAPI().get_best(protocol)
