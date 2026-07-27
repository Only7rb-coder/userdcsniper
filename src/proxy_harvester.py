import asyncio
import aiohttp
import random
import re
import time
import json
import os
from typing import List, Set, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("proxy_harvester")

@dataclass
class Proxy:
    host: str
    port: int
    protocol: str
    latency: float = float('inf')
    alive: bool = False
    
    def __str__(self):
        return f"{self.protocol}://{self.host}:{self.port}"

PROXY_SOURCES = {
    'http': [
        "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&simplified=true",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    ],
    'https': [
        "https://api.proxyscrape.com/v2/?request=get&protocol=https&timeout=10000&country=all&ssl=all&anonymity=all&simplified=true",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
    ],
    'socks4': [
        "https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all&ssl=all&anonymity=all&simplified=true",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
    ],
    'socks5': [
        "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all&simplified=true",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    ]
}

class ProxyHarvester:
    def __init__(self, max_proxies: int = 300, test_url: str = "https://discord.com/api/v9/users/@me"):
        self.max_proxies = max_proxies
        self.test_url = test_url
        self.working_proxies: List[Proxy] = []
        self.semaphore = asyncio.Semaphore(50)
        
    async def fetch_source(self, session: aiohttp.ClientSession, url: str) -> Set[Tuple[str, int]]:
        proxies = set()
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with session.get(url, timeout=timeout, ssl=False) as resp:
                if resp.status != 200:
                    return proxies
                text = await resp.text()
                pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[:\s]+(\d{2,5})'
                matches = re.findall(pattern, text)
                for ip, port in matches:
                    try:
                        port_num = int(port)
                        if 1 <= port_num <= 65535:
                            proxies.add((ip, port_num))
                    except ValueError:
                        continue
        except Exception:
            pass
        return proxies
    
    async def test_proxy(self, proxy: Proxy) -> Optional[Proxy]:
        async with self.semaphore:
            try:
                start = time.time()
                if proxy.protocol in ('socks4', 'socks5'):
                    try:
                        from aiohttp_socks import ProxyConnector
                        connector = ProxyConnector.from_url(str(proxy))
                        timeout = aiohttp.ClientTimeout(total=8)
                        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                            async with session.get(self.test_url) as resp:
                                if resp.status in (200, 401, 403):
                                    proxy.latency = time.time() - start
                                    proxy.alive = True
                                    return proxy
                    except ImportError:
                        return None
                else:
                    timeout = aiohttp.ClientTimeout(total=8)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(self.test_url, proxy=str(proxy), ssl=False) as resp:
                            if resp.status in (200, 401, 403):
                                proxy.latency = time.time() - start
                                proxy.alive = True
                                return proxy
            except Exception:
                pass
            return None
    
    async def harvest(self) -> List[Proxy]:
        print("[PROXY] Harvesting free proxies...")
        all_proxies: Set[Tuple[str, int]] = set()
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for protocol, urls in PROXY_SOURCES.items():
                for url in urls:
                    tasks.append(self.fetch_source(session, url))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, set):
                    all_proxies.update(result)
        
        print(f"[PROXY] Collected {len(all_proxies)} raw proxies")
        
        proxy_objects = []
        for ip, port in all_proxies:
            proxy_objects.append(Proxy(ip, port, 'http'))
            proxy_objects.append(Proxy(ip, port, 'socks5'))
        
        random.shuffle(proxy_objects)
        proxy_objects = proxy_objects[:self.max_proxies * 2]
        
        print(f"[PROXY] Testing {len(proxy_objects)} proxies...")
        test_tasks = [self.test_proxy(p) for p in proxy_objects]
        results = await asyncio.gather(*test_tasks, return_exceptions=True)
        
        working = [r for r in results if isinstance(r, Proxy) and r.alive]
        working.sort(key=lambda p: p.latency)
        
        self.working_proxies = working[:self.max_proxies]
        print(f"[PROXY] ✅ {len(self.working_proxies)} working proxies ready")
        
        return self.working_proxies
    
    def get_proxy(self) -> Optional[Proxy]:
        if not self.working_proxies:
            return None
        if random.random() < 0.7 and len(self.working_proxies) > 10:
            top_tier = self.working_proxies[:max(1, len(self.working_proxies) // 3)]
            return random.choice(top_tier)
        return random.choice(self.working_proxies)
    
    def mark_dead(self, proxy: Proxy):
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
