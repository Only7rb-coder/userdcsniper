#!/usr/bin/env python3
import asyncio
import os
import sys
import json

sys.path.insert(0, 'src')

from proxy_harvester import ProxyHarvester
from checker import DiscordUsernameChecker
from username_gen import UsernameGenerator

async def main():
    # Step 1: Auto proxy harvest
    print("🔌 Step 1: Harvesting proxies...")
    harvester = ProxyHarvester(max_proxies=int(os.environ.get('PROXY_COUNT', 300)))
    
    # Try to load cached proxies first
    if os.path.exists('proxies/working.json'):
        try:
            with open('proxies/working.json', 'r') as f:
                cached = json.load(f)
            print(f"📦 Loaded {len(cached)} cached proxies")
        except:
            pass
    
    await harvester.harvest()
    
    # Save working proxies for next run
    os.makedirs('proxies', exist_ok=True)
    with open('proxies/working.json', 'w') as f:
        json.dump([{'host': p.host, 'port': p.port, 'protocol': p.protocol, 'latency': p.latency} 
                   for p in harvester.working_proxies], f)
    
    print(f"✅ {len(harvester.working_proxies)} proxies ready")
    
    # Build username list
    usernames = []
    source = os.environ.get('USERNAME_SOURCE', 'generate')
    
    if source in ('file', 'both'):
        if os.path.exists('usernames.txt'):
            file_names = UsernameGenerator.from_file('usernames.txt')
            usernames.extend(file_names)
            print(f"📁 Loaded {len(file_names)} from file")
    
    if source in ('generate', 'both'):
        count = int(os.environ.get('GENERATE_COUNT', 5000))
        pattern = os.environ.get('PATTERN', 'mixed')
        generated = list(UsernameGenerator.generate(count, pattern))
        usernames.extend(generated)
        print(f"🎲 Generated {len(generated)} usernames ({pattern})")
    
    usernames = list(dict.fromkeys(usernames))
    if not usernames:
        print("❌ No usernames!")
        return 1
    
    print(f"🎯 Hunting {len(usernames)} usernames...")
    
    # Run checker
    checker = DiscordUsernameChecker(
        concurrency=int(os.environ.get('CONCURRENCY', 50)),
        timeout=int(os.environ.get('TIMEOUT', 10)),
        webhook_url=os.environ.get('WEBHOOK_URL') or None,
        proxy_harvester=harvester
    )
    
    await checker.run(usernames)
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))