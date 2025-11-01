# Railway CLI Setup & Variable Access

## Install Railway CLI

**Option 1: Official Installer (Recommended)**
```bash
bash -c "$(curl -fsSL https://railway.app/install.sh)"
```

**Option 2: Using Homebrew**
```bash
brew install railway
```

**Option 3: Using npm**
```bash
npm install -g @railway/cli
```

---

## Connect to Your Project

### Step 1: Login
```bash
railway login
```
This will open a browser window for authentication.

### Step 2: Link Project
```bash
cd /Users/joshisrael/hume-dspy-agent
railway link
```
Select your `hume-dspy-agent` project from the list.

---

## View Environment Variables

### List All Variables
```bash
railway variables
```

### Get Specific Variable
```bash
railway variables get SUPABASE_URL
railway variables get OPENAI_API_KEY
railway variables get WOLFRAM_APP_ID
```

### Export All Variables to File
```bash
railway variables > railway_env_vars.txt
```

---

## Check Deployment Status

### View Recent Deployments
```bash
railway status
```

### View Deployment Logs
```bash
railway logs
```

### View Live Logs (Follow)
```bash
railway logs --follow
```

---

## Deploy Current Changes

### Check What Will Be Deployed
```bash
git status
```

### Deploy to Railway
```bash
railway up
```

**Or use Git push (if auto-deploy is enabled):**
```bash
git add .
git commit -m "feat: Phase 2.0 - RAG + Wolfram Alpha Integration"
git push origin main
```

---

## Verify Deployment

### Check Service Health
```bash
railway run curl https://hume-dspy-agent-production.up.railway.app/health
```

### Run Command in Railway Environment
```bash
railway run python tools/test_integration.py
```

---

## Environment Variables You Need to Verify

### Core Services (REQUIRED)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### Integrations
- `SLACK_BOT_TOKEN`
- `SLACK_APP_TOKEN`
- `GMASS_API_KEY`
- `CLOSE_API_KEY`

### New - Phase 2.0 (CHECK THESE)
- `WOLFRAM_APP_ID` ⚠️ **VERIFY THIS IS SET**
- `MCP_ZAPIER_API_KEY`
- `MCP_PERPLEXITY_API_KEY`
- `MCP_APIFY_API_KEY`

### Observability
- `PHOENIX_API_KEY`
- `PHOENIX_PROJECT_NAME`
- `PHOENIX_ENDPOINT`

---

## Quick Commands Reference

```bash
# Login
railway login

# Link project
railway link

# View all variables
railway variables

# View logs
railway logs

# Deploy
railway up

# Check status
railway status

# Open in browser
railway open

# Run command in Railway environment
railway run <command>

# Get shell access
railway shell
```

---

## Alternative: Check Variables in Railway Dashboard

1. Go to https://railway.app/
2. Select your `hume-dspy-agent` project
3. Click on your service
4. Go to **Variables** tab
5. You'll see all environment variables

---

## What to Check For

### Missing Variables
Look for any missing variables that might cause deployment failures:
- ✅ All core services configured
- ⚠️ `WOLFRAM_APP_ID` - New in Phase 2.0, verify it's set
- ✅ Observability (Phoenix) configured

### Deployment Issues
If deployment is failing:
```bash
# Check logs for errors
railway logs | grep -i error

# Check specific service
railway logs --service=web

# View build logs
railway logs --filter=build
```

---

## Current Deployment Status

**Your project has uncommitted changes:**
- Modified: `agents/strategy_agent.py`
- Modified: `tools/strategy_tools.py`
- New files: Documentation + test suite

**To deploy these changes:**
```bash
cd /Users/joshisrael/hume-dspy-agent
./DEPLOY_NOW.sh
```

This will commit and push all changes, triggering Railway auto-deploy.

---

## Troubleshooting

### Railway CLI Not Found
If you get "railway: command not found":
```bash
# Check installation
which railway

# Re-install
bash -c "$(curl -fsSL https://railway.app/install.sh)"

# Or add to PATH
export PATH="$HOME/.railway/bin:$PATH"
```

### Permission Denied
If you get permission errors:
```bash
# Use sudo for installation
sudo bash -c "$(curl -fsSL https://railway.app/install.sh)"
```

### Project Not Linked
If Railway says "No project linked":
```bash
railway link
# Then select: hume-dspy-agent
```

---

**Next Steps:**
1. Install Railway CLI (see options above)
2. Run `railway login`
3. Run `railway link` (select hume-dspy-agent)
4. Run `railway variables` to see all your environment variables
5. Run `railway logs` to check deployment status
