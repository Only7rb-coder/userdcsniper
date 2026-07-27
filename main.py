#!/usr/bin/env python3
import asyncio
import sys
import os
import yaml
import logging
from pathlib import Path

from src.checker import DiscordUsernameChecker
from src.proxy_harvester import ProxyHarvester
from src.username_gen import UsernameGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

def print_banner():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║           DISCORD USERNAME HUNTER v2.0                   ║
    ║              by ENI for LO 💜                            ║
    ╚══════════════════════════════════════════════════════════╝
    """)

def get_input_mode() -> str:
    """○ Usernames — (f)ile or (g)enerate, just press a key"""
    while True:
        print("\n📋 USERNAME SOURCE")
        print("   [f] Load from file (usernames.txt)")
        print("   [g] Generate automatically")
        print("   [b] Both (file + generated)")
        key = input("   Press a key: ").strip().lower()
        if key in ('f', 'g', 'b'):
            return key
        print("   Invalid key. Try again.")

def get_speed_config() -> tuple:
    """○ Speed — concurrency + timeout"""
    print("\n⚡ SPEED CONFIGURATION")
    
    print("   Concurrency (simultaneous checks):")
    print("   [1] Low    - 10  (safe, slow)")
    print("   [2] Medium - 50  (balanced)")
    print("   [3] High   - 100 (aggressive)")
    print("   [4] Custom")
    
    while True:
        c = input("   Select [1-4]: ").strip()
        if c == '1': concurrency = 10
        elif c == '2': concurrency = 50
        elif c == '3': concurrency = 100
        elif c == '4': concurrency = int(input("   Enter number: "))
        else: continue
        break
    
    print("\n   Timeout per request (seconds):")
    print("   [1] Fast   - 5s")
    print("   [2] Normal - 10s")
    print("   [3] Slow   - 20s")
    
    while True:
        t = input("   Select [1-3]: ").strip()
        if t == '1': timeout = 5
        elif t == '2': timeout = 10
        elif t == '3': timeout = 20
        else: continue
        break
    
    print(f"\n   Config: {concurrency} concurrent, {timeout}s timeout")
    return concurrency, timeout

def get_webhook() -> Optional[str]:
    """○ Webhook — optional Discord notifications"""
    print("\n🔔 DISCORD WEBHOOK (optional)")
    url = input("   Enter webhook URL (or press Enter to skip): ").strip()
    return url if url else None

def load_config() -> dict:
    """Load or create config."""
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    return {}

def save_config(config: dict):
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

async def main():
    print_banner()
    
    # Step 1: Auto-run proxy harvest (no user input needed)
    print("🔌 Step 1: Harvesting free proxies...")
    harvester = ProxyHarvester(max_proxies=200)
    await harvester.harvest()
    
    if not harvester.working_proxies:
        print("❌ No working proxies found. Check your connection.")
        return 1
    
    print(f"✅ Step 1 complete: {len(harvester.working_proxies)} proxies ready\n")
    
    # Step 2: User inputs
    mode = get_input_mode()
    concurrency, timeout = get_speed_config()
    webhook = get_webhook()
    
    # Build username list
    usernames = []
    
    if mode in ('f', 'b'):
        if os.path.exists('usernames.txt'):
            file_names = UsernameGenerator.from_file('usernames.txt')
            usernames.extend(file_names)
            print(f"📁 Loaded {len(file_names)} usernames from file")
        else:
            print("⚠️ usernames.txt not found, creating...")
            Path('usernames.txt').touch()
    
    if mode in ('g', 'b'):
        print("\n🎲 Generating usernames...")
        gen_count = int(input("   How many to generate? [1000]: ").strip() or "1000")
        pattern = input("   Pattern [short/words/mixed/leet] (mixed): ").strip() or "mixed"
        generated = list(UsernameGenerator.generate(gen_count, pattern))
        usernames.extend(generated)
        print(f"   Generated {len(generated)} usernames")
    
    usernames = list(dict.fromkeys(usernames))  # Remove duplicates
    if not usernames:
        print("❌ No usernames to check!")
        return 1
    
    print(f"\n🎯 Total unique usernames: {len(usernames)}")
    confirm = input("   Start hunting? [Y/n]: ").strip().lower()
    if confirm == 'n':
        return 0
    
    # Save config for GitHub Actions
    config = {
        'mode': mode,
        'concurrency': concurrency,
        'timeout': timeout,
        'webhook': webhook,
        'username_count': len(usernames)
    }
    save_config(config)
    
    # Run checker
    checker = DiscordUsernameChecker(
        concurrency=concurrency,
        timeout=timeout,
        webhook_url=webhook,
        proxy_harvester=harvester
    )
    
    await checker.run(usernames)
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))