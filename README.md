# Hume Programs - DSPy Lead Qualification Agent

🤖 **AI-powered lead qualification system using DSPy, Pydantic, and FastAPI**

## 🎯 Overview

This is a production-ready agentic framework that automatically qualifies inbound leads from Typeform submissions using Stanford's DSPy framework with OpenAI GPT-4o or Anthropic Claude.

### Key Features

- ✅ **Intelligent Lead Scoring**: 0-100 scoring across 7 criteria
- ✅ **Tier Assignment**: Hot/Warm/Cold/Unqualified classification
- ✅ **AI-Generated Templates**: Personalized email and SMS messages
- ✅ **Multi-LLM Support**: OpenAI or Anthropic backends
- ✅ **Type-Safe**: Full Pydantic validation
- ✅ **Production Ready**: FastAPI with auto-docs
- ✅ **Integration Ready**: Close CRM, SendGrid, Twilio, Slack

## 🏗️ Architecture

```
Typeform Webhook → N8N → DSPy API → Qualification Results
                            ↓
                    Supabase Database
                            ↓
                    Slack Notification
                            ↓
                    Close CRM Lead
```

## 📊 Qualification Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Business Size | 20 pts | Company employee count |
| Patient Volume | 20 pts | Monthly patient capacity |
| Industry Fit | 15 pts | Healthcare/wellness alignment |
| Response Quality | 15 pts | AI summary depth |
| Calendly Booking | 15 pts | Call scheduled |
| Response Complete | 15 pts | Form completion |
| Company Data | 0 pts | Additional context |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key OR Anthropic API key
- (Optional) Supabase, Close CRM, SendGrid, Twilio credentials

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd hume-dspy-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`
2. Add your API keys:

```bash
# Required: Choose one LLM provider
LLM_PROVIDER=openai  # or 'anthropic'
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# Optional: Integrations
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...
CLOSE_API_KEY=api_...
SENDGRID_API_KEY=SG...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
SLACK_BOT_TOKEN=xoxb-...
```

### Run the API

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## 📡 API Endpoints

### POST `/qualify`

Qualify a lead and get scoring, tier, and recommended actions.

**Request Body**:
```json
{
  "first_name": "Sarah",
  "last_name": "Mitchell",
  "email": "sarah@example.com",
  "company": "Wellness Clinic",
  "business_size": "Medium-sized business (6-20 employees)",
  "patient_volume": "51-300 patients",
  "response_type": "completed"
}
```

**Response**:
```json
{
  "is_qualified": true,
  "score": 85,
  "tier": "hot",
  "reasoning": "...",
  "suggested_email_template": "...",
  "suggested_sms_message": "...",
  "next_actions": ["schedule_call", "send_email"]
}
```

## 🧪 Testing

```bash
# Run comprehensive test suite
python tests/test_suite_comprehensive.py
```

## 📦 Project Structure

```
hume-dspy-agent/
├── agents/
│   └── inbound_agent.py      # Main DSPy agent
├── api/
│   └── main.py               # FastAPI application
├── models/
│   ├── lead.py               # Lead data models
│   ├── qualification.py      # Qualification models
│   └── agent_state.py        # Agent state models
├── tools/
│   ├── rag_tools.py          # RAG tools
│   ├── strategy_tools.py     # Strategy tools
│   └── wolfram_alpha.py      # Wolfram Alpha integration
├── tests/
│   └── test_suite_comprehensive.py # Comprehensive test suite
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🔧 Configuration Options

### LLM Providers

- **OpenAI**: `gpt-4o`, `gpt-4o-mini`
- **Anthropic**: `claude-3-7-sonnet`, `claude-3-5-haiku`

### Tier Thresholds

- **Hot**: 80-100 points
- **Warm**: 60-79 points
- **Cold**: 40-59 points
- **Unqualified**: 0-39 points

## 🌐 Deployment

### Railway

```bash
railway login
railway init
railway up
```

### Render

1. Connect GitHub repository
2. Set environment variables
3. Deploy with `uvicorn api.main:app --host 0.0.0.0 --port $PORT`

### Docker

```bash
docker build -t hume-dspy-agent .
docker run -p 8000:8000 --env-file .env hume-dspy-agent
```

## 💰 Cost Estimate

**Per Lead**:
- OpenAI GPT-4o: $0.02-0.05
- Processing: ~14 seconds

**Monthly (1000 leads)**:
- API: $20-50
- Hosting: $15-35
- **Total**: $35-85/month

## 🤝 Integration Examples

### N8N Webhook

```javascript
// N8N HTTP Request Node
const response = await $http.post('http://your-api.com/qualify', {
  body: $json
});
return response;
```

### Zapier

1. Trigger: Typeform submission
2. Action: Webhooks POST to `/qualify`
3. Action: Send to Slack/CRM based on tier

## 📝 License

MIT License - See LICENSE file

## 🙋 Support

For questions or issues, please open a GitHub issue.

---

**Built with ❤️ using DSPy, FastAPI, and Pydantic**
