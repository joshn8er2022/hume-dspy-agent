# Deployment Checklist

## Pre-Deployment

### 1. Rotate Exposed Credentials ✅
- [ ] Generate new Supabase keys ([Supabase Dashboard](https://app.supabase.com))
- [ ] Generate new GMass API key
- [ ] Audit access logs for unauthorized usage
- [ ] Save new credentials securely

### 2. Get Required API Keys
- [ ] Anthropic API key ([Anthropic Console](https://console.anthropic.com))
- [ ] OpenAI API key (for DSPy)
- [ ] Slack Bot Token ([Slack App Settings](https://api.slack.com/apps))
- [ ] GMass API key
- [ ] Typeform webhook secret (from Typeform webhook settings)

### 3. Slack Bot Setup
- [ ] Create Slack app at https://api.slack.com/apps
- [ ] Enable bot token scopes:
  - `chat:write` (post messages)
  - `chat:write.public` (post to any channel)
- [ ] Install app to workspace
- [ ] Copy bot token (starts with `xoxb-`)
- [ ] Create `#inbound-leads` channel (or update SLACK_CHANNEL env var)
- [ ] Invite bot to channel: `/invite @YourBotName`

---

## Railway Deployment

### 1. Install Railway CLI
```bash
npm install -g railway
railway login
```

### 2. Link to Project
```bash
cd /Users/joshisrael/hume-dspy-agent
railway link
```

### 3. Add Redis Service
- Go to Railway dashboard
- Click "New" → "Database" → "Redis"
- Railway will auto-set `REDIS_URL` environment variable

### 4. Set Environment Variables
```bash
# Core Services
railway variables set SUPABASE_URL="https://your-project.supabase.co"
railway variables set SUPABASE_KEY="your_NEW_supabase_key"
railway variables set SUPABASE_SERVICE_KEY="your_NEW_service_key"
railway variables set OPENAI_API_KEY="sk-..."
railway variables set ANTHROPIC_API_KEY="sk-ant-..."

# Webhook Security
railway variables set TYPEFORM_WEBHOOK_SECRET="your_webhook_secret"

# Integrations
railway variables set SLACK_BOT_TOKEN="xoxb-..."
railway variables set SLACK_CHANNEL="inbound-leads"
railway variables set GMASS_API_KEY="your_NEW_gmass_key"

# Email
railway variables set FROM_EMAIL="hello@yourcompany.com"

# Environment
railway variables set ENVIRONMENT="production"
railway variables set DEBUG="false"
```

### 5. Deploy
```bash
railway up
```

### 6. Verify Deployment
- [ ] Check logs: `railway logs`
- [ ] Visit health endpoint: `https://your-app.railway.app/health`
- [ ] Verify no startup errors

---

## Post-Deployment

### 1. Configure Typeform Webhook
- [ ] Go to your Typeform dashboard
- [ ] Navigate to form → Integrations → Webhooks
- [ ] Add webhook URL: `https://your-app.railway.app/webhooks/typeform`
- [ ] Copy webhook secret and add to Railway env vars
- [ ] Test webhook with sample submission

### 2. Test End-to-End Flow
- [ ] Submit test form on Typeform
- [ ] Check Railway logs for processing
- [ ] Verify Slack notification appears
- [ ] Verify Slack thread is created
- [ ] Wait for first follow-up (check timing based on tier)
- [ ] Verify Slack thread update appears

### 3. Monitor First Real Lead
- [ ] Watch Slack for first real lead
- [ ] Verify qualification scores make sense
- [ ] Check email was sent (GMass dashboard)
- [ ] Monitor Slack thread for updates
- [ ] Verify follow-up schedule is correct

---

## Troubleshooting

### No Slack Messages Appearing

**Check:**
1. `SLACK_BOT_TOKEN` is set correctly
2. Bot is invited to `#inbound-leads` channel
3. Bot has `chat:write` permission
4. Railway logs show "✅ Enhanced Slack sent"

**Fix:**
```bash
# In Slack
/invite @YourBotName

# Verify token
railway variables get SLACK_BOT_TOKEN
```

### Follow-up Agent Not Running

**Check:**
1. `ANTHROPIC_API_KEY` is set
2. LangGraph dependencies installed
3. Railway logs show "✅ Autonomous follow-up agent started"

**Fix:**
```bash
# Check logs
railway logs | grep "follow-up"

# Verify Anthropic key
railway variables get ANTHROPIC_API_KEY
```

### Emails Not Sending

**Check:**
1. `GMASS_API_KEY` is set and valid
2. `FROM_EMAIL` is configured
3. GMass account is active

**Fix:**
```bash
# Check GMass dashboard for API errors
# Verify key is rotated (not the old exposed one)
railway variables get GMASS_API_KEY
```

### Webhook Signature Verification Failing

**Check:**
1. `TYPEFORM_WEBHOOK_SECRET` matches Typeform dashboard
2. Railway logs show signature verification errors

**Fix:**
```bash
# Get secret from Typeform dashboard
# Update Railway
railway variables set TYPEFORM_WEBHOOK_SECRET="correct_secret_here"
```

---

## Scaling Considerations

### Current Setup (Good for <1000 leads/month)
- Single Railway service
- Single Redis instance
- No load balancing needed

### If You Grow (>1000 leads/month)
- [ ] Add Celery worker instances (separate Railway service)
- [ ] Upgrade Redis to Redis Cloud or ElastiCache
- [ ] Add horizontal scaling for API
- [ ] Implement rate limiting
- [ ] Add monitoring (Sentry, DataDog)

---

## Monitoring & Alerts

### Set Up Alerts

**Railway:**
- [ ] Enable deployment notifications (Slack/email)
- [ ] Set up crash alerts

**Slack:**
- [ ] Monitor `#inbound-leads` channel
- [ ] Set up keyword alerts for "error", "failed"

**GMass:**
- [ ] Monitor bounce rates
- [ ] Check spam complaints
- [ ] Review open rates weekly

### Key Metrics to Track

| Metric | Target | Red Flag |
|--------|--------|----------|
| Lead processing time | <5 seconds | >30 seconds |
| Qualification score (avg) | 50-70 | <40 (bad leads) |
| Hot lead % | 10-30% | <5% (form issues) |
| Email open rate | >20% | <10% (spam folder) |
| Slack thread updates | 100% | Missing updates |

---

## Rollback Plan

If something goes wrong:

```bash
# Revert to previous deployment
railway rollback

# Or disable webhooks in Typeform
# → Integrations → Webhooks → Disable

# Check previous version logs
railway logs --previous
```

---

## Security Checklist

- [ ] All hardcoded credentials removed from code
- [ ] `.env` file is gitignored
- [ ] Webhook signature verification enabled
- [ ] Production credentials rotated
- [ ] Debug mode disabled (`DEBUG=false`)
- [ ] HTTPS enforced (Railway does this automatically)
- [ ] Rate limiting configured (TODO)
- [ ] PII redaction in logs (implemented)

---

## Success Criteria

Your deployment is successful when:

1. ✅ Test lead submitted on Typeform
2. ✅ Slack notification appears in `#inbound-leads`
3. ✅ Slack thread created with initial message
4. ✅ Follow-up email sent (check GMass)
5. ✅ Slack thread updated with "✅ Email sent"
6. ✅ No errors in Railway logs
7. ✅ Lead saved to Supabase

---

## Next Steps After Deployment

1. **Train Your Team**
   - Show them the `#inbound-leads` channel
   - Explain the tier system (HOT/WARM/COLD)
   - Teach them to respond to @channel pings for hot leads

2. **Optimize Over Time**
   - Review qualification scores weekly
   - Adjust tier thresholds if needed
   - A/B test email templates
   - Monitor response rates

3. **Scale Features**
   - Add SMS follow-ups
   - Implement response detection
   - Build analytics dashboard
   - Add multi-channel routing

---

**Deployment Date:** _______________
**Deployed By:** _______________
**Railway URL:** _______________
**Status:** ⬜ Not Started | ⬜ In Progress | ⬜ Complete

