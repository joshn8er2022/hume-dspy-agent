# Railway CLI - Variable Check Guide

**Purpose:** How to check environment variables in Railway using CLI

---

## 🔧 Setup Railway CLI

### Install Railway CLI

**Option 1: NPM**
```bash
npm i -g @railway/cli
```

**Option 2: Homebrew**
```bash
brew install railway
```

**Option 3: Direct Download**
- Visit: https://railway.app/cli

### Login
```bash
railway login
```

### Link to Project
```bash
# Navigate to project directory
cd /Users/joshisrael/hume-dspy-agent-1

# Link to Railway project
railway link
```

---

## 📋 Check Variables

### Quick Check (All Variables)
```bash
railway variables
```

### Check Specific Variable
```bash
railway variables | grep VARIABLE_NAME
```

### Use Check Script
```bash
chmod +x scripts/check_railway_vars.sh
./scripts/check_railway_vars.sh
```

---

## 🔍 Variables to Check

### Critical (Required)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY`
- `SLACK_BOT_TOKEN`
- `GMASS_API_KEY`
- `FROM_EMAIL`

### High Value
- `MCP_SERVER_URL` (unlocks 200+ tools)
- `CLEARBIT_API_KEY`
- `WOLFRAM_APP_ID`

### Optional
- `SENDGRID_API_KEY`
- `CLOSE_API_KEY`
- `APOLLO_API_KEY`
- `PERPLEXITY_API_KEY`
- `PHOENIX_API_KEY`

---

## 📊 Expected Results

After running `railway variables`, you should see output like:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxxx...
OPENROUTER_API_KEY=sk-or-xxx...
...
```

Compare the output with the list in `docs/COMPLETE_TOOL_INVENTORY.md` to see what's missing.

---

## 🔧 Set Missing Variables

If variables are missing, set them:

```bash
# Set a variable
railway variables set VARIABLE_NAME=value

# Example
railway variables set WOLFRAM_APP_ID=YOUR_APP_ID
```

---

## 📚 Related

- Full tool inventory: `docs/COMPLETE_TOOL_INVENTORY.md`
- Tool status summary: `docs/TOOL_STATUS_SUMMARY.md`

