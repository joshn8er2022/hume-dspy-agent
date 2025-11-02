# Complete Tool Inventory - Internal & External

**Date:** 2025-11-02  
**Purpose:** Comprehensive inventory of all tools available to the system

---

## 📋 Executive Summary

### Tool Categories

| Category | Count | Status |
|----------|-------|--------|
| **ReAct Tools (StrategyAgent)** | 16 | ✅ Active |
| **Internal Tools** | 8 | ✅ Active |
| **External APIs** | 12+ | ⚠️ Varies |
| **MCP Tools (Zapier)** | 200+ | ⚠️ Requires MCP_SERVER_URL |
| **Research Tools** | 6 | ⚠️ Partially Implemented |
| **RAG Tools** | 3 | ✅ Active (87 docs indexed) |
| **Wolfram Tools** | 3 | ⚠️ Requires WOLFRAM_APP_ID |

---

## 🔧 INTERNAL TOOLS

### 1. ReAct Tools (StrategyAgent)

**Location:** `agents/strategy_agent.py` - `_init_tools()` method

These are the tools that StrategyAgent can call via ReAct reasoning:

#### Core Tools (3)
1. **`audit_lead_flow(timeframe_hours=24)`**
   - Audits lead flow with real data from Supabase and GMass
   - Returns: Lead metrics, email stats, deliverability, opens, clicks, replies
   - **Status:** ✅ Working
   - **Requires:** Supabase, GMass API

2. **`query_supabase(table, limit=100)`**
   - Queries Supabase database tables (leads, conversations, agent_state)
   - Returns: JSON query results
   - **Status:** ✅ Working
   - **Requires:** SUPABASE_URL, SUPABASE_SERVICE_KEY

3. **`get_pipeline_stats()`**
   - Gets current pipeline statistics
   - Returns: Total leads, breakdown by tier/source, recent activity
   - **Status:** ✅ Working
   - **Requires:** Supabase

#### MCP Tools (4)
4. **`create_close_lead(name, email, phone, company, note)`**
   - Creates lead in Close CRM via MCP
   - **Status:** ⚠️ Requires MCP_SERVER_URL + Close CRM integration
   - **Requires:** MCP_SERVER_URL, Close CRM configured in Zapier

5. **`research_with_perplexity(query)`**
   - Research using Perplexity AI via MCP
   - **Status:** ⚠️ Requires MCP_SERVER_URL + Perplexity integration
   - **Requires:** MCP_SERVER_URL, Perplexity configured in Zapier

6. **`scrape_website(url)`**
   - Scrapes website via Apify MCP tool
   - **Status:** ⚠️ Requires MCP_SERVER_URL + Apify integration
   - **Requires:** MCP_SERVER_URL, Apify configured in Zapier

7. **`list_mcp_tools()`**
   - Lists all available MCP tools from Zapier (200+)
   - **Status:** ⚠️ Requires MCP_SERVER_URL
   - **Requires:** MCP_SERVER_URL

#### Agent Collaboration Tools (3)
8. **`delegate_to_subordinate(profile, task)`**
   - Delegates to specialized subordinate agents
   - Profiles: competitor_analyst, market_researcher, account_researcher, etc.
   - **Status:** ✅ Working
   - **Requires:** Agent delegation system

9. **`ask_other_agent(agent_name, question)`**
   - Asks other agents (InboundAgent, ResearchAgent, FollowUpAgent, AuditAgent)
   - **Status:** ✅ Working
   - **Requires:** A2A communication

10. **`refine_subordinate_work(profile, feedback)`**
    - Provides feedback to refine subordinate work
    - **Status:** ✅ Working
    - **Requires:** Agent delegation system

#### RAG Knowledge Base Tools (3)
11. **`search_knowledge_base(query, limit=5)`**
    - Semantic search across 87 indexed Google Drive files (11,325 chunks)
    - **Status:** ✅ Working
    - **Requires:** SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY
    - **Data:** 87 documents indexed

12. **`list_indexed_documents()`**
    - Lists all indexed documents in knowledge base
    - **Status:** ✅ Working
    - **Requires:** Supabase

13. **`query_spreadsheet_data(file_name, query_description)`**
    - Queries data from indexed spreadsheets (KPI trackers, logs, etc.)
    - **Status:** ✅ Working
    - **Requires:** Supabase

