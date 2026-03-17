"""
代理池管理器 - 核心模块，负责协调所有组件
"""
import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import List, Optional, Dict, Callable
from collections import defaultdict

from .models import Proxy, ProxyStatus, ProtocolType, AnonymityLevel, ProxyPoolConfig
from .storage import ProxyStorage
from .fetcher import ProxyFetcherManager, SyncProxyFetcher
from .verifier import ProxyVerifier, SyncProxyVerifier, VerifierStats


class ProxyPool:
    """代理池主类 - 提供完整的代理管理功能"""
    
    def __init__(self, config: Optional[ProxyPoolConfig] = None):
        self.config = config or ProxyPoolConfig()
        self.storage = ProxyStorage(self.config)
        self.fetcher_manager = ProxyFetcherManager(self.config)
        self.sync_fetcher = SyncProxyFetcher(self.config)
        
        # 内存缓存
        self._memory_cache: Dict[str, List[Proxy]] = defaultdict(list)
        self._cache_lock = threading.RLock()
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 300  # 缓存5分钟
        
        # 定时任务
        self._running = False
        self._fetch_thread: Optional[threading.Thread] = None
        self._verify_thread: Optional[threading.Thread] = None
        self._scheduler_lock = threading.Lock()
        
        # 回调函数
        self._on_fetch_callbacks: List[Callable] = []
        self._on_verify_callbacks: List[Callable] = []
        
        # 日志
        self.logger = logging.getLogger(__name__)
        
        # 统计信息
        self.stats = {
            "total_fetches": 0,
            "total_verifies": 0,
            "last_fetch": None,
            "last_verify": None
        }
    
    # ==================== 核心功能 ====================
    
    async def fetch_proxies(self) -> int:
        """抓取新代理"""
        self.logger.info("开始抓取代理...")
        self.stats["total_fetches"] += 1
        
        try:
            # 异步抓取
            proxies = await self.fetcher_manager.fetch_all()
            
            if not proxies:
                # 备用同步抓取
                self.logger.info("异步抓取失败，使用同步抓取...")
                proxies = self.sync_fetcher.fetch_all()
            
            if proxies:
                # 添加到存储
                count = self.storage.add_proxies_batch(proxies)
                self.logger.info(f"抓取完成，新增 {count} 个代理")
                self.stats["last_fetch"] = datetime.now()
                
                # 触发回调
                for callback in self._on_fetch_callbacks:
                    try:
                        callback(proxies)
                    except Exception as e:
                        self.logger.error(f"执行抓取回调失败: {e}")
                
                # 清空缓存
                self._clear_cache()
                
                return count
            
            return 0
            
        except Exception as e:
            self.logger.error(f"抓取代理失败: {e}")
            return 0
    
    async def verify_proxies(self, max_proxies: int = 100) -> VerifierStats:
        """验证所有代理"""
        self.logger.info("开始验证代理...")
        self.stats["total_verifies"] += 1
        
        stats = VerifierStats()
        stats.start_time = datetime.now()
        
        try:
            # 获取待验证的代理
            proxies = self.storage.get_all_proxies(limit=max_proxies * 2)
            if not proxies:
                self.logger.warning("没有待验证的代理")
                return stats
            
            self.logger.info(f"待验证代理数量: {len(proxies)}")
            
            # 并发验证
            async with ProxyVerifier(self.config) as verifier:
                # 分批验证
                for i in range(0, len(proxies), self.config.verify_concurrency):
                    batch = proxies[i:i + self.config.verify_concurrency]
                    results = await verifier.verify_batch(batch)
                    
                    # 更新存储
                    for proxy in results:
                        self.storage.update_proxy(proxy)
                        stats.add_result(proxy)
                        
                        # 触发回调
                        for callback in self._on_verify_callbacks:
                            try:
                                callback(proxy)
                            except Exception:
                                pass
            
            stats.end_time = datetime.now()
            
            self.logger.info(
                f"验证完成: 有效 {stats.valid}, "
                f"无效 {stats.invalid}, 慢 {stats.slow}"
            )
            self.stats["last_verify"] = datetime.now()
            
            # 清空缓存
            self._clear_cache()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"验证代理失败: {e}")
            stats.end_time = datetime.now()
            return stats
    
    def verify_proxies_sync(self, max_proxies: int = 100) -> VerifierStats:
        """同步验证代理（用于非异步环境）"""
        self.logger.info("开始同步验证代理...")
        
        stats = VerifierStats()
        stats.start_time = datetime.now()
        
        try:
            proxies = self.storage.get_all_proxies(limit=max_proxies * 2)
            if not proxies:
                return stats
            
            verifier = SyncProxyVerifier(self.config)
            
            for i in range(0, len(proxies), 50):
                batch = proxies[i:i + 50]
                results = verifier.verify_batch(batch, max_workers=10)
                
                for proxy in results:
                    self.storage.update_proxy(proxy)
                    stats.add_result(proxy)
            
            stats.end_time = datetime.now()
            self.logger.info(f"同步验证完成: 有效 {stats.valid}")
            self.stats["last_verify"] = datetime.now()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"同步验证失败: {e}")
            stats.end_time = datetime.now()
            return stats
    
    # ==================== 获取代理 ====================
    
    def get_proxy(
        self,
        protocol: Optional[ProtocolType] = None,
        anonymity: Optional[AnonymityLevel] = None,
        max_response_time: Optional[float] = None
    ) -> Optional[Proxy]:
        """获取一个可用代理"""
        # 优先从内存缓存获取
        if self.config.enable_memory_cache:
            cache_key = self._build_cache_key(protocol, anonymity, max_response_time)
            cached = self._get_from_cache(cache_key)
            if cached:
                import random
                return random.choice(cached)
        
        # 从存储获取
        proxy = self.storage.get_random_proxy(protocol, anonymity, max_response_time)
        
        # 更新内存缓存
        if proxy and self.config.enable_memory_cache:
            self._add_to_cache(cache_key, proxy)
        
        return proxy
    
    def get_proxies(
        self,
        protocol: Optional[ProtocolType] = None,
        anonymity: Optional[AnonymityLevel] = None,
        max_response_time: Optional[float] = None,
        limit: int = 10
    ) -> List[Proxy]:
        """获取多个可用代理"""
        return self.storage.get_valid_proxies(
            protocol=protocol,
            anonymity=anonymity,
            max_response_time=max_response_time,
            limit=limit
        )
    
    def get_best_proxy(
        self,
        protocol: Optional[ProtocolType] = None,
        anonymity: Optional[AnonymityLevel] = None
    ) -> Optional[Proxy]:
        """获取最优代理（响应最快）"""
        proxies = self.get_proxies(
            protocol=protocol,
            anonymity=anonymity,
            max_response_time=self.config.min_response_time,
            limit=10
        )
        
        if proxies:
            # 按响应时间排序
            proxies.sort(key=lambda p: p.response_time)
            return proxies[0]
        
        return None
    
    # ==================== 定时任务 ====================
    
    def start_scheduler(self, fetch_interval: Optional[int] = None, 
                       verify_interval: Optional[int] = None):
        """启动定时任务"""
        if self._running:
            self.logger.warning("调度器已在运行")
            return
        
        fetch_interval = fetch_interval or self.config.fetch_interval
        verify_interval = verify_interval or self.config.verify_interval
        
        self._running = True
        
        # 启动抓取线程
        self._fetch_thread = threading.Thread(
            target=self._fetch_loop,
            args=(fetch_interval,),
            daemon=True
        )
        self._fetch_thread.start()
        
        # 启动验证线程
        self._verify_thread = threading.Thread(
            target=self._verify_loop,
            args=(verify_interval,),
            daemon=True
        )
        self._verify_thread.start()
        
        self.logger.info(f"定时任务已启动: 抓取间隔 {fetch_interval}s, 验证间隔 {verify_interval}s")
    
    def stop_scheduler(self):
        """停止定时任务"""
        self._running = False
        
        if self._fetch_thread:
            self._fetch_thread.join(timeout=5)
        
        if self._verify_thread:
            self._verify_thread.join(timeout=5)
        
        self.logger.info("定时任务已停止")
    
    def _fetch_loop(self, interval: int):
        """抓取循环"""
        while self._running:
            try:
                asyncio.run(self.fetch_proxies())
            except Exception as e:
                self.logger.error(f"定时抓取失败: {e}")
            
            time.sleep(interval)
    
    def _verify_loop(self, interval: int):
        """验证循环"""
        while self._running:
            try:
                asyncio.run(self.verify_proxies())
            except Exception as e:
                self.logger.error(f"定时验证失败: {e}")
            
            time.sleep(interval)
    
    # ==================== 维护功能 ====================
    
    def cleanup(self, keep_valid: bool = True) -> Dict[str, int]:
        """清理代理池"""
        result = {}
        
        # 删除无效代理
        invalid_count = self.storage.delete_invalid_proxies(days=7)
        result["deleted_invalid"] = invalid_count
        
        # 删除慢代理
        slow_count = self.storage.delete_slow_proxies(self.config.min_response_time)
        result["deleted_slow"] = slow_count
        
        self.logger.info(f"清理完成: 删除无效代理 {invalid_count}, 删除慢代理 {slow_count}")
        
        # 清空缓存
        self._clear_cache()
        
        return result
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        storage_stats = self.storage.get_statistics()
        
        return {
            **storage_stats,
            "fetch_count": self.stats["total_fetches"],
            "verify_count": self.stats["total_verifies"],
            "last_fetch": self.stats["last_fetch"].isoformat() if self.stats["last_fetch"] else None,
            "last_verify": self.stats["last_verify"].isoformat() if self.stats["last_verify"] else None,
            "cache_enabled": self.config.enable_memory_cache,
            "scheduler_running": self._running
        }
    
    # ==================== 回调管理 ====================
    
    def on_fetch(self, callback: Callable[[List[Proxy]], None]):
        """注册抓取回调"""
        self._on_fetch_callbacks.append(callback)
    
    def on_verify(self, callback: Callable[[Proxy], None]):
        """注册验证回调"""
        self._on_verify_callbacks.append(callback)
    
    # ==================== 缓存管理 ====================
    
    def _build_cache_key(self, protocol: Optional[ProtocolType], 
                        anonymity: Optional[AnonymityLevel],
                        max_response_time: Optional[float]) -> str:
        """构建缓存键"""
        parts = [
            protocol.value if protocol else "any",
            anonymity.value if anonymity else "any",
            str(max_response_time) if max_response_time else "any"
        ]
        return ":".join(parts)
    
    def _get_from_cache(self, key: str) -> Optional[List[Proxy]]:
        """从缓存获取"""
        with self._cache_lock:
            if self._cache_time:
                age = (datetime.now() - self._cache_time).total_seconds()
                if age < self._cache_ttl:
                    return self._memory_cache.get(key)
            
            # 缓存过期
            self._clear_cache()
            return None
    
    def _add_to_cache(self, key: str, proxy: Proxy):
        """添加到缓存"""
        with self._cache_lock:
            self._memory_cache[key].append(proxy)
            if not self._cache_time:
                self._cache_time = datetime.now()
    
    def _clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._memory_cache.clear()
            self._cache_time = None
    
    # ==================== 批量操作 ====================
    
    def add_proxy(self, proxy: Proxy) -> bool:
        """手动添加代理"""
        return self.storage.add_proxy(proxy)
    
    def add_proxies(self, proxies: List[Proxy]) -> int:
        """批量添加代理"""
        return self.storage.add_proxies_batch(proxies)
    
    def remove_proxy(self, ip: str, port: int) -> bool:
        """删除代理"""
        result = self.storage.delete_proxy(ip, port)
        self._clear_cache()
        return result
    
    def get_all_proxies(self, limit: Optional[int] = None) -> List[Proxy]:
        """获取所有代理"""
        return self.storage.get_all_proxies(limit)
    
    def get_valid_proxies(self, limit: int = 100) -> List[Proxy]:
        """获取所有有效代理"""
        return self.storage.get_valid_proxies(limit=limit)
    
    def clear(self) -> bool:
        """清空代理池"""
        self._clear_cache()
        return self.storage.clear_all()


