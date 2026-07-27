import aiohttp
import json
from typing import Optional
from dataclasses import asdict

class WebhookNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def notify_hit(self, result):
        """Send Discord webhook notification for available username."""
        embed = {
            "title": "🎯 Username Available!",
            "description": f"**{result.username}** is up for grabs!",
            "color": 0x00ff00,
            "fields": [
                {"name": "Response Time", "value": f"{result.response_time:.2f}s", "inline": True},
                {"name": "Proxy", "value": result.proxy_used or "Direct", "inline": True},
                {"name": "Checked At", "value": result.checked_at, "inline": True}
            ],
            "footer": {"text": "Discord Username Hunter"}
        }
        
        payload = {
            "username": "Username Hunter",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
            "embeds": [embed]
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as resp:
                    return resp.status == 204
        except Exception as e:
            print(f"Webhook failed: {e}")
            return False