#### Wolfram Alpha Tools (3)
14. **`wolfram_strategic_query(query, category=None)`**
    - Strategic intelligence queries (market analysis, demographics, etc.)
    - **Status:** ⚠️ Requires WOLFRAM_APP_ID
    - **Requires:** WOLFRAM_APP_ID

15. **`wolfram_market_analysis(market, metric, comparison_regions=None)`**
    - Market metrics analysis with regional comparisons
    - **Status:** ⚠️ Requires WOLFRAM_APP_ID
    - **Requires:** WOLFRAM_APP_ID

16. **`wolfram_demographic_insight(region, demographic_query)`**
    - Demographic data for strategic planning
    - **Status:** ⚠️ Requires WOLFRAM_APP_ID
    - **Requires:** WOLFRAM_APP_ID

---

## 🔌 EXTERNAL API SERVICES

### Database & Storage

#### Supabase ✅ ACTIVE
- **Purpose:** PostgreSQL database + pgvector for RAG
- **Status:** ✅ Configured and working
- **Environment Variables:**
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY` or `SUPABASE_KEY`
- **Features:**
  - Lead storage
  - Agent state persistence
  - RAG vector database (11,325 chunks)
  - Conversation history

### LLM Services

#### OpenRouter ✅ ACTIVE
- **Purpose:** Access to multiple LLM models (Claude Sonnet, Haiku, GPT-4, etc.)
- **Status:** ✅ Configured and working
- **Environment Variables:**
  - `OPENROUTER_API_KEY`
- **Models Used:**
  - Primary: `anthropic/claude-sonnet-4.5` (high-tier reasoning)
  - Secondary: `openrouter/anthropic/claude-haiku-4.5` (low-tier tasks)

#### OpenAI ✅ ACTIVE (for embeddings)
- **Purpose:** Text embeddings for RAG (text-embedding-3-small)
- **Status:** ✅ Configured and working
- **Environment Variables:**
  - `OPENAI_API_KEY`
- **Usage:** Knowledge base embeddings

#### Anthropic ⚠️ OPTIONAL
- **Purpose:** Direct Claude API access (fallback)
- **Status:** ⚠️ Configured but not primary
- **Environment Variables:**
  - `ANTHROPIC_API_KEY`

### Communication

#### Slack ✅ ACTIVE
- **Purpose:** Notifications, UI, lead updates
- **Status:** ✅ Configured and working
- **Environment Variables:**
  - `SLACK_BOT_TOKEN` or `SLACK_MCP_XOXB_TOKEN`
  - `SLACK_CHANNEL` or `SLACK_CHANNEL_INBOUND`
  - `JOSH_SLACK_DM_CHANNEL` (optional)
- **Features:**
  - Lead notifications
  - Thread updates
  - Conversational interface

#### Email (GMass) ⚠️ REQUIRES CONFIG
- **Purpose:** Email campaigns and follow-ups
- **Status:** ⚠️ Code ready, needs GMASS_API_KEY
- **Environment Variables:**
  - `GMASS_API_KEY`
  - `FROM_EMAIL` (authenticated Gmail address)
- **Fallback:** SendGrid (if configured)
- **Location:** `utils/email_client.py`

#### SendGrid ⚠️ OPTIONAL (fallback)
- **Purpose:** Email fallback if GMass fails
- **Status:** ⚠️ Optional
- **Environment Variables:**
  - `SENDGRID_API_KEY`

### CRM

#### Close CRM ⚠️ VIA MCP
- **Purpose:** Lead sync to CRM
- **Status:** ⚠️ Available via MCP (requires MCP_SERVER_URL)
- **Access:** Via `create_close_lead` ReAct tool
- **Requires:** MCP Zapier integration configured

### Research APIs

#### Clearbit ✅ IMPLEMENTED
- **Purpose:** Person and company enrichment
- **Status:** ✅ Code implemented
- **Environment Variables:**
  - `CLEARBIT_API_KEY`
- **Location:** `agents/research_agent.py`
- **Methods:**
  - `_clearbit_person_lookup(email)` ✅ Working
  - `_clearbit_company_lookup(company, domain)` ✅ Working

#### Apollo.io ❌ STUB
- **Purpose:** Find contacts at companies
- **Status:** ❌ Stub (returns empty list)
- **Environment Variables:**
  - `APOLLO_API_KEY`
- **Location:** `agents/research_agent.py`
- **Method:** `_apollo_find_contacts()` - TODO

#### Perplexity ⚠️ VIA MCP
- **Purpose:** AI research (real-time web research)
- **Status:** ⚠️ Available via MCP
- **Access:** Via `research_with_perplexity` ReAct tool
- **Requires:** MCP Zapier integration configured
- **Alternative:** Direct API key available (`PERPLEXITY_API_KEY`) but not used

### Web Scraping

#### Apify ⚠️ VIA MCP
- **Purpose:** Website scraping
- **Status:** ⚠️ Available via MCP
- **Access:** Via `scrape_website` ReAct tool
- **Requires:** MCP Zapier integration configured

### Strategic Intelligence

#### Wolfram Alpha ⚠️ REQUIRES API KEY
- **Purpose:** Computational knowledge, market analysis, demographics
- **Status:** ⚠️ Code ready, needs WOLFRAM_APP_ID
- **Environment Variables:**
  - `WOLFRAM_APP_ID`
- **Location:** `tools/wolfram_alpha.py`
- **Tools:**
  - `wolfram_strategic_query()`
  - `wolfram_market_analysis()`
  - `wolfram_demographic_insight()`

### Observability

#### Phoenix (Arize) ✅ ACTIVE
- **Purpose:** LLM tracing and observability
- **Status:** ✅ Configured and working
- **Environment Variables:**
  - `PHOENIX_API_KEY` (optional)
  - `PHOENIX_ENDPOINT` (optional)
  - `PHOENIX_PROJECT_NAME` (optional)
- **Location:** `core/observability.py`
- **Features:**
  - DSPy call tracing
  - LangChain tracing
  - Span visualization

---

## 🔄 MCP TOOLS (via Zapier)

### Access Method
- **MCP Client:** `core/mcp_client.py`
- **Server:** Zapier MCP server (200+ tools)
- **Status:** ⚠️ Requires `MCP_SERVER_URL` environment variable

### Available Integrations (200+ tools)

**Access via `list_mcp_tools()` ReAct tool once MCP_SERVER_URL is configured**

Common integrations include:
- **Google Workspace (68 tools):** Drive, Docs, Sheets, Gmail, Slides, Calendar
- **Close CRM (60+ tools):** Lead management, pipeline updates
- **GMass:** Email automation
- **Perplexity:** AI research
- **Apify:** Web scraping
- **Slack:** Enhanced Slack operations
- **Many more...**

### MCP Tools Used in Code

1. **`mcp.close_create_lead()`** - Create Close CRM lead
2. **`mcp.perplexity_research()`** - Perplexity research
3. **`mcp.scrape_url()`** - Apify web scraping
4. **`mcp.list_tools()`** - List all available MCP tools

---

## 📊 RESEARCH TOOLS STATUS

### ResearchAgent Tools

**Location:** `agents/research_agent.py`

| Tool | Status | Implementation | Env Var Required |
|------|--------|---------------|------------------|
| Clearbit Person Lookup | ✅ Working | Fully implemented | CLEARBIT_API_KEY |
| Clearbit Company Lookup | ✅ Working | Fully implemented | CLEARBIT_API_KEY |
| LinkedIn Search | ❌ **STUB** | Returns `None` | - |
| Company News Search | ❌ **STUB** | Returns `[]` | PERPLEXITY_API_KEY (not used) |
| Tech Stack Analysis | ❌ **STUB** | Returns `[]` | - |
| Apollo Contacts | ❌ **STUB** | Returns `[]` | APOLLO_API_KEY |
| Domain Lookup | ⚠️ Heuristic | Simple `.com` guess | - |

**Note:** Most research tools are stubs/TODOs. See `docs/MISSING_FUNCTIONALITY_ANALYSIS.md` for details.

---

## 🧪 TESTING TOOLS

### Available Test Scripts

1. **`tools/test_integration.py`** - Test tool imports and signatures
2. **`tests/test_research.py`** - Research agent tests
3. **`tests/test_email_reliability.py`** - Email client tests
4. **`tools/test_wolfram.py`** - Wolfram Alpha tests

---

## 📝 ENVIRONMENT VARIABLES SUMMARY

### Required for Core Functionality ✅

```bash
# Database
SUPABASE_URL
SUPABASE_SERVICE_KEY  # or SUPABASE_KEY

