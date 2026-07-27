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
        print("   Repo Settings → Secrets and variables → Actions → New repository secret")
        print("   Name: DISCORD_TOKEN")
        return 1

    webhook = os.environ.get('WEBHOOK_URL', '')
    interval = int(os.environ.get('MONITOR_INTERVAL', '30'))

    # Load watchlist
    watchlist = UsernameGenerator.from_file('watchlist.txt')

    # Generate additional candidates if requested
    mode = os.environ.get('GEN_MODE', 'none')  # none, short, words, mixed, leet
    gen_count = int(os.environ.get('GEN_COUNT', '0'))
    gen_length = os.environ.get('GEN_LENGTH', '5-7')

    if mode != 'none' and gen_count > 0:
        print(f"🎲 Generating {gen_count} usernames (mode: {mode}, length: {gen_length})...")
        generated = list(UsernameGenerator.generate(gen_count, mode, gen_length))
        watchlist.extend(generated)
        watchlist = list(dict.fromkeys(watchlist))  # Remove duplicates
        print(f"   Added {len(generated)} generated names")

    if not watchlist:
        print("❌ No usernames to monitor!")
        print("   Add names to watchlist.txt or enable generation")
        return 1

    print(f"👁️  Starting monitor for {len(watchlist)} usernames")
    print(f"⏰ Interval: {interval} minutes")
    print(f"🐌 Speed: 2-4 seconds between checks (human-like)")
    print(f"🔒 Token: {token[:10]}... (hidden)")

    monitor = UsernameMonitor(token, webhook, interval)
    await monitor.run(watchlist)
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
