import asyncio
import aiohttp
import random
import re
import time
from typing import List, Set, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("proxy_harvester")

@dataclass
class Proxy:
    host: str
    port: int
    protocol: str  # http, https, socks4, socks5
    latency: float = float('inf')
    alive: bool = False
    
    def __str__(self):
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def to_aiohttp(self):
        if self.protocol in ('http', 'https'):
            return self.__str__()
        # aiohttp supports socks via aiohttp-socks
        return f"{self.protocol}://{self.host}:{self.port}"

# Free proxy sources that don't require auth
PROXY_SOURCES = {
    'http': [
        "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all&simplified=true",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
    ],
    'https': [
        "https://api.proxyscrape.com/v2/?request=get&protocol=https&timeout=10000&country=all&ssl=all&anonymity=all&simplified=true",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/https.txt",
    ],
    'socks4': [
        "https://api.proxyscrape.com/v2/?request=get&protocol=socks4&timeout=10000&country=all&ssl=all&anonymity=all&simplified=true",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
    ],
    'socks5': [
        "https://api.proxyscrape.com/v2/?request=get&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all&simplified=true",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    ]
}

class ProxyHarvester:
    def __init__(self, max_proxies: int = 500, test_url: str = "https://discord.com/api/v9/users/@me"):
        self.max_proxies = max_proxies
        self.test_url = test_url
        self.working_proxies: List[Proxy] = []
        self.semaphore = asyncio.Semaphore(100)  # Concurrent proxy tests
        
    async def fetch_source(self, session: aiohttp.ClientSession, url: str, protocol: str) -> Set[Tuple[str, int]]:
        """Fetch and parse proxies from a single source."""
        proxies = set()
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with session.get(url, timeout=timeout, ssl=False) as resp:
                if resp.status != 200:
                    return proxies
                text = await resp.text()
                
                # Parse various formats: ip:port, json, csv, etc.
                # Pattern matches IP:PORT
                pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[:\s]+(\d{2,5})'
                matches = re.findall(pattern, text)
                
                for ip, port in matches:
                    try:
                        port_num = int(port)
                        if 1 <= port_num <= 65535:
                            proxies.add((ip, port_num))
                    except ValueError:
                        continue
                        
                logger.info(f"Fetched {len(matches)} proxies from {url[:50]}...")
                
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            
        return proxies
    
    async def test_proxy(self, proxy: Proxy) -> Optional[Proxy]:
        """Test if a proxy can reach Discord's API."""
        async with self.semaphore:
            try:
                start = time.time()
                
                if proxy.protocol in ('socks4', 'socks5'):
                    # Requires aiohttp-socks
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(str(proxy))
                    timeout = aiohttp.ClientTimeout(total=8)
                    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                        async with session.get(self.test_url) as resp:
                            latency = time.time() - start
                            if resp.status in (200, 401, 403):  # 401/403 means we hit Discord (auth failed = proxy works)
                                proxy.latency = latency
                                proxy.alive = True
                                return proxy
                else:
                    timeout = aiohttp.ClientTimeout(total=8)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        proxy_url = str(proxy)
                        async with session.get(
                            self.test_url, 
                            proxy=proxy_url, 
                            ssl=False
                        ) as resp:
                            latency = time.time() - start
                            if resp.status in (200, 401, 403):
                                proxy.latency = latency
                                proxy.alive = True
                                return proxy
                                
            except Exception:
                pass
            return None
    
    async def harvest(self) -> List[Proxy]:
        """Main harvest loop: fetch all sources, test all proxies, return working ones."""
        logger.info("🌾 Starting proxy harvest...")
        
        # Fetch all sources concurrently
        all_proxies: Set[Tuple[str, int]] = set()
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for protocol, urls in PROXY_SOURCES.items():
                for url in urls:
                    tasks.append(self.fetch_source(session, url, protocol))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, set):
                    all_proxies.update(result)
        
        logger.info(f"📦 Collected {len(all_proxies)} unique proxies from sources")
        
        # Build proxy objects with protocols (default to http if unknown)
        proxy_objects = []
        for ip, port in all_proxies:
            # Try http first, we'll test all protocols
            proxy_objects.append(Proxy(ip, port, 'http'))
            proxy_objects.append(Proxy(ip, port, 'socks5'))
            proxy_objects.append(Proxy(ip, port, 'socks4'))
        
        # Shuffle for even distribution
        random.shuffle(proxy_objects)
        proxy_objects = proxy_objects[:self.max_proxies * 3]  # Test more than we need
        
        # Test proxies concurrently
        logger.info(f"🔬 Testing {len(proxy_objects)} proxies against Discord...")
        test_tasks = [self.test_proxy(p) for p in proxy_objects]
        results = await asyncio.gather(*test_tasks, return_exceptions=True)
        
        working = [r for r in results if r is not None and isinstance(r, Proxy)]
        working.sort(key=lambda p: p.latency)
        
        self.working_proxies = working[:self.max_proxies]
        logger.info(f"✅ Found {len(self.working_proxies)} working proxies (best: {working[0].latency:.2f}s)" if working else "❌ No working proxies found")
        
        return self.working_proxies
    
    def get_proxy(self) -> Optional[Proxy]:
        """Get a random working proxy, weighted toward faster ones."""
        if not self.working_proxies:
            return None
        # Weighted random: 70% chance to pick from top 30% (fastest)
        if random.random() < 0.7 and len(self.working_proxies) > 10:
            top_tier = self.working_proxies[:max(1, len(self.working_proxies) // 3)]
            return random.choice(top_tier)
        return random.choice(self.working_proxies)
    
    def mark_dead(self, proxy: Proxy):
        """Remove a dead proxy from rotation."""
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
            logger.debug(f"Removed dead proxy: {proxy}")