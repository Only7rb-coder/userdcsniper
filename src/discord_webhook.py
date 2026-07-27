import aiohttp
import json
from typing import Optional
from dataclasses import asdict

class WebhookNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def _send(self, payload: dict) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as resp:
                    return resp.status in (200, 204)
        except Exception:
            return False
    
    async def notify_start(self, total: int, concurrency: int, length: str, pattern: str, proxy_count: int):
        embed = {
            "title": "🟡 Hunter Started",
            "description": f"Username hunt initiated on GitHub Actions",
            "color": 0xffaa00,
            "fields": [
                {"name": "Total Usernames", "value": str(total), "inline": True},
                {"name": "Concurrency", "value": str(concurrency), "inline": True},
                {"name": "Length", "value": length, "inline": True},
                {"name": "Pattern", "value": pattern, "inline": True},
                {"name": "Proxies", "value": str(proxy_count), "inline": True},
                {"name": "Status", "value": "Harvesting proxies...", "inline": True}
            ],
            "footer": {"text": "Discord Username Hunter | ENI for LO"}
        }
        await self._send({"username": "Hunter Bot", "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png", "embeds": [embed]})
    
    async def notify_proxies_ready(self, working: int, best_latency: float):
        embed = {
            "title": "🟢 Proxies Ready",
            "description": f"Proxy harvest complete. {working} proxies responding.",
            "color": 0x00ff00,
            "fields": [
                {"name": "Working Proxies", "value": str(working), "inline": True},
                {"name": "Best Latency", "value": f"{best_latency:.2f}s", "inline": True}
            ],
            "footer": {"text": "Hunter Bot"}
        }
        await self._send({"username": "Hunter Bot", "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png", "embeds": [embed]})
    
    async def notify_progress(self, checked: int, total: int, hits: int, elapsed: float, proxies_alive: int):
        percent = (checked / total) * 100 if total > 0 else 0
        rate = checked / elapsed if elapsed > 0 else 0
        eta = (total - checked) / rate if rate > 0 else 0
        
        embed = {
            "title": "🔵 Progress Update",
            "description": f"{'█' * int(percent/5)}{'░' * (20-int(percent/5))} {percent:.1f}%",
            "color": 0x0099ff,
            "fields": [
                {"name": "Checked", "value": f"{checked}/{total}", "inline": True},
                {"name": "Hits", "value": f"🎯 {hits}", "inline": True},
                {"name": "Rate", "value": f"{rate:.1f}/s", "inline": True},
                {"name": "Elapsed", "value": f"{elapsed/60:.1f}m", "inline": True},
                {"name": "ETA", "value": f"{eta/60:.1f}m", "inline": True},
                {"name": "Proxies", "value": str(proxies_alive), "inline": True}
            ],
            "footer": {"text": "Hunter Bot"}
        }
        await self._send({"username": "Hunter Bot", "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png", "embeds": [embed]})
    
    async def notify_hit(self, result):
        embed = {
            "title": "🎯 HIT — Username Available!",
            "description": f"**`{result.username}`** is up for grabs!",
            "color": 0x00ff00,
            "fields": [
                {"name": "Response Time", "value": f"{result.response_time:.2f}s", "inline": True},
                {"name": "Proxy", "value": result.proxy_used or "Direct", "inline": True},
                {"name": "Checked At", "value": result.checked_at[:19], "inline": True}
            ],
            "footer": {"text": "Claim it before someone else does!"}
        }
        await self._send({"username": "Hunter Bot", "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png", "embeds": [embed]})
    
    async def notify_complete(self, checked: int, hits: int, elapsed: float, errors: int):
        embed = {
            "title": "🏁 Hunt Complete",
            "description": f"Finished checking {checked} usernames",
            "color": 0x00ff00 if hits > 0 else 0xff5555,
            "fields": [
                {"name": "Total Checked", "value": str(checked), "inline": True},
                {"name": "Hits Found", "value": f"🎯 {hits}", "inline": True},
                {"name": "Errors", "value": str(errors), "inline": True},
                {"name": "Duration", "value": f"{elapsed/60:.1f} minutes", "inline": True},
                {"name": "Rate", "value": f"{checked/elapsed:.1f}/s", "inline": True}
            ],
            "footer": {"text": "Download results artifact for full list"}
        }
        await self._send({"username": "Hunter Bot", "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png", "embeds": [embed]})
    
    async def notify_error(self, error_msg: str):
        embed = {
            "title": "🔴 Hunter Error",
            "description": f"```{error_msg[:1000]}```",
            "color": 0xff0000,
            "footer": {"text": "Check Actions logs for details"}
        }
        await self._send({"username": "Hunter Bot", "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png", "embeds": [embed]})
