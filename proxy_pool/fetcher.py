"""
代理池抓取模块 - 多源代理IP自动抓取
"""
import asyncio
import re
import time
from abc import ABC, abstractmethod
from typing import List, Optional
from urllib.parse import urlparse
import aiohttp
import requests

from .models import Proxy, ProtocolType, AnonymityLevel, ProxyPoolConfig


class BaseFetcher(ABC):
    """代理抓取器基类"""
    
    def __init__(self, config: ProxyPoolConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
    
    @abstractmethod
    async def fetch(self) -> List[Proxy]:
        """抓取代理列表"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """抓取源名称"""
        pass
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.config.verify_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _fetch_text(self, url: str, headers: Optional[dict] = None) -> Optional[str]:
        """获取网页内容"""
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
        except Exception:
            pass
        return None
    
    def _parse_proxy_line(self, line: str, source: str) -> Optional[Proxy]:
        """解析代理行数据"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        
        # 支持格式: ip:port 或 ip:port:protocol
        parts = line.split(':')
        if len(parts) >= 2:
            try:
                ip = parts[0].strip()
                port = int(parts[1].strip())
                
                # 判断协议类型
                protocol = ProtocolType.HTTP
                if len(parts) > 2:
                    protocol_str = parts[2].lower().strip()
                    if protocol_str in ['https', 'socks5', 'socks4']:
                        protocol = ProtocolType(protocol_str)
                
                return Proxy(
                    ip=ip,
                    port=port,
                    protocol=protocol,
                    source=source,
                    status=ProxyStatus.untested
                )
            except (ValueError, KeyError):
                return None
        return None


class FreeProxyListFetcher(BaseFetcher):
    """从 free-proxy-list.net 抓取"""
    
    @property
    def name(self) -> str:
        return "free-proxy-list"
    
    async def fetch(self) -> List[Proxy]:
        proxies = []
        url = "https://free-proxy-list.net/"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            text = await self._fetch_text(url, headers)
            
            if text:
                # 解析表格数据
                table_match = re.search(r'<tbody>(.*?)</tbody>', text, re.DOTALL)
                if table_match:
                    rows = re.findall(r'<tr>(.*?)</tr>', table_match.group(1), re.DOTALL)
                    for row in rows:
                        cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL)
                        if len(cells) >= 2:
                            ip = cells[0].strip()
                            port = cells[1].strip()
                            
                            # 解析协议
                            is_https = 'yes' in cells[6].lower() if len(cells) > 6 else False
                            protocol = ProtocolType.HTTPS if is_https else ProtocolType.HTTP
                            
                            # 解析匿名级别
                            anonymity = self._parse_anonymity(cells[4] if len(cells) > 4 else '')
                            
                            proxy = Proxy(
                                ip=ip,
                                port=int(port),
                                protocol=protocol,
                                anonymity=anonymity,
                                source=self.name,
                                status=ProxyStatus.untested
                            )
                            proxies.append(proxy)
        except Exception:
            pass
        
        return proxies
    
    def _parse_anonymity(self, text: str) -> AnonymityLevel:
        text = text.lower()
        if 'anonymous' in text and 'transparent' not in text:
            if 'high' in text or 'elite' in text:
                return AnonymityLevel.HIGH_ANONYMOUS
            return AnonymityLevel.ANONYMOUS
        return AnonymityLevel.TRANSPARENT


class ProxyScrapeFetcher(BaseFetcher):
    """从 proxyscrape.com 抓取"""
    
    @property
    def name(self) -> str:
        return "proxyscrape"
    
    async def fetch(self) -> List[Proxy]:
        proxies = []
        
        # 支持的API列表
        apis = [
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=https&timeout=10000&country=all",
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
        ]
        
        protocols = [ProtocolType.HTTP, ProtocolType.HTTPS, ProtocolType.SOCKS5]
        
        for url, protocol in zip(apis, protocols):
            try:
                text = await self._fetch_text(url)
                if text:
                    for line in text.split('\n'):
                        proxy = self._parse_proxy_line(line, self.name)
                        if proxy:
                            proxy.protocol = protocol
                            proxies.append(proxy)
            except Exception:
                continue
        
        return proxies


class GitHubFetcher(BaseFetcher):
    """从 GitHub 热门代理列表抓取"""
    
    @property
    def name(self) -> str:
        return "github"
    
    async def fetch(self) -> List[Proxy]:
        proxies = []
        
        urls = [
            ("https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.json", ProtocolType.SOCKS5),
            ("https://raw.githubusercontent.com/jetkai/proxy-list/main/online/all.txt", None),
            ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", ProtocolType.HTTP),
            ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt", ProtocolType.SOCKS5),
        ]
        
        for url, default_protocol in urls:
            try:
                text = await self._fetch_text(url)
                if text:
                    for line in text.split('\n'):
                        proxy = self._parse_proxy_line(line, self.name)
                        if proxy:
                            if default_protocol:
                                proxy.protocol = default_protocol
                            proxies.append(proxy)
            except Exception:
                continue
        
        return proxies