# LLMs
OPENROUTER_API_KEY
OPENAI_API_KEY  # For embeddings

# Communication
SLACK_BOT_TOKEN  # or SLACK_MCP_XOXB_TOKEN
SLACK_CHANNEL  # or SLACK_CHANNEL_INBOUND
```

### Required for Email ✅

```bash
GMASS_API_KEY
FROM_EMAIL  # Authenticated Gmail address
```

### Optional but Recommended ⚠️

```bash
# CRM
CLOSE_API_KEY  # Or use via MCP

# Research
CLEARBIT_API_KEY  # Person/company enrichment
APOLLO_API_KEY  # Contact finding (not implemented)
PERPLEXITY_API_KEY  # Not used directly (use MCP)

# Strategic Intelligence
WOLFRAM_APP_ID  # Market analysis, demographics

# MCP Access (200+ tools)
MCP_SERVER_URL  # Zapier MCP server URL

# Observability
PHOENIX_API_KEY  # Optional
PHOENIX_ENDPOINT  # Optional
PHOENIX_PROJECT_NAME  # Optional
```

---

## ✅ WORKING TOOLS (No Action Needed)

1. **Supabase** - Database + RAG ✅
2. **OpenRouter** - LLM access ✅
3. **OpenAI** - Embeddings ✅
4. **Slack** - Notifications ✅
5. **Phoenix** - Observability ✅
6. **RAG Tools** - Knowledge base search ✅
7. **Core ReAct Tools** - audit, query, stats ✅
8. **Agent Collaboration** - delegate, ask, refine ✅
9. **Clearbit** - Person/company enrichment ✅

---

## ⚠️ NEEDS CONFIGURATION

### High Priority
1. **GMASS_API_KEY** - Email sending
2. **MCP_SERVER_URL** - Access to 200+ MCP tools

### Medium Priority
3. **WOLFRAM_APP_ID** - Strategic intelligence
4. **CLEARBIT_API_KEY** - Already works, but verify it's set

### Low Priority (Stubs)
5. **APOLLO_API_KEY** - Contact finding (not implemented yet)
6. **PERPLEXITY_API_KEY** - Not used directly (use MCP instead)

---

## ❌ NOT IMPLEMENTED (Stubs/TODOs)

1. **LinkedIn Search** - Returns `None`
2. **Company News Search** - Returns `[]`
3. **Tech Stack Analysis** - Returns `[]`
4. **Apollo Contacts** - Returns `[]`
5. **Domain Lookup** - Simple heuristic only

**See:** `docs/MISSING_FUNCTIONALITY_ANALYSIS.md` for implementation plan.

---

## 🔍 HOW TO CHECK TOOL STATUS

### Test Internal Tools
```python
# Test RAG search
from tools.strategy_tools import search_knowledge_base
result = await search_knowledge_base("test query")

