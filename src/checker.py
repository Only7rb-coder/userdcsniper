import asyncio
import aiohttp
import random
import time
import json
import os
from typing import List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .proxy_harvester import ProxyHarvester
from .discord_webhook import WebhookNotifier

@dataclass
class CheckResult:
    username: str
    available: bool
    checked_at: str
    proxy_used: Optional[str] = None
    response_time: float = 0.0
    error: Optional[str] = None

class DiscordUsernameChecker:
    def __init__(self, concurrency=50, timeout=10, delay_between=0.5, webhook_url=None, proxy_harvester=None):
        self.concurrency = concurrency
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.delay_between = delay_between
        self.webhook = None
        if webhook_url and webhook_url.strip().startswith('http'):
            try:
                self.webhook = WebhookNotifier(webhook_url.strip())
                print(f"[WEBHOOK] Enabled: {webhook_url[:50]}...")
            except Exception as e:
                print(f"[WEBHOOK] Failed to init: {e}")
        else:
            print(f"[WEBHOOK] Disabled (no valid URL)")
            
        self.proxy_harvester = proxy_harvester or ProxyHarvester()
        self.semaphore = asyncio.Semaphore(concurrency)
        self.results = []
        self.stats = {'checked': 0, 'available': 0, 'errors': 0, 'start_time': None}
        
    async def check_username(self, session: aiohttp.ClientSession, username: str) -> CheckResult:
        async with self.semaphore:
            start = time.time()
            proxy = self.proxy_harvester.get_proxy()
            proxy_str = str(proxy) if proxy else None
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Content-Type': 'application/json',
                    'Origin': 'https://discord.com',
                    'Referer': 'https://discord.com/register'
                }
                payload = {
                    'username': username,
                    'consent': True,
                    'date_of_birth': '1990-01-01',
                    'gift_code_sku_id': None,
                    'captcha_key': None
                }
                
                kwargs = {
                    'headers': headers,
                    'json': payload,
                    'timeout': self.timeout,
                    'ssl': False
                }
                if proxy:
                    kwargs['proxy'] = proxy_str
                
                async with session.post("https://discord.com/api/v9/auth/register", **kwargs) as resp:
                    response_time = time.time() - start
                    timestamp = datetime.now().isoformat()
                    
                    if resp.status == 400:
                        try:
                            data = await resp.json()
                            if 'username' in data.get('errors', {}):
                                return CheckResult(username, False, timestamp, proxy_str, response_time)
                        except:
                            pass
                        return CheckResult(username, False, timestamp, proxy_str, response_time, "bad_request")
                    
                    elif resp.status == 429:
                        return CheckResult(username, False, timestamp, proxy_str, response_time, "rate_limited")
                    
                    elif resp.status in (200, 201, 204):
                        return CheckResult(username, True, timestamp, proxy_str, response_time)
                    
                    else:
                        return CheckResult(username, False, timestamp, proxy_str, response_time, f"status_{resp.status}")
                        
            except asyncio.TimeoutError:
                if proxy:
                    self.proxy_harvester.mark_dead(proxy)
                return CheckResult(username, False, datetime.now().isoformat(), proxy_str, time.time() - start, "timeout")
            except Exception as e:
                if proxy and 'proxy' in str(e).lower():
                    self.proxy_harvester.mark_dead(proxy)
                return CheckResult(username, False, datetime.now().isoformat(), proxy_str, time.time() - start, str(e)[:50])
            
            finally:
                await asyncio.sleep(self.delay_between * random.uniform(0.8, 1.2))
    
    async def run(self, usernames: List[str]) -> List[CheckResult]:
        self.stats['start_time'] = time.time()
        total = len(usernames)
        
        print(f"[CHECK] Starting hunt: {total} usernames @ {self.concurrency} concurrency")
        
        # Webhook start
        if self.webhook:
            try:
                await self.webhook.notify_start(total, self.concurrency, 
                    os.environ.get('LENGTH', '2-32'),
                    os.environ.get('PATTERN', 'mixed'), 0)
                print("[WEBHOOK] Start notification sent")
            except Exception as e:
                print(f"[WEBHOOK] Start failed: {e}")
        
        # Harvest proxies
        if not self.proxy_harvester.working_proxies:
            await self.proxy_harvester.harvest()
        
        if not self.proxy_harvester.working_proxies:
            print("[CHECK] ❌ No working proxies! Running direct (will likely rate limit)...")
        
        # Webhook proxies ready
        if self.webhook and self.proxy_harvester.working_proxies:
            try:
                best = self.proxy_harvester.working_proxies[0].latency
                await self.webhook.notify_proxies_ready(len(self.proxy_harvester.working_proxies), best)
                print("[WEBHOOK] Proxies notification sent")
            except Exception as e:
                print(f"[WEBHOOK] Proxies notify failed: {e}")
        
        connector = aiohttp.TCPConnector(limit=self.concurrency * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.check_username(session, u) for u in usernames]
            
            for i, completed in enumerate(asyncio.as_completed(tasks)):
                result = await completed
                self.results.append(result)
                self.stats['checked'] += 1
                
                if result.available:
                    self.stats['available'] += 1
                    print(f"[HIT] 🎯 {result.username} AVAILABLE!")
                    if self.webhook:
                        try:
                            await self.webhook.notify_hit(result)
                        except Exception as e:
                            print(f"[WEBHOOK] Hit notify failed: {e}")
                
                elif result.error:
                    self.stats['errors'] += 1
                
                # Progress every 100
                if self.stats['checked'] % 100 == 0:
                    elapsed = time.time() - self.stats['start_time']
                    rate = self.stats['checked'] / elapsed
                    print(f"[PROGRESS] {self.stats['checked']}/{total} | {rate:.1f}/s | Hits: {self.stats['available']} | Proxies: {len(self.proxy_harvester.working_proxies)}")
                    
                    if self.webhook:
                        try:
                            await self.webhook.notify_progress(self.stats['checked'], total, 
                                self.stats['available'], elapsed, 
                                len(self.proxy_harvester.working_proxies))
                        except Exception as e:
                            print(f"[WEBHOOK] Progress notify failed: {e}")
        
        # Final
        elapsed = time.time() - self.stats['start_time']
        print(f"[DONE] {self.stats['checked']} in {elapsed:.1f}s | Hits: {self.stats['available']} | Errors: {self.stats['errors']}")
        
        if self.webhook:
            try:
                await self.webhook.notify_complete(self.stats['checked'], 
                    self.stats['available'], elapsed, self.stats['errors'])
                print("[WEBHOOK] Complete notification sent")
            except Exception as e:
                print(f"[WEBHOOK] Complete notify failed: {e}")
        
        self._save_results()
        return self.results
    
    def _save_results(self):
        os.makedirs('results', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(f'results/check_{timestamp}.json', 'w') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        
        available = [r for r in self.results if r.available]
        if available:
            with open(f'results/hits_{timestamp}.txt', 'w') as f:
                for r in available:
                    f.write(f"{r.username}\n")
            with open('results/all_hits.txt', 'a') as f:
                for r in available:
                    f.write(f"{r.username}\n")
            print(f"[SAVE] {len(available)} hits saved to results/")
