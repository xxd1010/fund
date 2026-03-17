"""
代理池验证模块 - 多维度代理验证系统
"""
import asyncio
import time
import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from urllib.parse import urlparse
import aiohttp
import requests

from .models import Proxy, ProxyStatus, ProtocolType, AnonymityLevel, ProxyPoolConfig


class ProxyVerifier:
    """代理验证器"""
    
    def __init__(self, config: ProxyPoolConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore: Optional[asyncio.Semaphore] = None
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.config.verify_timeout)
        connector = aiohttp.TCPConnector(
            limit=self.config.verify_concurrency,
            limit_per_host=10
        )
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        self.semaphore = asyncio.Semaphore(self.config.verify_concurrency)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def verify(self, proxy: Proxy) -> Proxy:
        """验证单个代理"""
        start_time = time.time()
        
        try:
            # 1. 基本连接测试
            is_valid, response_time = await self._test_connection(proxy)
            
            if not is_valid:
                proxy.status = ProxyStatus.invalid
                proxy.response_time = response_time
                proxy.fail_count += 1
                proxy.last_checked = datetime.now()
                return proxy
            
            proxy.response_time = response_time
            
            # 2. 如果响应太慢，标记为慢代理
            if response_time > self.config.min_response_time:
                proxy.status = ProxyStatus.slow
                proxy.fail_count += 1
                proxy.last_checked = datetime.now()
                return proxy
            
            # 3. 检测匿名级别
            anonymity = await self._check_anonymity(proxy)
            proxy.anonymity = anonymity
            
            # 4. 检测支持的协议
            supported_protocols = await self._check_protocols(proxy)
            
            # 5. 更新代理信息
            proxy.status = ProxyStatus.valid
            proxy.success_count += 1
            proxy.last_checked = datetime.now()
            proxy.last_success = datetime.now()
            
            # 更新协议（如果检测到支持HTTPS）
            if ProtocolType.HTTPS in supported_protocols:
                proxy.protocol = ProtocolType.HTTPS
            
        except asyncio.TimeoutError:
            proxy.status = ProxyStatus.invalid
            proxy.response_time = self.config.verify_timeout
            proxy.fail_count += 1
            proxy.last_checked = datetime.now()
        except Exception as e:
            proxy.status = ProxyStatus.invalid
            proxy.fail_count += 1
            proxy.last_checked = datetime.now()
        
        return proxy
    
    async def verify_batch(self, proxies: List[Proxy]) -> List[Proxy]:
        """批量验证代理（并发）"""
        async with self:
            tasks = [self._verify_with_semaphore(proxy) for proxy in proxies]
            return await asyncio.gather(*tasks)
    
    async def _verify_with_semaphore(self, proxy: Proxy) -> Proxy:
        """使用信号量控制并发"""
        async with self.semaphore:
            return await self.verify(proxy)
    
    async def _test_connection(self, proxy: Proxy) -> Tuple[bool, float]:
        """测试代理连接"""
        start_time = time.time()
        
        try:
            # 使用配置的验证URL
            verify_url = self.config.verify_urls[0]
            
            # 构建代理字典
            proxy_dict = self._build_proxy_dict(proxy)
            
            async with self.session.get(
                verify_url,
                proxy=proxy_dict.get(proxy.protocol.value),
                allow_redirects=False
            ) as response:
                response_time = time.time() - start_time
                
                if response.status in [200, 201, 204]:
                    return True, response_time
                
                return False, response_time
                
        except asyncio.TimeoutError:
            return False, self.config.verify_timeout
        except aiohttp.ClientError:
            return False, time.time() - start_time
        except Exception:
            return False, time.time() - start_time
    
    async def _check_anonymity(self, proxy: Proxy) -> AnonymityLevel:
        """检测代理匿名级别"""
        try:
            # 检测我们自己的请求头是否被暴露
            check_url = self.config.check_anonymity_url
            proxy_dict = self._build_proxy_dict(proxy)
            
            async with self.session.get(
                check_url,
                proxy=proxy_dict.get(proxy.protocol.value)
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    try:
                        headers = json.loads(text)
                        
                        # 检查是否有代理特征
                        # 1. 检查是否暴露了真实IP
                        # 2. 检查是否有Via或X-Forwarded-For头
                        
                        # 高匿名：不会暴露任何代理特征
                        # 普通匿名：会暴露使用了代理
                        # 透明代理：会暴露真实IP
                        
                        has_forwarded = 'x-forwarded-for' in [h.lower() for h in headers.keys()]
                        has_via = 'via' in [h.lower() for h in headers.keys()]
                        
                        if has_forwarded or has_via:
                            return AnonymityLevel.ANONYMOUS
                        
                        # 如果返回的IP不是代理IP，则是透明代理
                        # 这里简化处理：默认返回高匿名
                        return AnonymityLevel.HIGH_ANONYMOUS
                        
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        
        return AnonymityLevel.TRANSPARENT
    
    async def _check_protocols(self, proxy: Proxy) -> List[ProtocolType]:
        """检测支持的协议"""
        supported = []
        
        # 测试HTTP
        if await self._test_protocol(proxy, "http://httpbin.org/ip", ProtocolType.HTTP):
            supported.append(ProtocolType.HTTP)
        
        # 测试HTTPS
        if await self._test_protocol(proxy, "https://httpbin.org/ip", ProtocolType.HTTPS):
            supported.append(ProtocolType.HTTPS)
        
        # 测试SOCKS5
        if proxy.protocol == ProtocolType.SOCKS5:
            if await self._test_socks5(proxy):
                supported.append(ProtocolType.SOCKS5)
        
        return supported
    
    async def _test_protocol(self, proxy: Proxy, url: str, protocol: ProtocolType) -> bool:
        """测试特定协议"""
        try:
            proxy_dict = self._build_proxy_dict(proxy)
            
            async with self.session.get(
                url,
                proxy=proxy_dict.get(protocol.value),
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def _test_socks5(self, proxy: Proxy) -> bool:
        """测试SOCKS5代理"""
        try:
            import socks
            
            # 使用socks库直接测试
            s = socks.socksocket()
            s.set_proxy(
                socks.SOCKS5,
                proxy.ip,
                proxy.port,
                rdns=True
            )
            s.settimeout(5)
            s.connect(("httpbin.org", 80))
            s.close()
            return True
        except Exception:
            return False
    
    def _build_proxy_dict(self, proxy: Proxy) -> Dict[str, str]:
        """构建代理字典"""
        if proxy.protocol == ProtocolType.SOCKS5:
            return {"socks5": f"{proxy.ip}:{proxy.port}"}
        return {proxy.protocol.value: f"{proxy.ip}:{proxy.port}"}


class SyncProxyVerifier:
    """同步代理验证器（备用方案）"""
    
    def __init__(self, config: ProxyPoolConfig):
        self.config = config
    
    def verify(self, proxy: Proxy) -> Proxy:
        """同步验证单个代理"""
        start_time = time.time()
        
        try:
            # 测试连接
            is_valid, response_time = self._test_connection(proxy)
            
            if not is_valid:
                proxy.status = ProxyStatus.invalid
                proxy.response_time = response_time
                proxy.fail_count += 1
                proxy.last_checked = datetime.now()
                return proxy
            
            proxy.response_time = response_time
            
            if response_time > self.config.min_response_time:
                proxy.status = ProxyStatus.slow
                proxy.fail_count += 1
                proxy.last_checked = datetime.now()
                return proxy
            
            proxy.status = ProxyStatus.valid
            proxy.success_count += 1
            proxy.last_checked = datetime.now()
            proxy.last_success = datetime.now()
            
        except requests.Timeout:
            proxy.status = ProxyStatus.invalid
            proxy.response_time = self.config.verify_timeout
            proxy.fail_count += 1
            proxy.last_checked = datetime.now()
        except Exception as e:
            proxy.status = ProxyStatus.invalid
            proxy.fail_count += 1
            proxy.last_checked = datetime.now()
        
        return proxy
    
    def verify_batch(self, proxies: List[Proxy], max_workers: int = 10) -> List[Proxy]:
        """批量验证代理（多线程）"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.verify, proxy): proxy for proxy in proxies}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    proxy = futures[future]
                    proxy.status = ProxyStatus.invalid
                    results.append(proxy)
        
        return results
    
    def _test_connection(self, proxy: Proxy) -> Tuple[bool, float]:
        """测试代理连接"""
        start_time = time.time()
        
        try:
            verify_url = self.config.verify_urls[0]
            proxy_url = self._build_proxy_url(proxy)
            
            response = requests.get(
                verify_url,
                proxies={"http": proxy_url, "https": proxy_url},
                timeout=self.config.verify_timeout,
                allow_redirects=False
            )
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 201, 204]:
                return True, response_time
            
            return False, response_time
            
        except requests.Timeout:
            return False, self.config.verify_timeout
        except requests.RequestException:
            return False, time.time() - start_time
        except Exception:
            return False, time.time() - start_time
    
    def _build_proxy_url(self, proxy: Proxy) -> str:
        """构建代理URL"""
        if proxy.protocol == ProtocolType.SOCKS5:
            return f"socks5://{proxy.ip}:{proxy.port}"
        return f"{proxy.protocol.value}://{proxy.ip}:{proxy.port}"


class VerifierStats:
    """验证统计信息"""
    
    def __init__(self):
        self.total = 0
        self.valid = 0
        self.invalid = 0
        self.slow = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def add_result(self, proxy: Proxy):
        """添加验证结果"""
        self.total += 1
        if proxy.status == ProxyStatus.valid:
            self.valid += 1
        elif proxy.status == ProxyStatus.slow:
            self.slow += 1
        else:
            self.invalid += 1
    
    def to_dict(self) -> dict:
        """转换为字典"""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            "total": self.total,
            "valid": self.valid,
            "invalid": self.invalid,
            "slow": self.slow,
            "valid_rate": round(self.valid / self.total, 3) if self.total > 0 else 0,
            "duration": round(duration, 2) if duration else None
        }
