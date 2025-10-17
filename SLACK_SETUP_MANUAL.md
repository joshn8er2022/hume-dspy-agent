# Manual Slack Setup (If Script Fails)

If the automated script doesn't work, set Railway variables manually:

## Option 1: Railway CLI
```bash
railway variables set SLACK_BOT_TOKEN="xoxb-your-token-here"
railway variables set JOSH_SLACK_DM_CHANNEL="U01234ABC56"
```

## Option 2: Railway Dashboard
1. Go to [railway.app](https://railway.app/)
2. Select your `hume-dspy-agent` project
3. Click **"Variables"** tab
4. Click **"Add Variable"**

### Add these variables:

**Variable 1:**
- Name: `SLACK_BOT_TOKEN`
- Value: `xoxb-YOUR-BOT-TOKEN-HERE`
  (Your actual bot token from Step 4)

**Variable 2:**
- Name: `JOSH_SLACK_DM_CHANNEL`  
- Value: `U01234ABC56`
  (Your user ID from Step 5)

5. Click **"Save"**
6. Railway will automatically redeploy

## Verify Deployment
Wait 2-3 minutes, then check:
```bash
railway logs --tail
```

Look for:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

## Test Bot
1. Open Slack
2. Find your bot: **Hume AI Assistant**
3. Send DM: `help`
4. You should get a response!

If no response:
- Check Railway logs: `railway logs | grep -i slack`
- Verify Event Subscriptions URL is verified
- Check bot has DM permissions (`im:history`)
