# checker.py - Modified entry point
import asyncio
import sys

async def main():
    # Check if running in workflow mode
    import os
    if os.path.exists('workflow_config.json'):
        from wizard import run_auto_wizard
        from engine import AsyncChecker
        
        config = await run_auto_wizard()
        
        # Send webhook notification that we're starting
        if config.get('webhook'):
            from engine import DiscordWebhookReporter
            webhook = DiscordWebhookReporter(config['webhook'])
            await webhook.send_report(
                "🎯 **Starting CloudChecker**",
                embed_data={
                    "title": "🚀 Check Started",
                    "description": f"Checking {len(config['usernames']):,} usernames",
                    "color": 0x00ff00,
                    "fields": [
                        {"name": "Concurrency", "value": str(config['concurrency']), "inline": True},
                        {"name": "Timeout", "value": f"{config['timeout']}s", "inline": True},
                        {"name": "Proxies", "value": str(len(config['proxies'])), "inline": True}
                    ]
                }
            )
        
        checker = AsyncChecker(config)
        await checker.run(config['usernames'])
    else:
        # Run normal interactive wizard
        from wizard import run_interactive_wizard
        config = await run_interactive_wizard()
        from engine import AsyncChecker
        checker = AsyncChecker(config)
        await checker.run(config['usernames'])

if __name__ == "__main__":
    asyncio.run(main())