class ProxyPoolTopFetcher(BaseFetcher):
    """从 proxy-pool.top 抓取"""
    
    @property
    def name(self) -> str:
        return "proxy-pool-top"
    
    async def fetch(self) -> List[Proxy]:
        proxies = []
        
        try:
            text = await self._fetch_text("https://proxy-pool.top/api/proxies")
            if text:
                import json
                data = json.loads(text)
                if isinstance(data, dict) and 'proxies' in data:
                    for item in data['proxies']:
                        try:
                            proxy = Proxy(
                                ip=item.get('ip', ''),
                                port=int(item.get('port', 0)),
                                protocol=ProtocolType(item.get('protocol', 'http')),
                                source=self.name,
                                status=ProxyStatus.untested
                            )
                            proxies.append(proxy)
                        except (ValueError, KeyError):
                            continue
        except Exception:
            pass
        
        return proxies


class ProxyFetcherManager:
    """代理抓取管理器"""
    
    def __init__(self, config: ProxyPoolConfig):
        self.config = config
        self.fetchers: List[BaseFetcher] = [
            FreeProxyListFetcher(config),
            ProxyScrapeFetcher(config),
            GitHubFetcher(config),
            ProxyPoolTopFetcher(config),
        ]
    
    async def fetch_all(self) -> List[Proxy]:
        """从所有源抓取代理"""
        all_proxies = []
        
        async with asyncio.TaskGroup() as task_group:
            tasks = [task_group.create_task(fetcher.fetch()) for fetcher in self.fetchers]
        
        for task in tasks:
            try:
                proxies = task.result()
                all_proxies.extend(proxies)
            except Exception:
                continue
        
        # 去重
        seen = set()
        unique_proxies = []
        for proxy in all_proxies:
            key = (proxy.ip, proxy.port)
            if key not in seen:
                seen.add(key)
                unique_proxies.append(proxy)
        
        return unique_proxies
    
    async def fetch_from_source(self, source_name: str) -> List[Proxy]:
        """从指定源抓取"""
        for fetcher in self.fetchers:
            if fetcher.name == source_name:
                async with fetcher:
                    return await fetcher.fetch()
        return []


class SyncProxyFetcher:
    """同步代理抓取器（备用方案）"""
    
    def __init__(self, config: ProxyPoolConfig):
        self.config = config
    
    def fetch_all(self) -> List[Proxy]:
        """同步抓取所有代理"""
        all_proxies = []
        
        # 使用 requests 进行同步抓取
        sources = [
            self._fetch_free_proxy_list,
            self._fetch_github,
        ]
        
        for source_func in sources:
            try:
                proxies = source_func()
                all_proxies.extend(proxies)
            except Exception:
                continue
        
        # 去重
        seen = set()
        unique_proxies = []
        for proxy in all_proxies:
            key = (proxy.ip, proxy.port)
            if key not in seen:
                seen.add(key)
                unique_proxies.append(proxy)
        
        return unique_proxies
    
    def _fetch_free_proxy_list(self) -> List[Proxy]:
        """从 free-proxy-list.net 抓取"""
        proxies = []
        
        try:
            response = requests.get(
                "https://free-proxy-list.net/",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                text = response.text
                table_match = re.search(r'<tbody>(.*?)</tbody>', text, re.DOTALL)
                if table_match:
                    rows = re.findall(r'<tr>(.*?)</tr>', table_match.group(1), re.DOTALL)
                    for row in rows:
                        cells = re.findall(r'<td>(.*?)</td>', row, re.DOTALL)
                        if len(cells) >= 2:
                            try:
                                ip = cells[0].strip()
                                port = int(cells[1].strip())
                                
                                is_https = 'yes' in cells[6].lower() if len(cells) > 6 else False
                                protocol = ProtocolType.HTTPS if is_https else ProtocolType.HTTP
                                
                                anonymity = AnonymityLevel.TRANSPARENT
                                if len(cells) > 4:
                                    anon_text = cells[4].lower()
                                    if 'anonymous' in anon_text:
                                        if 'high' in anon_text or 'elite' in anon_text:
                                            anonymity = AnonymityLevel.HIGH_ANONYMOUS
                                        else:
                                            anonymity = AnonymityLevel.ANONYMOUS
                                
                                proxy = Proxy(
                                    ip=ip,
                                    port=port,
                                    protocol=protocol,
                                    anonymity=anonymity,
                                    source="free-proxy-list",
                                    status=ProxyStatus.untested
                                )
                                proxies.append(proxy)
                            except (ValueError, IndexError):
                                continue
        except Exception:
            pass
        
        return proxies
    
    def _fetch_github(self) -> List[Proxy]:
        """从 GitHub 抓取"""
        proxies = []
        
        urls = [
            ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", ProtocolType.HTTP),
            ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt", ProtocolType.SOCKS5),
        ]
        
        for url, protocol in urls:
            try:
                response = requests.get(url, timeout=20)
                if response.status_code == 200:
                    for line in response.text.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split(':')
                            if len(parts) >= 2:
                                try:
                                    ip = parts[0]
                                    port = int(parts[1])
                                    
                                    proxy = Proxy(
                                        ip=ip,
                                        port=port,
                                        protocol=protocol,
                                        source="github",
                                        status=ProxyStatus.untested
                                    )
                                    proxies.append(proxy)
                                except (ValueError, IndexError):
                                    continue
            except Exception:
                continue
        
        return proxies
