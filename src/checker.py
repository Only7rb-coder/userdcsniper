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
    def __init__(self, concurrency=50, timeout=10, delay_between=0.5, 
                 webhook_url=None, proxy_harvester=None, mode="hunt"):
        self.concurrency = concurrency
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.delay_between = delay_between
        self.mode = mode  # "hunt" or "monitor"
        
        self.webhook = None
        if webhook_url and webhook_url.strip().startswith('http'):
            self.webhook = WebhookNotifier(webhook_url.strip())
            print(f"[WEBHOOK] Enabled")
        else:
            print(f"[WEBHOOK] Disabled")
            
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
                # THE FIX: Use a session-based approach that properly reads errors
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Content-Type': 'application/json',
                    'Origin': 'https://discord.com',
                    'Referer': 'https://discord.com/register',
                    'X-Super-Properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIn0='
                }
                
                payload = {
                    'username': username,
                    'consent': True,
                    'date_of_birth': '1990-01-01',
                    'gift_code_sku_id': None,
                    'captcha_key': None,
                    'promotional_email_opt_in': False
                }
                
                kwargs = {
                    'headers': headers,
                    'json': payload,
                    'timeout': self.timeout,
                    'ssl': False
                }
                if proxy:
                    kwargs['proxy'] = proxy_str
                
                async with session.post(
                    "https://discord.com/api/v9/auth/register", 
                    **kwargs
                ) as resp:
                    response_time = time.time() - start
                    timestamp = datetime.now().isoformat()
                    
                    body = {}
                    try:
                        body = await resp.json()
                    except:
                        pass
                    
                    # DEBUG: Log actual response for troubleshooting
                    if self.stats['checked'] < 5:
                        print(f"[DEBUG] {username} -> status:{resp.status} body:{str(body)[:200]}")
                    
                    # PROPER AVAILABILITY DETECTION:
                    # 400 with username._errors = TAKEN (or invalid)
                    # 400 with captcha = need captcha (treat as unknown)
                    # 200/204 = AVAILABLE (registration would proceed)
                    
                    if resp.status == 200:
                        # 200 OK means username is valid and available!
                        return CheckResult(username, True, timestamp, proxy_str, response_time)
                    
                    elif resp.status == 204:
                        return CheckResult(username, True, timestamp, proxy_str, response_time)
                    
                    elif resp.status == 400:
                        errors = body.get('errors', {})
                        username_errors = errors.get('username', {})
                        
                        if username_errors:
                            # Has username-specific errors = taken or invalid
                            # Check if it's "already registered" vs "invalid format"
                            error_str = str(username_errors).lower()
                            if 'already' in error_str or 'taken' in error_str:
                                return CheckResult(username, False, timestamp, proxy_str, response_time, "taken")
                            else:
                                # Invalid format, not just taken
                                return CheckResult(username, False, timestamp, proxy_str, response_time, "invalid")
                        else:
                            # 400 but no username error = might be available but other issue
                            return CheckResult(username, True, timestamp, proxy_str, response_time, "maybe_available")
                    
                    elif resp.status == 429:
                        return CheckResult(username, False, timestamp, proxy_str, response_time, "rate_limited")
                    
                    else:
                        return CheckResult(username, False, timestamp, proxy_str, response_time, f"status_{resp.status}")
                        
            except asyncio.TimeoutError:
                if proxy:
                    self.proxy_harvester.mark_dead(proxy)
                return CheckResult(username, False, datetime.now().isoformat(), proxy_str, time.time() - start, "timeout")
            except Exception as e:
                err = str(e)[:60]
                if proxy and 'proxy' in err.lower():
                    self.proxy_harvester.mark_dead(proxy)
                return CheckResult(username, False, datetime.now().isoformat(), proxy_str, time.time() - start, err)
            
            finally:
                await asyncio.sleep(self.delay_between * random.uniform(0.8, 1.2))
    
    async def run(self, usernames: List[str]) -> List[CheckResult]:
        self.stats['start_time'] = time.time()
        total = len(usernames)
        
        print(f"[CHECK] Mode: {self.mode} | {total} usernames | {self.concurrency} concurrency")
        
        if self.webhook:
            await self.webhook.notify_start(total, self.concurrency,
                os.environ.get('LENGTH', '5-7'),
                os.environ.get('PATTERN', 'mixed'),
                len(self.proxy_harvester.working_proxies),
                self.mode)
        
        if not self.proxy_harvester.working_proxies:
            await self.proxy_harvester.harvest()
        
        if not self.proxy_harvester.working_proxies:
            print("[CHECK] ⚠️ No proxies! Running direct (high rate limit risk)...")
        
        if self.webhook and self.proxy_harvester.working_proxies:
            await self.webhook.notify_proxies_ready(
                len(self.proxy_harvester.working_proxies),
                self.proxy_harvester.working_proxies[0].latency)
        
        connector = aiohttp.TCPConnector(limit=self.concurrency * 2)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.check_username(session, u) for u in usernames]
            
            for completed in asyncio.as_completed(tasks):
                result = await completed
                self.results.append(result)
                self.stats['checked'] += 1
                
                if result.available:
                    self.stats['available'] += 1
                    print(f"[HIT] 🎯 {result.username} AVAILABLE! (status: {result.error or 'clean'})")
                    if self.webhook:
                        if self.mode == "monitor":
                            await self.webhook.notify_watchlist_hit(result.username)
                        else:
                            await self.webhook.notify_hit(result)
                elif result.error and result.error not in ('taken', 'invalid'):
                    self.stats['errors'] += 1
                
                if self.stats['checked'] % 100 == 0:
                    elapsed = time.time() - self.stats['start_time']
                    rate = self.stats['checked'] / elapsed
                    hits = self.stats['available']
                    proxies = len(self.proxy_harvester.working_proxies)
                    print(f"[PROGRESS] {self.stats['checked']}/{total} | {rate:.1f}/s | Hits: {hits} | Proxies: {proxies}")
                    
                    if self.webhook and self.stats['checked'] % 500 == 0:
                        await self.webhook.notify_progress(
                            self.stats['checked'], total, hits, elapsed, proxies)
        
        elapsed = time.time() - self.stats['start_time']
        print(f"[DONE] {self.stats['checked']} checked | {self.stats['available']} hits | {self.stats['errors']} errors | {elapsed:.1f}s")
        
        if self.webhook:
            await self.webhook.notify_complete(
                self.stats['checked'], self.stats['available'], elapsed, self.stats['errors'])
        
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
            print(f"[SAVE] {len(available)} hits written to results/")
