import aiohttp

class WebhookNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    async def notify_hit(self, result):
        embed = {
            "title": "🎯 Username Available!",
            "description": f"**{result.username}** is up for grabs!",
            "color": 0x00ff00,
            "fields": [
                {"name": "Response Time", "value": f"{result.response_time:.2f}s", "inline": True},
                {"name": "Proxy", "value": result.proxy_used or "Direct", "inline": True}
            ],
            "footer": {"text": "Username Hunter"}
        }
        
        payload = {
            "username": "Username Hunter",
            "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
            "embeds": [embed]
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    return resp.status == 204
        except Exception:
            return False
