import aiohttp
import asyncio
from typing import Optional, Dict, Any

class DiscordAPI:
    """Real Discord API client using bot token"""

    def __init__(self, token: str):
        self.token = token.strip()
        self.base_url = "https://discord.com/api/v9"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bot {self.token}",
                "User-Agent": "DiscordBot (https://github.com/Only7rb-coder/userdcsniper, 1.0)",
                "Content-Type": "application/json"
            }
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def lookup_user(self, username: str) -> Dict[str, Any]:
        """
        Check if a username exists by searching for it.
        Returns user data if found, None if not found (potentially available).
        """
        try:
            # First verify our token works
            async with self.session.get(
                f"{self.base_url}/users/@me",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 401:
                    return {"error": "invalid_token"}

            # Use registration endpoint with bot token context
            headers = {
                "Authorization": f"Bot {self.token}",
                "Content-Type": "application/json",
                "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIn0="
            }

            payload = {
                "username": username,
                "consent": True,
                "date_of_birth": "1990-01-01",
                "gift_code_sku_id": None,
                "captcha_key": None
            }

            async with self.session.post(
                f"{self.base_url}/auth/register",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                body = {}
                try:
                    body = await resp.json()
                except:
                    pass

                return {
                    "status": resp.status,
                    "body": body,
                    "username": username
                }

        except asyncio.TimeoutError:
            return {"error": "timeout", "username": username}
        except Exception as e:
            return {"error": str(e)[:100], "username": username}

    async def check_username_availability(self, username: str) -> Dict[str, Any]:
        """
        More reliable check using Discord's username change endpoint.
        Requires the token to have proper permissions.
        """
        try:
            payload = {"username": username}

            async with self.session.patch(
                f"{self.base_url}/users/@me",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                body = {}
                try:
                    body = await resp.json()
                except:
                    pass

                if resp.status == 200:
                    return {"available": True, "method": "patch", "username": username}

                elif resp.status == 400:
                    errors = body.get("errors", {})
                    if "username" in errors:
                        return {"available": False, "reason": "taken_or_invalid", "username": username}
                    return {"available": False, "reason": "other_error", "body": body, "username": username}

                elif resp.status == 429:
                    return {"available": False, "reason": "rate_limited", "username": username}

                else:
                    return {"available": False, "reason": f"status_{resp.status}", "username": username}

        except asyncio.TimeoutError:
            return {"available": False, "reason": "timeout", "username": username}
        except Exception as e:
            return {"available": False, "reason": str(e)[:100], "username": username}
