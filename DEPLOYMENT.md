# 🚀 Deployment Guide

## Quick Deploy to Railway

### 1. Prepare Repository

```bash
cd /root/hume-dspy-agent
git init
git add .
git commit -m "Initial commit: DSPy Inbound Agent"
```

### 2. Push to GitHub

```bash
# Create new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/hume-dspy-agent.git
git branch -M main
git push -u origin main
```

### 3. Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `hume-dspy-agent` repository
4. Railway will auto-detect Python and FastAPI

### 4. Configure Environment Variables

In Railway dashboard, add these variables:

**Required:**
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
DSPY_MODEL=gpt-4o
SUPABASE_URL=https://mvjqoojihjvohstnepfm.supabase.co
SUPABASE_KEY=your_key
```

**Optional (for full integration):**
```
CLOSE_API_KEY=...
SENDGRID_API_KEY=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
SLACK_BOT_TOKEN=...
VAPI_API_KEY=...
```

### 5. Configure Start Command

In Railway settings, set start command:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

### 6. Deploy!

Railway will automatically:
- Install dependencies from `requirements.txt`
- Start the FastAPI server
- Provide a public URL

### 7. Test Deployment

```bash
curl https://your-app.railway.app/health
```

## Alternative: Docker Deployment

### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run

```bash
docker build -t hume-dspy-agent .
docker run -p 8000:8000 --env-file .env hume-dspy-agent
```

## N8N Integration

### Webhook URL

Once deployed, your webhook URL will be:

```
https://your-app.railway.app/webhooks/typeform
```

### N8N Workflow

1. **Typeform Trigger**
   - Webhook URL: (from Typeform)
   - On form submission

2. **HTTP Request Node**
   - Method: POST
   - URL: `https://your-app.railway.app/webhooks/typeform`
   - Body: `{{ $json }}`

3. **Supabase Node** (optional)
   - Log event to events table

4. **Conditional Node**
   - If qualified → Create Close CRM lead
   - If hot → Send Slack notification

## Monitoring

### Railway Logs

View real-time logs in Railway dashboard:
- API requests
- DSPy processing
- Errors and warnings

### Health Check

Set up uptime monitoring:
- Endpoint: `/health`
- Expected: `{"status": "healthy"}`

## Scaling

### Horizontal Scaling

Railway auto-scales based on traffic.

For manual scaling:
- Increase replicas in Railway settings
- Add load balancer if needed

### Performance Tips

1. **Cache DSPy responses** (for similar leads)
2. **Use background tasks** (already implemented)
3. **Batch processing** (for high volume)
4. **Database connection pooling**

## Cost Estimates

### Railway
- Free tier: $5 credit/month
- Hobby: $5/month
- Pro: $20/month

### LLM API Costs
- OpenAI GPT-4o: ~$0.01 per lead
- Anthropic Claude: ~$0.015 per lead

For 1000 leads/month:
- Railway: $5-20
- LLM API: $10-15
- **Total: $15-35/month**

## Security

### API Key Management

- Never commit `.env` to git
- Use Railway environment variables
- Rotate keys regularly

### Rate Limiting

Add to `api/main.py`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/qualify")
@limiter.limit("10/minute")
async def qualify_lead(...):
    ...
```

## Troubleshooting

### Common Issues

**1. DSPy initialization fails**
- Check API key is set
- Verify LLM provider is correct

**2. Webhook not receiving data**
- Check N8N workflow is active
- Verify webhook URL is correct
- Check Railway logs for errors

**3. Slow response times**
- DSPy can take 2-5 seconds per lead
- Use background tasks (already implemented)
- Consider caching for similar leads

## Next Steps

1. ✅ Deploy to Railway
2. ✅ Configure N8N webhook
3. ✅ Test with sample lead
4. ✅ Monitor logs
5. ✅ Add Supabase integration
6. ✅ Add Close CRM integration
7. ✅ Add email/SMS automation
8. ✅ Set up Slack notifications

---

**Ready to deploy? Let's go! 🚀**
