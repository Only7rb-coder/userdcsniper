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
    verified: bool = False  # Double-checked hit

class DiscordUsernameChecker:
    def __init__(self, concurrency=50, timeout=10, delay_between=0.5, 
                 webhook_url=None, proxy_harvester=None, mode="hunt"):
        self.concurrency = concurrency
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.delay_between = delay_between
        self.mode = mode
        
        self.webhook = None
        if webhook_url and webhook_url.strip().startswith('http'):
            self.webhook = WebhookNotifier(webhook_url.strip())
            print(f"[WEBHOOK] Enabled")
        else:
            print(f"[WEBHOOK] Disabled")
            
        self.proxy_harvester = proxy_harvester or ProxyHarvester()
        self.semaphore = asyncio.Semaphore(concurrency)
        self.results = []
        self.stats = {'checked': 0, 'available': 0, 'verified_hits': 0, 'errors': 0, 'start_time': None}
        
    async def _do_check(self, session: aiohttp.ClientSession, username: str, proxy: Optional[Proxy]) -> tuple:
        """Single check request. Returns (status, body_dict, response_time)"""
        proxy_str = str(proxy) if proxy else None
        start = time.time()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
            'Origin': 'https://discord.com',
            'Referer': 'https://discord.com/register',
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
        
        try:
            async with session.post(
                "https://discord.com/api/v9/auth/register", 
                **kwargs
            ) as resp:
                response_time = time.time() - start
                body = {}
                try:
                    body = await resp.json()
                except:
                    pass
                return resp.status, body, response_time, proxy_str
                
        except asyncio.TimeoutError:
            if proxy:
                self.proxy_harvester.mark_dead(proxy)
            return -1, {}, time.time() - start, proxy_str
        except Exception as e:
            if proxy and 'proxy' in str(e).lower():
                self.proxy_harvester.mark_dead(proxy)
            return -2, {}, time.time() - start, proxy_str
    
    async def check_username(self, session: aiohttp.ClientSession, username: str) -> CheckResult:
        async with self.semaphore:
            timestamp = datetime.now().isoformat()
            
            # First check
            status1, body1, rt1, proxy_str = await self._do_check(session, username, self.proxy_harvester.get_proxy())
            
            # Parse first response
            if status1 == 200:
                # Potential hit! But need to verify - Discord sometimes returns 200 for invalid names
                # Wait a moment and check again with different proxy
                await asyncio.sleep(random.uniform(0.5, 1.5))
                status2, body2, rt2, _ = await self._do_check(session, username, self.proxy_harvester.get_proxy())
                
                if status2 == 200:
                    # DOUBLE VERIFIED HIT
                    return CheckResult(username, True, timestamp, proxy_str, rt1, None, True)
                else:
                    # First was a fluke
                    return CheckResult(username, False, timestamp, proxy_str, rt1, f"unverified_200_second_{status2}", False)
            
            elif status1 == 400:
                errors = body1.get('errors', {})
                username_errors = errors.get('username', {})
                
                if username_errors:
                    error_str = str(username_errors).lower()
                    if 'already' in error_str or 'taken' in error_str:
                        return CheckResult(username, False, timestamp, proxy_str, rt1, "taken")
                    else:
                        return CheckResult(username, False, timestamp, proxy_str, rt1, "invalid")
                else:
                    # 400 with no username error = might be available but blocked
                    return CheckResult(username, False, timestamp, proxy_str, rt1, "blocked")
            
            elif status1 == 429:
                return CheckResult(username, False, timestamp, proxy_str, rt1, "rate_limited")
            
            elif status1 == -1:
                return CheckResult(username, False, timestamp, proxy_str, rt1, "timeout")
            
            elif status1 == -2:
                return CheckResult(username, False, timestamp, proxy_str, rt1, "request_error")
            
            else:
                return CheckResult(username, False, timestamp, proxy_str, rt1, f"status_{status1}")
            
            finally:
                await asyncio.sleep(self.delay_between * random.uniform(0.8, 1.2))
    
    async def run(self, usernames: List[str]) -> List[CheckResult]:
        self.stats['start_time'] = time.time()
        total = len(usernames)
        
        print(f"[CHECK] Mode: {self.mode} | {total} usernames | {self.concurrency} concurrency")
        print(f"[CHECK] First 5 usernames: {usernames[:5]}")
        
        if self.webhook:
            await self.webhook.notify_start(total, self.concurrency,
                os.environ.get('LENGTH', '5-7'),
                os.environ.get('PATTERN', 'mixed'),
                len(self.proxy_harvester.working_proxies),
                self.mode)
        
        if not self.proxy_harvester.working_proxies:
            await self.proxy_harvester.harvest()
        
        if not self.proxy_harvester.working_proxies:
            print("[CHECK] ⚠️ No proxies! Running direct...")
        
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
                    if result.verified:
                        self.stats['verified_hits'] += 1
                        print(f"[HIT] 🎯✅ VERIFIED: {result.username} is AVAILABLE!")
                        if self.webhook:
                            if self.mode == "monitor":
                                await self.webhook.notify_watchlist_hit(result.username)
                            else:
                                await self.webhook.notify_hit(result)
                    else:
                        print(f"[HIT] ⚠️ UNVERIFIED: {result.username} (first 200, second failed)")
                
                elif result.error and result.error not in ('taken', 'invalid', 'blocked'):
                    self.stats['errors'] += 1
                
                if self.stats['checked'] % 100 == 0:
                    elapsed = time.time() - self.stats['start_time']
                    rate = self.stats['checked'] / elapsed
                    hits = self.stats['verified_hits']
                    proxies = len(self.proxy_harvester.working_proxies)
                    print(f"[PROGRESS] {self.stats['checked']}/{total} | {rate:.1f}/s | Verified Hits: {hits} | Proxies: {proxies}")
                    
                    if self.webhook and self.stats['checked'] % 500 == 0:
                        await self.webhook.notify_progress(
                            self.stats['checked'], total, hits, elapsed, proxies)
        
        elapsed = time.time() - self.stats['start_time']
        print(f"[DONE] {self.stats['checked']} checked | {self.stats['verified_hits']} verified hits | {self.stats['errors']} errors | {elapsed:.1f}s")
        
        if self.webhook:
            await self.webhook.notify_complete(
                self.stats['checked'], self.stats['verified_hits'], elapsed, self.stats['errors'])
        
        self._save_results()
        return self.results
    
    def _save_results(self):
        os.makedirs('results', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with open(f'results/check_{timestamp}.json', 'w') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        
        verified = [r for r in self.results if r.available and r.verified]
        if verified:
            with open(f'results/hits_{timestamp}.txt', 'w') as f:
                for r in verified:
                    f.write(f"{r.username}\n")
            with open('results/all_hits.txt', 'a') as f:
                for r in verified:
                    f.write(f"{r.username}\n")
            print(f"[SAVE] {len(verified)} VERIFIED hits written to results/")
