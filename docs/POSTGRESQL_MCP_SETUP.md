# 🐘 PostgreSQL MCP Server Setup

**Date**: October 19, 2025  
**Purpose**: Enable agents to query Supabase/PostgreSQL via MCP tools

**Repository**: https://github.com/crystaldba/postgres-mcp

---

## **🎯 What This Adds**

### **Current State**

Agents query Supabase using direct Python client:

```python
# Direct Supabase client
result = self.supabase.table('leads').select('*').execute()
```

### **With PostgreSQL MCP**

Agents can query via MCP tools (more flexible, composable):

```python
# Via MCP tool in ReAct
def query_leads_table(conditions: str) -> str:
    """Query leads table via MCP."""
    result = await mcp.call_tool("postgres_query", {
        "query": f"SELECT * FROM leads WHERE {conditions}"
    })
    return json.dumps(result)
```

---

## **✅ Benefits**

1. **Unified Tool Interface** - All database queries through MCP
2. **Better ReAct Integration** - Agents can reason about SQL queries
3. **Query Composition** - Combine with other MCP tools
4. **Flexible Queries** - Ad-hoc SQL via tools, not hardcoded
5. **Observable** - All queries traced in Phoenix

---

## **🔧 Setup Instructions**

### **Step 1: Add PostgreSQL MCP Server**

**Option A: Using uvx** (Recommended)

No installation needed! MCP client spawns server on-demand:

```bash
# Server is spawned automatically by MCP client
# Just need to configure it
```

**Option B: Manual Installation**

```bash
# Install the PostgreSQL MCP server
pip install mcp-server-postgres

# Or with uv
uv pip install mcp-server-postgres
```

---

### **Step 2: Configure MCP Client**

Add PostgreSQL server to MCP configuration:

```python
# core/mcp_client.py

class MCPClient:
    def __init__(self):
        # Existing Zapier server
        zapier_url = os.getenv("MCP_SERVER_URL")
        
        # NEW: PostgreSQL server configuration
        self.postgres_server = self._setup_postgres_server()
    
    def _setup_postgres_server(self):
        """Configure PostgreSQL MCP server for Supabase."""
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            logger.warning("⚠️ No DATABASE_URL - PostgreSQL MCP unavailable")
            return None
        
        # Configure MCP server
        server_config = {
            "command": "uvx",
            "args": [
                "mcp-server-postgres",
                database_url  # Supabase connection string
            ]
        }
        
        logger.info("✅ PostgreSQL MCP server configured")
        return server_config
```

---

### **Step 3: Add PostgreSQL Tools to ReAct**

Add database query tools to agents:

```python
# agents/strategy_agent.py

def _init_tools(self) -> List:
    """Initialize tools including PostgreSQL MCP."""
    
    # ... existing tools ...
    
    def query_leads_advanced(
        where_clause: str = "",
        order_by: str = "created_at DESC",
        limit: int = 100
    ) -> str:
        """
        Query leads table with flexible SQL conditions via MCP.
        
        Args:
            where_clause: SQL WHERE conditions (e.g., "tier = 'HOT'")
            order_by: SQL ORDER BY clause
            limit: Max rows to return
        
        Returns:
            JSON string with query results
        """
        try:
            query = f"""
                SELECT 
                    id, email, first_name, last_name, company,
                    qualification_tier, qualification_score,
                    status, created_at
                FROM leads
                {f"WHERE {where_clause}" if where_clause else ""}
                ORDER BY {order_by}
                LIMIT {limit}
            """
            
            logger.info(f"🔧 ReAct MCP tool: query_leads_advanced")
            result = run_async_in_thread(
                mcp.call_tool("postgres_query", {"query": query})
            )
            logger.info(f"✅ ReAct MCP tool: query_leads_advanced succeeded")
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"❌ ReAct MCP tool query_leads_advanced failed: {e}")
            return json.dumps({"error": str(e), "tool": "query_leads_advanced"})
    
    def aggregate_pipeline_stats() -> str:
        """
        Get aggregate pipeline statistics via SQL via MCP.
        
        Returns:
            JSON with tier counts, avg scores, conversion rates
        """
        try:
            query = """
                SELECT 
                    qualification_tier as tier,
                    COUNT(*) as count,
                    AVG(qualification_score) as avg_score,
                    COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) as conversions
                FROM leads
                WHERE created_at > NOW() - INTERVAL '30 days'
                GROUP BY qualification_tier
                ORDER BY 
                    CASE qualification_tier
                        WHEN 'SCORCHING' THEN 1
                        WHEN 'HOT' THEN 2
                        WHEN 'WARM' THEN 3
                        WHEN 'COOL' THEN 4
                        WHEN 'COLD' THEN 5
                        ELSE 6
                    END
            """
            
            result = run_async_in_thread(
                mcp.call_tool("postgres_query", {"query": query})
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # Return all tools
    tools = [
        # Existing tools
        audit_lead_flow,
        query_supabase,
        get_pipeline_stats,
        create_close_lead,
        research_with_perplexity,
        scrape_website,
        # NEW PostgreSQL MCP tools
        query_leads_advanced,
        aggregate_pipeline_stats
    ]
    
    logger.info(f"   Initialized {len(tools)} ReAct tools")
    logger.info(f"   - 6 existing tools")
    logger.info(f"   - 2 PostgreSQL MCP tools")
    return tools
```

