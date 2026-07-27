import asyncio
import aiohttp
import random
import time
import json
import os
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from .proxy_harvester import ProxyHarvester, Proxy
from .discord_webhook import WebhookNotifier

logger = logging.getLogger("checker")

DISCORD_API = "https://discord.com/api/v9/users/@me"
DISCORD_REGISTER_CHECK = "https://discord.com/api/v9/auth/register"  # Username availability endpoint

@dataclass
class CheckResult:
    username: str
    available: bool
    checked_at: str
    proxy_used: Optional[str] = None
    response_time: float = 0.0
    error: Optional[str] = None

class DiscordUsernameChecker:
    def __init__(
        self,
        concurrency: int = 50,
        timeout: int = 10,
        delay_between: float = 0.5,
        webhook_url: Optional[str] = None,
        proxy_harvester: Optional[ProxyHarvester] = None
    ):
        self.concurrency = concurrency
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.delay_between = delay_between
        self.webhook = WebhookNotifier(webhook_url) if webhook_url else None
        self.proxy_harvester = proxy_harvester or ProxyHarvester()
        self.semaphore = asyncio.Semaphore(concurrency)
        self.results: List[CheckResult] = []
        self.stats = {
            'checked': 0,
            'available': 0,
            'taken': 0,
            'errors': 0,
            'start_time': None
        }
        
    async def check_username(self, session: aiohttp.ClientSession, username: str) -> CheckResult:
        """Check if a username is available."""
        async with self.semaphore:
            start = time.time()
            proxy = self.proxy_harvester.get_proxy()
            proxy_str = str(proxy) if proxy else None
            
            try:
                # Discord's username availability check
                # We use the register endpoint with a preflight check
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
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
                
                request_kwargs = {
                    'headers': headers,
                    'json': payload,
                    'timeout': self.timeout,
                    'ssl': False
                }
                
                if proxy and proxy.protocol in ('http', 'https'):
                    request_kwargs['proxy'] = proxy_str
                
                elif proxy and proxy.protocol in ('socks4', 'socks5'):
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(proxy_str)
                    async with aiohttp.ClientSession(connector=connector) as sock_session:
                        async with sock_session.post(
                            "https://discord.com/api/v9/auth/register",
                            **{k: v for k, v in request_kwargs.items() if k != 'proxy'}
                        ) as resp:
                            response_time = time.time() - start
                            return self._parse_response(username, resp, response_time, proxy_str)
                
                async with session.post(
                    "https://discord.com/api/v9/auth/register",
                    **request_kwargs
                ) as resp:
                    response_time = time.time() - start
                    return self._parse_response(username, resp, response_time, proxy_str)
                    
            except asyncio.TimeoutError:
                if proxy:
                    self.proxy_harvester.mark_dead(proxy)
                return CheckResult(username, False, datetime.now().isoformat(), proxy_str, time.time() - start, "timeout")
            except Exception as e:
                if proxy and 'proxy' in str(e).lower():
                    self.proxy_harvester.mark_dead(proxy)
                return CheckResult(username, False, datetime.now().isoformat(), proxy_str, time.time() - start, str(e))
            
            finally:
                # Adaptive delay with jitter
                jitter = random.uniform(0.8, 1.2)
                await asyncio.sleep(self.delay_between * jitter)
    
    def _parse_response(self, username: str, resp: aiohttp.ClientResponse, response_time: float, proxy_str: Optional[str]) -> CheckResult:
        """Parse Discord API response."""
        timestamp = datetime.now().isoformat()
        
        if resp.status == 400:
            try:
                data = resp.json()
                errors = data.get('errors', {})
                # Username taken or invalid
                if 'username' in errors:
                    return CheckResult(username, False, timestamp, proxy_str, response_time)
            except:
                pass
            return CheckResult(username, False, timestamp, proxy_str, response_time, "bad_request")
        
        elif resp.status == 429:
            # Rate limited - mark proxy as potentially dead
            return CheckResult(username, False, timestamp, proxy_str, response_time, "rate_limited")
        
        elif resp.status in (200, 201, 204):
            # Success - username might be available
            # Actually, Discord returns 200 with errors object for taken usernames
            # 400 with username_errors = taken
            # Need to check the actual response body
            return CheckResult(username, True, timestamp, proxy_str, response_time)
        
        elif resp.status == 403:
            return CheckResult(username, False, timestamp, proxy_str, response_time, "forbidden")
        
        else:
            return CheckResult(username, False, timestamp, proxy_str, response_time, f"status_{resp.status}")
    
    async def run(self, usernames: List[str]) -> List[CheckResult]:
        """Run the checker against a list of usernames."""
        self.stats['start_time'] = time.time()
        logger.info(f"🚀 Starting check of {len(usernames)} usernames @ {self.concurrency} concurrency")
        
        # Harvest proxies first (Step 1 - auto)
        if not self.proxy_harvester.working_proxies:
            await self.proxy_harvester.harvest()
        
        if not self.proxy_harvester.working_proxies:
            logger.error("❌ No working proxies! Cannot continue.")
            return []
        
        connector = aiohttp.TCPConnector(limit=self.concurrency * 2, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.check_username(session, u) for u in usernames]
            
            for completed in asyncio.as_completed(tasks):
                result = await completed
                self.results.append(result)
                self.stats['checked'] += 1
                
                if result.available:
                    self.stats['available'] += 1
                    logger.info(f"🎯 HIT: {result.username} is AVAILABLE!")
                    if self.webhook:
                        await self.webhook.notify_hit(result)
                elif result.error:
                    self.stats['errors'] += 1
                else:
                    self.stats['taken'] += 1
                
                # Progress every 50
                if self.stats['checked'] % 50 == 0:
                    elapsed = time.time() - self.stats['start_time']
                    rate = self.stats['checked'] / elapsed
                    logger.info(f"📊 Progress: {self.stats['checked']}/{len(usernames)} | {rate:.1f}/s | Hits: {self.stats['available']} | Proxies: {len(self.proxy_harvester.working_proxies)}")
        
        # Final stats
        elapsed = time.time() - self.stats['start_time']
        logger.info(f"🏁 Done! Checked {self.stats['checked']} in {elapsed:.1f}s | Hits: {self.stats['available']} | Errors: {self.stats['errors']}")
        
        # Save results
        self._save_results()
        return self.results
    
    def _save_results(self):
        """Save results to file."""
        os.makedirs('results', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # All results
        with open(f'results/check_{timestamp}.json', 'w') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        
        # Available only
        available = [r for r in self.results if r.available]
        if available:
            with open(f'results/hits_{timestamp}.txt', 'w') as f:
                for r in available:
                    f.write(f"{r.username}\n")
            with open('results/all_hits.txt', 'a') as f:
                for r in available:
                    f.write(f"{r.username}\n")