# Test Wolfram (if configured)
from tools.wolfram_alpha import wolfram_strategic_query
result = await wolfram_strategic_query("test query")
```

### Test MCP Tools
```python
from core.mcp_client import get_mcp_client
mcp = get_mcp_client()
tools = await mcp.list_tools()  # Should return 200+ tools if configured
```

### Test ReAct Tools
```python
# In Slack: Ask StrategyAgent
"List all available MCP tools"
"Search knowledge base for Q1 strategy"
"What are the pipeline stats?"
```

---

## 📊 TOOL USAGE STATISTICS

- **Total ReAct Tools:** 16
- **MCP Tools Available:** 200+ (if MCP_SERVER_URL configured)
- **RAG Documents Indexed:** 87 files, 11,325 chunks
- **Research Tools Implemented:** 2/7 (29%)
- **Working External APIs:** 6/12+ (50%)

---

## 🚀 NEXT STEPS

1. **Configure MCP_SERVER_URL** - Unlock 200+ tools
2. **Set WOLFRAM_APP_ID** - Enable strategic intelligence
3. **Implement Research Stubs** - LinkedIn, news, Apollo
4. **Verify GMASS_API_KEY** - Ensure email sending works
5. **Test All Tools** - Run integration tests

---

## 📚 RELATED DOCUMENTATION

- **Missing Functionality:** `docs/MISSING_FUNCTIONALITY_ANALYSIS.md`
- **Root Cause Analysis:** `docs/ROOT_CAUSE_ANALYSIS.md`
- **MCP Integration:** `docs/MCP_INTEGRATION_PHASE0.md`
- **RAG Implementation:** `docs/RAG_IMPLEMENTATION_PLAN.md`

