# 🔧 Trusted MCP Servers - Hume AI B2B Sales Automation

**Purpose**: This file guides the agent on WHEN and WHY to use each MCP server.  
**Updated**: October 19, 2025

---

## **📋 MCP SERVERS**

### **com.zapier/mcp**

**What it provides**:
- 200+ business integrations (CRMs, email, calendars, etc.)
- Close CRM operations (60+ tools)
- GMass email automation
- Calendar management
- Data sync across platforms

**When to USE**:
- Creating or updating leads in Close CRM
- Sending automated email sequences
- Scheduling meetings or calendar operations
- Cross-platform data synchronization
- Business workflow automation

**When NOT to use**:
- Simple data queries (use Supabase directly instead)
- Research tasks (use Perplexity instead)
- Read-only database operations (too expensive)
- Testing or development work (use mock data)

**Cost**: ⚠️ **HIGH**
- API calls to Zapier ($)
- Downstream API calls to integrated services ($$)
- Rate limits apply

**Performance**: Medium (1-3 seconds per operation)

**Best Practice**:
- Batch operations when possible
- Use only for write operations (creating/updating)
- Prefer direct API calls for read-only ops

---

### **com.perplexity/research**

**What it provides**:
- Real-time web research with citations
- Company intelligence (funding, news, team)
- Market research and trends
- Competitive analysis
- Recent information (<6 months)

**When to USE**:
- Researching companies for lead qualification
- Finding decision-makers at target accounts
- Checking recent company news (funding, acquisitions)
- Competitive intelligence gathering
- Market trend analysis
- Anything requiring recent/current information

**When NOT to use**:
- Company data already in Supabase (check first!)
- Historical analysis (use our database)
- Structured data that Clearbit/Apollo can provide
- Simple web lookups (use Apify for scraping)

**Cost**: ⚠️ **MEDIUM**
- Per-query pricing (~$0.01-0.05 per search)
- Higher for complex multi-step research

**Performance**: Fast (2-5 seconds)

**Best Practice**:
- Check Supabase first (avoid duplicate research)
- Use for HOT leads primarily (better ROI)
- Cache results in memory for reuse

---

### **com.apify/web-scraping**

**What it provides**:
- Large-scale website scraping
- Data extraction from any web page
- Monitoring competitor websites
- Building lead lists from directories
- Structured data extraction

**When to USE**:
- Extracting multiple leads from a directory
- Monitoring competitor pricing/features
- Building contact lists from websites
- Scraping company data at scale
- When no API exists for the data

**When NOT to use**:
- Single-page lookups (use Perplexity instead)
- Data available via API (always prefer API)
- Real-time research (Perplexity is faster)
- Simple company lookups (use Clearbit/Apollo)

**Cost**: ⚠️ **HIGH**
- Compute-intensive operations
- Per-run pricing (varies by complexity)
- Can be slow (30 seconds to several minutes)

**Performance**: Slow (30s - 5min depending on scale)

**Best Practice**:
- Use for batch operations (10+ items)
- Schedule during off-peak hours if possible
- Only for data not available via API

---

## **🏠 INTERNAL TOOLS (Always Available)**

These tools are always loaded - no MCP server needed. Use these FIRST before considering MCP servers.

### **audit_lead_flow**

**What it does**: Audits email campaigns and lead quality

**When to USE**:
- Checking email deliverability
- Analyzing campaign performance
- Lead flow quality checks
- Troubleshooting GMass issues

**Cost**: FREE (internal)  
**Performance**: Fast (1-2 seconds)

---

### **query_supabase**

**What it does**: Direct SQL queries to PostgreSQL

**When to USE**:
- ANY database read operation
- Lead lookups
- Pipeline analytics
- Historical data queries
- Data verification

**Cost**: FREE (internal)  
**Performance**: Very fast (<1 second)

**Best Practice**: 
- ALWAYS check Supabase BEFORE researching externally
- Use this for ALL read operations
- Prefer over MCP for data we already have

---

### **get_pipeline_stats**

**What it does**: Pipeline analytics and metrics

**When to USE**:
- Pipeline health checks
- Conversion rate analysis
- Lead tier distribution
- Campaign performance metrics

**Cost**: FREE (internal)  
**Performance**: Fast (1-2 seconds)

---

## **🎯 DECISION TREE**

Use this to decide which tools to load:

