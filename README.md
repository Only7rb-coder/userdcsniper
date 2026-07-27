# Discord Username Monitor

A reliable, patient username monitor that checks your watchlist every 30 minutes using a real Discord bot token.

## Why This Works

- **No proxies needed** — uses real Discord API with bot token
- **Human speed** — 2-4 seconds between checks, never rate limited
- **Persistent state** — remembers finds, doesn't re-notify
- **Real Discord API** — not hacked registration endpoints

## Setup

### 1. Get a Discord Bot Token

1. Go to https://discord.com/developers/applications
2. Click "New Application" → name it anything
3. Go to "Bot" tab → "Add Bot"
4. Copy the token (looks like `MTAx...`)

### 2. Add Token to GitHub Secrets

1. In your repo, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `DISCORD_TOKEN`
4. Value: your bot token from step 1

### 3. Add Usernames to Watch

Edit `watchlist.txt` and add usernames you want to monitor:
```
alpha
neo
zephyr
cryo
ember
```

**Rules:**
- 2-32 characters
- lowercase a-z, 0-9, underscores, periods
- No more than 50 names (it checks slowly)

### 4. Run the Monitor

1. Go to **Actions** tab in your repo
2. Click **Username Monitor**
3. Click **Run workflow**
4. Optional: add Discord webhook URL for notifications
5. Click **Run workflow**

The monitor runs for 6 hours, checking every 30 minutes.

## Webhook Notifications

If you provide a webhook URL, you'll get:
- 🟡 **Start** — when monitor begins
- 🎯 **Hit** — when a username becomes available
- 🔵 **Cycle** — summary after each check round

## File Structure

```
userdcsniper/
├── .github/workflows/monitor.yml   # GitHub Actions workflow
├── src/
│   ├── __init__.py                  # Package marker
│   ├── discord_api.py               # Discord API client
│   ├── webhook.py                   # Discord notifications
│   ├── monitor.py                   # Monitor engine
│   └── username_gen.py              # Username validation
├── run_monitor.py                   # Entry point
├── requirements.txt                 # Dependencies
├── watchlist.txt                    # Your targets
└── README.md                        # This file
```

## Troubleshooting

**"DISCORD_TOKEN not set"**
→ You forgot to add the secret. Go to Settings → Secrets → Actions.

**"watchlist.txt is empty"**
→ Add at least one username to the file.

**"invalid_token"**
→ Your bot token is wrong. Regenerate it in Discord Developer Portal.

**No notifications**
→ Check your webhook URL is correct. Test it by sending a POST manually.
