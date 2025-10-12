# Railway Deployment Guide - Hume DSPy Agent

## 🚀 Quick Deploy to Railway

### Prerequisites
- GitHub account with the hume-dspy-agent repository
- Railway account (sign up at railway.app)
- All API credentials ready

### Step 1: Create Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose **joshn8er2022/hume-dspy-agent**
5. Railway will automatically detect the Python app

### Step 2: Configure Environment Variables

In Railway dashboard, go to **Variables** tab and add:

```bash
# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# Close CRM
CLOSE_API_KEY=your_close_api_key

# SendGrid
SENDGRID_API_KEY=your_sendgrid_key

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number

# Slack
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_USER_TOKEN=your_slack_user_token

# Vapi
VAPI_API_KEY=your_vapi_key
VAPI_ASSISTANT_ID=your_vapi_assistant_id

# Typeform
TYPEFORM_TOKEN=your_typeform_token
```

**💡 Tip:** Copy actual values from your credentials backup file

### Step 3: Deploy

1. Railway will automatically build and deploy
2. Wait 2-3 minutes for deployment
3. You'll get a public URL like: `https://hume-dspy-agent-production.up.railway.app`

### Step 4: Configure Typeform Webhook

1. Go to your Typeform form settings
2. Navigate to **Connect** → **Webhooks**
3. Add webhook URL: `https://your-railway-url.up.railway.app/webhook/typeform`
4. Test the webhook

### Step 5: Test the Deployment

```bash
# Health check
curl https://your-railway-url.up.railway.app/health

# Test lead qualification
curl -X POST https://your-railway-url.up.railway.app/api/qualify-lead   -H "Content-Type: application/json"   -d @test_lead.json
```

## 📊 Expected Costs

- **Railway Hosting**: $5/month (Hobby plan)
- **OpenAI API**: ~$20-30/month (1000 leads)
- **Total**: ~$25-35/month

## 🔧 Troubleshooting

### Deployment Fails
- Check Railway logs for errors
- Verify all environment variables are set
- Ensure requirements.txt is up to date

### Webhook Not Working
- Verify Railway URL is public
- Check Typeform webhook configuration
- Review Railway logs for incoming requests

### Database Connection Issues
- Verify Supabase credentials
- Check Supabase project is active
- Test connection from Railway logs

## 📚 Next Steps

1. **Monitor**: Check Railway logs and metrics
2. **Scale**: Upgrade Railway plan if needed
3. **Optimize**: Review DSPy agent performance
4. **Expand**: Add more agents (outbound, routing, analytics)

## 🔗 Useful Links

- [Railway Docs](https://docs.railway.app/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [DSPy Documentation](https://dspy-docs.vercel.app/)

---

**Need help?** Check Railway logs or contact support.
