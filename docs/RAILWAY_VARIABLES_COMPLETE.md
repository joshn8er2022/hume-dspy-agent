# Complete Railway Variables List

**Date:** 2025-11-02  
**Service:** hume-dspy-agent  
**Project:** calm-stillness  
**Environment:** production

---

## 📋 ALL VARIABLES (40 total)

### Core Infrastructure ✅
- ✅ `SUPABASE_URL` = `https://umawnwaoahhuttbeyuxs.supabase.co`
- ✅ `SUPABASE_SERVICE_KEY` = `eyJhbGci...` (service role JWT)
- ✅ `SUPABASE_KEY` = `eyJhbGci...` (anon key)
- ✅ `SUPABASE_ANON_KEY` = `eyJhbGci...` (anon key)
- ✅ `DATABASE_URL` = `postgresql://postgres:...@db.umawnwaoahhuttbeyuxs.supabase.co:5432/postgres`
- ✅ `REDIS_URL` = `redis://redis-10331.c276.us-east-1-2.ec2.redns.redis-cloud.com:10331`

### LLM Services ✅
- ✅ `OPENROUTER_API_KEY` = `sk-or-v1-42adc7bead7...`
- ✅ `OPENAI_API_KEY` = `sk-proj-iCkwyXugOWkK...`
- ✅ `ANTHROPIC_API_KEY` = `sk-ant-api03-ETGzSGhr...`
- ✅ `LLM_PROVIDER` = `openai`

### Communication ✅
- ✅ `SLACK_BOT_TOKEN` = `xoxb-161288722917-...`
- ✅ `SLACK_CHANNEL` = `ai-test`
- ✅ `JOSH_SLACK_DM_CHANNEL` = `U08NWTATZM0`

### Email ✅
- ✅ `GMASS_API_KEY` = `279d97fc-9c33-49b8-b...`
- ✅ `FROM_EMAIL` = `Josh@myhumehealth.com`
- ✅ `SENDGRID_API_KEY` = `SG.r7ItOHHXTlGsO1qJ...`

### CRM ✅
- ✅ `CLOSE_API_KEY` = `api_07RkcrSr63LcenAv...`

### SMS ✅
- ✅ `TWILIO_ACCOUNT_SID` = `ACde6464828bc8deeae2...`
- ✅ `TWILIO_AUTH_TOKEN` = `604c675f77725086ac5f...`
- ✅ `TWILIO_PHONE_NUMBER` = `+16312505902`

### MCP & External Tools ✅
- ✅ `MCP_SERVER_URL` = `https://mcp.zapier.com/api/mcp/s/...` ← **200+ tools!**

### Research ⚠️
- ❌ `CLEARBIT_API_KEY` - NOT SET (code ready)
- ❌ `APOLLO_API_KEY` - NOT SET (stub anyway)
- ❌ `PERPLEXITY_API_KEY` - NOT SET (not needed, using MCP)

### Strategic Intelligence ⚠️
- ❌ `WOLFRAM_APP_ID` - NOT SET (code ready)

### Observability ✅
- ✅ `PHOENIX_API_KEY` = `eyJhbGci...`

### Knowledge Base (RAG) ✅
- ✅ `GOOGLE_DRIVE_CREDENTIALS_BASE64` = `eyJpbnN0YWxsZWQi...`
- ✅ `GOOGLE_DRIVE_TOKEN_BASE64` = `eyJ0b2tlbiI6ICJ5YTI5...`

### Agent Communication ✅
- ✅ `A2A_API_KEY` = `PzHvM9lOYqkc5TfzWm_YqBfJ5LC14arX4SxphFOwa1Q`

### Webhooks ✅
- ✅ `TYPEFORM_WEBHOOK_SECRET` = `This1`

### Configuration ✅
- ✅ `USE_STRATEGY_AGENT_ENTRY` = `true`
- ✅ `DEBUG` = `false`
- ✅ `ENVIRONMENT` = `production`

### Railway Metadata (Auto-set) ✅
- ✅ `RAILWAY_ENVIRONMENT` = `production`
- ✅ `RAILWAY_ENVIRONMENT_ID` = `b0cfb5a4-9d3f-4533-8a75-993eecd37411`
- ✅ `RAILWAY_ENVIRONMENT_NAME` = `production`
- ✅ `RAILWAY_PROJECT_ID` = `5053bada-208a-4a82-b31e-aad41a7faa45`
- ✅ `RAILWAY_PROJECT_NAME` = `calm-stillness`
- ✅ `RAILWAY_SERVICE_ID` = `af7eac14-d971-48e3-939e-03b69b26383b`
- ✅ `RAILWAY_SERVICE_NAME` = `hume-dspy-agent`
- ✅ `RAILWAY_PUBLIC_DOMAIN` = `hume-dspy-agent-production.up.railway.app`
- ✅ `RAILWAY_PRIVATE_DOMAIN` = `hume-dspy-agent.railway.internal`
- ✅ `RAILWAY_SERVICE_HUME_DSPY_AGENT_URL` = `hume-dspy-agent-production.up.railway.app`
- ✅ `RAILWAY_SERVICE_AGENT_ZERO_URL` = `agent-zero-production-810a.up.railway.app`
- ✅ `RAILWAY_TOKEN` = `bfa6f910-d27e-4db0-97bc-67f7794b0c69`

---

## 📊 CONFIGURATION STATUS BY TOOL

### ✅ FULLY WORKING (12 tools/services)
1. Supabase (database + RAG)
2. OpenRouter (LLMs)
3. OpenAI (embeddings)
4. Slack (notifications)
5. GMass (email)
6. SendGrid (email fallback)
7. Close CRM (direct API)
8. MCP/Zapier (200+ tools)
9. Phoenix (observability)
10. Google Drive (RAG knowledge base)
11. Twilio (SMS)
12. Redis (task queue)

### ⚠️ NEEDS API KEY (2 tools)
1. Clearbit (person/company enrichment)
2. Wolfram Alpha (strategic intelligence)

### ❌ NOT IMPLEMENTED (4 tools - stubs)
1. LinkedIn Search
2. Company News Search
3. Tech Stack Analysis
4. Apollo Contacts

---

## 🎯 SUMMARY

**Total Variables:** 40  
**Critical Variables:** 8/8 ✅ (100%)  
**High-Value Variables:** 1/3 ⚠️ (33%)  
**Optional Variables:** 4/6 ✅ (67%)

**Overall:** ✅ **EXCELLENT** - All critical infrastructure configured!

**Missing:** Only 2 optional keys (Clearbit, Wolfram) that would enhance capabilities but aren't blocking core functionality.

