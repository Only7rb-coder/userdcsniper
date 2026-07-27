import aiohttp

class WebhookNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip() if webhook_url else ""

    async def send(self, title: str, description: str, color: int = 0x0099ff, fields: list = None):
        if not self.webhook_url.startswith('http'):
            return False

        embed = {
            "title": title,
            "description": description,
            "color": color
        }
        if fields:
            embed["fields"] = fields

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(self.webhook_url, json={
                    "username": "Username Monitor",
                    "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png",
                    "embeds": [embed]
                }) as resp:
                    return resp.status in (200, 204)
        except Exception as e:
            print(f"[WEBHOOK] Failed: {e}")
            return False

    async def notify_available(self, username: str, method: str):
        await self.send(
            "🎯 USERNAME AVAILABLE!",
            f"`{username}` is **confirmed available**!",
            0x00ff00,
            [
                {"name": "Method", "value": method, "inline": True},
                {"name": "Action", "value": "Claim it now!", "inline": True}
            ]
        )

    async def notify_start(self, count: int, interval: int):
        await self.send(
            "🟡 Monitor Started",
            f"Watching {count} usernames every {interval} minutes",
            0xffaa00
        )

    async def notify_cycle(self, checked: int, available: int, errors: int):
        await self.send(
            "🔵 Cycle Complete",
            f"Checked {checked} usernames",
            0x0099ff,
            [
                {"name": "Available", "value": str(available), "inline": True},
                {"name": "Errors", "value": str(errors), "inline": True}
            ]
        )
