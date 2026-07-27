import aiohttp

class WebhookNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()
    
    async def _send(self, payload: dict) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=8)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as resp:
                    print(f"[WEBHOOK] Sent, status: {resp.status}")
                    return resp.status in (200, 204)
        except Exception as e:
            print(f"[WEBHOOK] Send failed: {e}")
            return False
    
    async def notify_start(self, total, concurrency, length, pattern, proxy_count):
        await self._send({
            "username": "Hunter Bot",
            "embeds": [{
                "title": "🟡 Hunter Started",
                "color": 0xffaa00,
                "fields": [
                    {"name": "Usernames", "value": str(total), "inline": True},
                    {"name": "Concurrency", "value": str(concurrency), "inline": True},
                    {"name": "Length", "value": length, "inline": True}
                ]
            }]
        })
    
    async def notify_proxies_ready(self, working, best_latency):
        await self._send({
            "username": "Hunter Bot",
            "embeds": [{
                "title": "🟢 Proxies Ready",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Working", "value": str(working), "inline": True},
                    {"name": "Best Latency", "value": f"{best_latency:.2f}s", "inline": True}
                ]
            }]
        })
    
    async def notify_progress(self, checked, total, hits, elapsed, proxies_alive):
        percent = (checked / total) * 100 if total > 0 else 0
        await self._send({
            "username": "Hunter Bot",
            "embeds": [{
                "title": "🔵 Progress",
                "description": f"{percent:.1f}% complete",
                "color": 0x0099ff,
                "fields": [
                    {"name": "Checked", "value": f"{checked}/{total}", "inline": True},
                    {"name": "Hits", "value": str(hits), "inline": True},
                    {"name": "Proxies", "value": str(proxies_alive), "inline": True}
                ]
            }]
        })
    
    async def notify_hit(self, result):
        await self._send({
            "username": "Hunter Bot",
            "embeds": [{
                "title": "🎯 HIT!",
                "description": f"`{result.username}` is available!",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Time", "value": f"{result.response_time:.2f}s", "inline": True}
                ]
            }]
        })
    
    async def notify_complete(self, checked, hits, elapsed, errors):
        await self._send({
            "username": "Hunter Bot",
            "embeds": [{
                "title": "🏁 Complete",
                "color": 0x00ff00 if hits > 0 else 0xff5555,
                "fields": [
                    {"name": "Checked", "value": str(checked), "inline": True},
                    {"name": "Hits", "value": str(hits), "inline": True},
                    {"name": "Duration", "value": f"{elapsed/60:.1f}m", "inline": True}
                ]
            }]
        })
