import asyncio
import aiohttp
import os
import json
import time
import random
from datetime import datetime
from typing import List, Dict

from .discord_api import DiscordAPI
from .webhook import WebhookNotifier

class UsernameMonitor:
    def __init__(self, token: str, webhook_url: str, interval_minutes: int = 30):
        self.token = token
        self.webhook = WebhookNotifier(webhook_url)
        self.interval = interval_minutes * 60  # seconds
        self.known_available: set = set()
        self.load_state()

    def load_state(self):
        """Load previously found available usernames to avoid re-notifying"""
        if os.path.exists('results/known_available.json'):
            try:
                with open('results/known_available.json', 'r') as f:
                    self.known_available = set(json.load(f))
            except:
                pass

    def save_state(self):
        os.makedirs('results', exist_ok=True)
        with open('results/known_available.json', 'w') as f:
            json.dump(list(self.known_available), f)

    async def check_single(self, api: DiscordAPI, username: str) -> Dict:
        """Check one username. Slow and careful."""
        result = await api.lookup_user(username)

        # Parse result
        status = result.get("status")
        body = result.get("body", {})

        if status == 200:
            # 200 on register = might be available
            # But we need to be sure — check if there's any error in body
            errors = body.get("errors", {})
            if not errors:
                return {"available": True, "username": username, "confidence": "high"}
            else:
                return {"available": False, "username": username, "reason": "has_errors"}

        elif status == 400:
            errors = body.get("errors", {})
            username_errors = errors.get("username", {})
            if username_errors:
                return {"available": False, "username": username, "reason": "taken"}
            return {"available": False, "username": username, "reason": "blocked"}

        elif status == 429:
            return {"available": False, "username": username, "reason": "rate_limited"}

        elif "error" in result:
            return {"available": False, "username": username, "reason": result["error"]}

        return {"available": False, "username": username, "reason": f"status_{status}"}

    async def run_cycle(self, usernames: List[str]):
        """Run one monitoring cycle"""
        print(f"\n{","*60}")
        print(f"👁️  MONITOR CYCLE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{","*60}")

        async with DiscordAPI(self.token) as api:
            available_count = 0
            error_count = 0
            new_hits = []

            for i, username in enumerate(usernames):
                result = await self.check_single(api, username)

                if result.get("available"):
                    available_count += 1
                    if username not in self.known_available:
                        self.known_available.add(username)
                        new_hits.append(username)
                        print(f"🎯 NEW HIT: {username}")
                        await self.webhook.notify_available(username, "register_endpoint")
                    else:
                        print(f"✓ Still available: {username}")

                elif result.get("reason") in ("rate_limited", "timeout", "request_error"):
                    error_count += 1
                    print(f"⚠️  Error on {username}: {result['reason']}")

                else:
                    # Taken or invalid — expected
                    if i % 100 == 0:
                        print(f"  Checked {i+1}/{len(usernames)}...")

                # HUMAN DELAY — this is the key
                # 2-4 seconds between checks, never faster
                await asyncio.sleep(random.uniform(2.0, 4.0))

            self.save_state()

            print(f"\nCycle complete: {available_count} available, {error_count} errors, {len(new_hits)} new hits")

            if new_hits or error_count > 5:
                await self.webhook.notify_cycle(len(usernames), len(new_hits), error_count)

    async def run(self, usernames: List[str]):
        """Run monitor indefinitely"""
        await self.webhook.notify_start(len(usernames), self.interval // 60)

        while True:
            await self.run_cycle(usernames)

            next_check = datetime.now().timestamp() + self.interval
            print(f"\n⏳ Next check at {datetime.fromtimestamp(next_check).strftime('%H:%M:%S')}")
            await asyncio.sleep(self.interval)