---

### **Step 4: Add Environment Variable**

**Railway**:

```bash
# Use your Supabase connection string
railway variables set DATABASE_URL="postgresql://postgres:PASSWORD@HOST:5432/postgres"
```

**Local** (`.env`):

```bash
# Format: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.umawnwaoahhuttbeyuxs.supabase.co:5432/postgres
```

**Get from Supabase**:
1. Go to Supabase Dashboard
2. Project Settings → Database
3. Copy "Connection string" (URI format)
4. Replace `[YOUR-PASSWORD]` with your actual password

---

## **🧪 Testing**

### **Test 1: Query via Slack**

```
Send: "query the leads table for all HOT leads created this week"

Expected:
→ ReAct selects query_leads_advanced tool
→ MCP executes SQL query
→ Returns results
→ Agent synthesizes natural language response
```

### **Test 2: Aggregate Stats**

```
Send: "show me pipeline breakdown by tier for last 30 days"

Expected:
→ ReAct selects aggregate_pipeline_stats tool
→ MCP executes aggregate query
→ Returns tier counts + conversion rates
→ Agent formats results nicely
```

---

## **📊 Available PostgreSQL MCP Tools**

Based on the [postgres-mcp](https://github.com/crystaldba/postgres-mcp) repository:

### **Core Tools**

1. **`postgres_query`** - Execute SELECT queries
   ```python
   await mcp.call_tool("postgres_query", {
       "query": "SELECT * FROM leads WHERE tier = 'HOT'"
   })
   ```

2. **`postgres_execute`** - Execute INSERT/UPDATE/DELETE
   ```python
   await mcp.call_tool("postgres_execute", {
       "query": "UPDATE leads SET status = 'CONTACTED' WHERE id = ?"
   })
   ```

3. **`postgres_schema`** - Get table schema
   ```python
   await mcp.call_tool("postgres_schema", {
       "table": "leads"
   })
   ```

4. **`postgres_list_tables`** - List all tables
   ```python
   await mcp.call_tool("postgres_list_tables", {})
   ```

---

## **🎯 Use Cases**

### **Use Case 1: Dynamic Lead Queries**

**User**: "Show me all leads from healthcare companies that haven't been contacted"

**Agent**:
```python
# ReAct reasoning
"I need to query leads table with specific conditions"

# Tool call
query_leads_advanced(
    where_clause="company LIKE '%health%' AND status = 'NEW'",
    order_by="qualification_score DESC"
)
```

---

### **Use Case 2: Ad-hoc Analysis**

**User**: "What's our conversion rate by lead source?"

**Agent**:
```python
# Custom SQL via MCP
await mcp.call_tool("postgres_query", {
    "query": """
        SELECT 
            source,
            COUNT(*) as total_leads,
            COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) as conversions,
            ROUND(100.0 * COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) / COUNT(*), 2) as conversion_rate
        FROM leads
        GROUP BY source
        ORDER BY conversion_rate DESC
    """
})
```

---

### **Use Case 3: Data Validation**

**User**: "Check if we have any leads with invalid email formats"

**Agent**:
```python
await mcp.call_tool("postgres_query", {
    "query": """
        SELECT id, email, company
        FROM leads
        WHERE email NOT LIKE '%@%.%'
        OR email IS NULL
    """
})
```

---

## **⚖️ PostgreSQL MCP vs Direct Supabase Client**

### **When to Use PostgreSQL MCP**

✅ **Use MCP when**:
- ReAct agents need flexible queries
- Ad-hoc analysis required
- User asks complex SQL questions
- Want to compose with other MCP tools
- Need full observability in Phoenix

### **When to Use Direct Client**

✅ **Use Direct Client when**:
- Simple CRUD operations
- Predefined queries
- Performance-critical paths
- No reasoning needed (just data fetch)

### **Best Practice: Use Both!**

```python
# Simple, predefined queries → Direct client
async def get_lead_by_id(lead_id: str):
    return self.supabase.table('leads').select('*').eq('id', lead_id).single().execute()

# Complex, dynamic queries → MCP
async def query_leads_dynamic(conditions: Dict):
    # Build SQL dynamically
    # Execute via MCP for flexibility + tracing
    return await mcp.call_tool("postgres_query", {"query": sql})
```

---

## **🚀 Summary**

### **What We Get**

**Before**:
- Direct Supabase client only
- Hardcoded queries
- Limited flexibility

**After**:
- Direct client + PostgreSQL MCP
- Dynamic SQL via ReAct tools
- Flexible ad-hoc queries
- Full observability

### **Total New Tools**

- ✅ `query_leads_advanced` - Flexible lead queries
- ✅ `aggregate_pipeline_stats` - Pipeline analytics
- ✅ Any custom SQL via `postgres_query`

### **Time Investment**

- Configure MCP server: 10 min
- Add ReAct tools: 20 min
- Test + validate: 10 min
- **Total**: 40 minutes

---

## **💡 Next Steps**

**Want me to implement this?**

**A)** Yes, add PostgreSQL MCP now (40 min)

**B)** Later, let's finish PostgreSQL Checkpointer first (already done!)

**C)** Both! (Checkpointer done, add MCP now)

PostgreSQL Checkpointer = **DONE** ✅  
PostgreSQL MCP = **READY TO ADD** (40 min)

Your call! 🎯
