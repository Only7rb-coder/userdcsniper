#!/usr/bin/env python3
import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.proxy_harvester import ProxyHarvester
from src.checker import DiscordUsernameChecker
from src.username_gen import UsernameGenerator

async def main():
    mode = os.environ.get('MODE', 'hunt')  # 'hunt' or 'monitor'
    
    print(f"🔌 Step 1: Harvesting proxies...")
    harvester = ProxyHarvester(max_proxies=int(os.environ.get('PROXY_COUNT', 80)))
    
    if os.path.exists('proxies/working.json'):
        try:
            with open('proxies/working.json', 'r') as f:
                cached = json.load(f)
            print(f"📦 Loaded {len(cached)} cached proxies")
        except:
            pass
    
    await harvester.harvest()
    
    os.makedirs('proxies', exist_ok=True)
    with open('proxies/working.json', 'w') as f:
        json.dump([{'host': p.host, 'port': p.port, 'latency': p.latency} 
                   for p in harvester.working_proxies], f)
    
    print(f"✅ {len(harvester.working_proxies)} proxies ready")
    
    usernames = []
    
    if mode == 'monitor':
        # WATCHLIST MODE: Check specific names you want
        watchlist = UsernameGenerator.from_file('watchlist.txt')
        if not watchlist:
            print("❌ watchlist.txt empty or missing! Add names to monitor.")
            return 1
        
        # Generate variants (leet, suffixes)
        usernames = UsernameGenerator.generate_watchlist_variants(watchlist)
        print(f"👁️ Monitoring {len(usernames)} variants of {len(watchlist)} base names...")
        
        # In monitor mode, we loop forever with delays
        checker = DiscordUsernameChecker(
            concurrency=int(os.environ.get('CONCURRENCY', 30)),
            timeout=int(os.environ.get('TIMEOUT', 10)),
            delay_between=1.0,  # Slower in monitor mode
            webhook_url=os.environ.get('WEBHOOK_URL'),
            proxy_harvester=harvester,
            mode="monitor"
        )
        
        cycle = 0
        while True:
            cycle += 1
            print(f"\n{'='*50}")
            print(f"👁️ MONITOR CYCLE #{cycle}")
            print(f"{'='*50}")
            
            await checker.run(usernames)
            
            # Reset for next cycle
            checker.results = []
            checker.stats = {'checked': 0, 'available': 0, 'errors': 0, 'start_time': None}
            
            wait_minutes = int(os.environ.get('MONITOR_INTERVAL', 30))
            print(f"⏳ Waiting {wait_minutes} minutes before next check...")
            await asyncio.sleep(wait_minutes * 60)
    
    else:
        # HUNT MODE: Generate and check new names
        source = os.environ.get('USERNAME_SOURCE', 'generate')
        
        if source in ('file', 'both'):
            if os.path.exists('usernames.txt'):
                file_names = UsernameGenerator.from_file('usernames.txt')
                usernames.extend(file_names)
                print(f"📁 Loaded {len(file_names)} from file")
        
        if source in ('generate', 'both'):
            count = int(os.environ.get('GENERATE_COUNT', 5000))
            pattern = os.environ.get('PATTERN', 'mixed')
            length = os.environ.get('LENGTH', '5-7')  # DEFAULT CHANGED TO 5-7
            generated = list(UsernameGenerator.generate(count, pattern, length))
            usernames.extend(generated)
            print(f"🎲 Generated {len(generated)} usernames ({pattern}, length {length})")
        
        usernames = list(dict.fromkeys(usernames))
        if not usernames:
            print("❌ No usernames!")
            return 1
        
        print(f"🎯 Hunting {len(usernames)} usernames...")
        
        checker = DiscordUsernameChecker(
            concurrency=int(os.environ.get('CONCURRENCY', 50)),
            timeout=int(os.environ.get('TIMEOUT', 10)),
            webhook_url=os.environ.get('WEBHOOK_URL'),
            proxy_harvester=harvester,
            mode="hunt"
        )
        
        await checker.run(usernames)
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
