#!/usr/bin/env python3
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.monitor import UsernameMonitor
from src.username_gen import UsernameGenerator

async def main():
    # Get token from environment
    token = os.environ.get('DISCORD_TOKEN', '')
    if not token:
        print("❌ DISCORD_TOKEN not set! Set it in GitHub Secrets.")
        return 1

    webhook = os.environ.get('WEBHOOK_URL', '')
    interval = int(os.environ.get('MONITOR_INTERVAL', '30'))

    # Load watchlist
    watchlist = UsernameGenerator.from_file('watchlist.txt')
    if not watchlist:
        print("❌ watchlist.txt is empty! Add usernames to monitor.")
        return 1

    print(f"👁️  Starting monitor for {len(watchlist)} usernames")
    print(f"⏰ Interval: {interval} minutes")
    print(f"🐌 Speed: 2-4 seconds between checks (human-like)")

    monitor = UsernameMonitor(token, webhook, interval)
    await monitor.run(watchlist)
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
