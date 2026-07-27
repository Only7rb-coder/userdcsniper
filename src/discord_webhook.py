import aiohttp

class WebhookNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip() if webhook_url else ""
    
    async def _send(self, payload: dict) -> bool:
        if not self.webhook_url.startswith('http'):
            return False
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    return resp.status in (200, 204)
        except Exception as e:
            print(f"[WEBHOOK] Send failed: {str(e)[:80]}")
            return False
    
    async def notify_start(self, total, concurrency, length, pattern, proxy_count, mode):
        await self._send({
            "username": "Hunter",
            "embeds": [{
                "title": "🟡 Hunt Started",
                "color": 0xffaa00,
                "fields": [
                    {"name": "Mode", "value": mode, "inline": True},
                    {"name": "Usernames", "value": str(total), "inline": True},
                    {"name": "Concurrency", "value": str(concurrency), "inline": True},
                    {"name": "Length", "value": length, "inline": True},
                    {"name": "Pattern", "value": pattern, "inline": True},
                    {"name": "Proxies", "value": str(proxy_count), "inline": True}
                ]
            }]
        })
    
    async def notify_proxies_ready(self, working, best):
        await self._send({
            "username": "Hunter",
            "embeds": [{
                "title": "🟢 Proxies Ready",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Working", "value": str(working), "inline": True},
                    {"name": "Best", "value": f"{best:.2f}s", "inline": True}
                ]
            }]
        })
    
    async def notify_hit(self, result):
        await self._send({
            "username": "Hunter",
            "embeds": [{
                "title": "🎯 HIT!",
                "description": f"`{result.username}` is **AVAILABLE**!",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Response", "value": f"{result.response_time:.2f}s", "inline": True},
                    {"name": "Proxy", "value": result.proxy_used or "Direct", "inline": True}
                ]
            }]
        })
    
    async def notify_progress(self, checked, total, hits, elapsed, proxies_alive):
        pct = (checked / total) * 100 if total else 0
        await self._send({
            "username": "Hunter",
            "embeds": [{
                "title": "🔵 Progress",
                "description": f"{pct:.1f}% | {checked}/{total}",
                "color": 0x0099ff,
                "fields": [
                    {"name": "Hits", "value": str(hits), "inline": True},
                    {"name": "Rate", "value": f"{checked/elapsed:.1f}/s", "inline": True},
                    {"name": "Proxies", "value": str(proxies_alive), "inline": True}
                ]
            }]
        })
    
    async def notify_watchlist_hit(self, username):
        await self._send({
            "username": "Hunter",
            "embeds": [{
                "title": "👁️ WATCHLIST DROP!",
                "description": f"`{username}` just became **AVAILABLE**!",
                "color": 0xff00ff,
                "fields": [
                    {"name": "Action", "value": "Claim it NOW!", "inline": False}
                ]
            }]
        })
    
    async def notify_complete(self, checked, hits, elapsed, errors):
        await self._send({
            "username": "Hunter",
            "embeds": [{
                "title": "🏁 Complete",
                "color": 0x00ff00 if hits > 0 else 0xff5555,
                "fields": [
                    {"name": "Checked", "value": str(checked), "inline": True},
                    {"name": "Hits", "value": f"🎯 {hits}", "inline": True},
                    {"name": "Time", "value": f"{elapsed/60:.1f}m", "inline": True}
                ]
            }]
        })
    
    async def notify_error(self, error_msg):
        await self._send({
            "username": "Hunter",
            "embeds": [{
                "title": "🔴 Error",
                "description": f"```{error_msg[:900]}```",
                "color": 0xff0000
            }]
        })