```
1. Do we need to CREATE/UPDATE data externally?
   YES → Consider Zapier (Close CRM, GMass, etc.)
   NO → Continue

2. Do we need RESEARCH on a company?
   YES → Check Supabase first
         Data exists? → Use query_supabase
         Data missing? → Use Perplexity
   NO → Continue

3. Do we need to SCRAPE multiple websites?
   YES → Use Apify (for batch operations)
   NO → Continue

4. Do we need INTERNAL DATA?
   YES → Use query_supabase (fastest)
   
5. Do we need PIPELINE METRICS?
   YES → Use get_pipeline_stats
```

---

## **💰 COST OPTIMIZATION RULES**

1. **Check internal data first**
   - Supabase is free and fast
   - Avoid re-researching known data

2. **Batch external operations**
   - Research 5+ companies? Use Apify
   - Creating multiple leads? Batch Zapier calls

3. **Tier-based spending**
   - HOT leads: All tools available
   - WARM leads: Perplexity + Zapier only
   - COOL leads: Internal tools only
   - COLD leads: No external research

4. **Cache aggressively**
   - Store research results in memory
   - Save to Supabase for future use
   - Avoid duplicate API calls

---

## **⚡ PERFORMANCE OPTIMIZATION**

### **Fast Operations** (<1 second)
- query_supabase
- get_pipeline_stats
- Memory recall

### **Medium Operations** (1-5 seconds)
- Perplexity research
- Zapier single operations
- audit_lead_flow

### **Slow Operations** (30s - 5min)
- Apify web scraping
- Zapier batch operations
- Multiple Perplexity queries

**Best Practice**: Combine fast + slow operations intelligently
- Start with fast (Supabase lookup)
- Then medium if needed (Perplexity)
- Only slow if absolutely necessary (Apify)

---

## **🚨 COMMON MISTAKES TO AVOID**

1. ❌ **Using Perplexity when data is in Supabase**
   - Wastes money and time
   - Always check database first

2. ❌ **Using Apify for single lookups**
   - Way too slow for one item
   - Use Perplexity instead

3. ❌ **Loading all MCP servers for simple queries**
   - Bloats context window
   - Slows responses
   - Increases costs

4. ❌ **Using Zapier for read operations**
   - Expensive and slow
   - Use Supabase or direct APIs

5. ❌ **Not caching research results**
   - Pays twice for same data
   - Store in Supabase after research

---

## **📈 USAGE EXAMPLES**

### **Example 1: Qualify a new lead**

**Task**: "Qualify lead: josh@acme.com"

**Correct Tool Selection**:
```
1. query_supabase → Check if we've seen them before
2. IF new:
   - Perplexity → Research Acme Corp
   - query_supabase → Store research results
3. Internal scoring → Qualify lead
4. IF HOT:
   - Zapier → Create Close lead
```

**Why**: Checks database first, researches only if new, stores results

---

### **Example 2: Audit email campaign**

**Task**: "How's the email campaign performing?"

**Correct Tool Selection**:
```
1. audit_lead_flow → Get email metrics
2. query_supabase → Get historical comparison
3. get_pipeline_stats → Overall context
```

**Why**: All internal tools, fast and free

---

### **Example 3: Research competitors**

**Task**: "Research our top 5 competitors"

**Correct Tool Selection**:
```
1. query_supabase → Get competitor list
2. Apify → Scrape all 5 websites in parallel
3. Perplexity → Get recent news for each
4. query_supabase → Store all research
```

**Why**: Batch operation justifies Apify, Perplexity for news

---

## **🔄 UPDATES & MAINTENANCE**

**When to update this file**:
- New MCP server added
- Pricing changes
- Performance characteristics change
- New use cases discovered
- Cost optimization insights

**Review frequency**: Monthly or when issues arise

---

## **🎓 LESSONS FROM RESEARCH**

Based on "Agentic MCP Configuration" paper:

1. **Curate, don't collect**
   - Small trusted list > huge tool directory
   - Quality over quantity

2. **Describe, don't just list**
   - Agent needs context on WHEN to use tools
   - Cost and performance matter

3. **Dynamic loading is key**
   - Don't load all tools all the time
   - Select based on task analysis

4. **Learn from usage**
   - Track which tools work for which tasks
   - Optimize selection over time

---

**Last Updated**: October 19, 2025  
**Maintained By**: Strategy Agent + Josh  
**Version**: 1.0