class ProxyPoolManager:
    """代理池管理器 - 支持多代理池"""
    
    def __init__(self):
        self._pools: Dict[str, ProxyPool] = {}
    
    def create_pool(self, name: str, config: Optional[ProxyPoolConfig] = None) -> ProxyPool:
        """创建代理池"""
        if name in self._pools:
            return self._pools[name]
        
        pool = ProxyPool(config)
        self._pools[name] = pool
        return pool
    
    def get_pool(self, name: str) -> Optional[ProxyPool]:
        """获取代理池"""
        return self._pools.get(name)
    
    def remove_pool(self, name: str) -> bool:
        """删除代理池"""
        if name in self._pools:
            pool = self._pools[name]
            pool.stop_scheduler()
            pool.clear()
            del self._pools[name]
            return True
        return False
    
    def list_pools(self) -> List[str]:
        """列出所有代理池"""
        return list(self._pools.keys())
    
    def get_all_statistics(self) -> Dict[str, Dict]:
        """获取所有代理池统计"""
        return {name: pool.get_statistics() for name, pool in self._pools.items()}


# 全局单例
_default_pool: Optional[ProxyPool] = None
_pool_lock = threading.Lock()


def get_default_pool() -> ProxyPool:
    """获取默认代理池"""
    global _default_pool
    
    with _pool_lock:
        if _default_pool is None:
            _default_pool = ProxyPool()
        return _default_pool


def create_pool(config: Optional[ProxyPoolConfig] = None) -> ProxyPool:
    """创建新代理池"""
    return ProxyPool(config)
