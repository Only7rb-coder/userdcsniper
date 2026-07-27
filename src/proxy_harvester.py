import asyncio
import aiohttp
import random
import re
import time
import json
import os
from typing import List, Set, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Proxy:
    host: str
    port: int
    protocol: str
    latency: float = float('inf')
    alive: bool = False
    
    def __str__(self):
        return f"http://{self.host}:{self.port}"  # Only HTTP, no SOCKS

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all&simplified=true",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]

class ProxyHarvester:
    def __init__(self, max_proxies: int = 100):
        self.max_proxies = max_proxies
        self.working_proxies: List[Proxy] = []
        
    async def fetch_source(self, session: aiohttp.ClientSession, url: str) -> Set[Tuple[str, int]]:
        proxies = set()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), ssl=False) as resp:
                if resp.status != 200:
                    return proxies
                text = await resp.text()
                pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[:\s]+(\d{2,5})'
                for ip, port in re.findall(pattern, text):
                    try:
                        p = int(port)
                        if 1 <= p <= 65535:
                            proxies.add((ip, p))
                    except:
                        pass
        except Exception as e:
            print(f"[PROXY] Fetch failed: {url[:40]}... ({e})")
        return proxies
    
    async def test_proxy(self, proxy: Proxy) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=3)  # AGGRESSIVE timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                start = time.time()
                async with session.get(
                    "https://discord.com/api/v9/users/@me",
                    proxy=str(proxy), ssl=False
                ) as resp:
                    if resp.status in (200, 401, 403):
                        proxy.latency = time.time() - start
                        proxy.alive = True
                        return True
        except:
            pass
        return False
    
    async def harvest(self) -> List[Proxy]:
        print("[PROXY] Step 1: Fetching proxy lists...")
        all_proxies: Set[Tuple[str, int]] = set()
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_source(session, url) for url in PROXY_SOURCES]
            results = await asyncio.gather(*tasks)
            for r in results:
                all_proxies.update(r)
        
        print(f"[PROXY] Fetched {len(all_proxies)} raw proxies")
        
        if not all_proxies:
            print("[PROXY] ❌ No proxies fetched! Running direct...")
            return []
        
        # Build proxy objects, limit to testable amount
        proxy_objects = [Proxy(ip, port, 'http') for ip, port in list(all_proxies)[:self.max_proxies * 3]]
        random.shuffle(proxy_objects)
        
        print(f"[PROXY] Testing {len(proxy_objects)} proxies (3s timeout each)...")
        
        # Test in small batches to avoid overwhelming
        working = []
        batch_size = 20
        for i in range(0, len(proxy_objects), batch_size):
            batch = proxy_objects[i:i+batch_size]
            results = await asyncio.gather(*[self.test_proxy(p) for p in batch])
            for proxy, ok in zip(batch, results):
                if ok:
                    working.append(proxy)
                    print(f"[PROXY] ✓ {proxy.host}:{proxy.port} ({proxy.latency:.2f}s)")
            
            if len(working) >= self.max_proxies:
                break
            
            print(f"[PROXY] Batch {i//batch_size + 1}: {len(working)} working so far...")
        
        working.sort(key=lambda p: p.latency)
        self.working_proxies = working[:self.max_proxies]
        print(f"[PROXY] ✅ {len(self.working_proxies)} working proxies ready")
        
        return self.working_proxies
    
    def get_proxy(self) -> Optional[Proxy]:
        if not self.working_proxies:
            return None
        return random.choice(self.working_proxies[:max(10, len(self.working_proxies)//3)] 
                           if random.random() < 0.7 else self.working_proxies)
    
    def mark_dead(self, proxy: Proxy):
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)
