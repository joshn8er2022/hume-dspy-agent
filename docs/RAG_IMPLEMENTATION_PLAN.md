# 🚀 RAG PIPELINE IMPLEMENTATION PLAN

**Date**: Oct 21, 2025, 12:55 AM  
**Goal**: Enable Hume agent to query business knowledge from Google Drive  
**Timeline**: 3-4 hours total

---

## 🎯 **WHAT WE'RE BUILDING**

### **The Flow**:
```
Your Google Drive (131 files)
        ↓
RAG Pipeline (monitors changes)
        ↓
Extracts text, chunks, creates embeddings
        ↓
Stores in Supabase vector database
        ↓
Agent queries via 4 new RAG tools
        ↓
Agent answers business questions! 🎉
```

### **Example Use Case**:
```
User: "What's our Q1 strategy?"

Agent:
1. Searches vector DB for "Q1 strategy"
2. Finds relevant chunks from "OKR Tracker" and "Call Notes"
3. Synthesizes answer from your actual business docs
4. Returns: "Based on your Q1 OKRs, your strategy focuses on..."
```

---

## 📦 **WHAT'S ALREADY DONE**

✅ Google Drive access (fixed tonight!)
✅ 131 files inventoried
✅ 42 high-priority files identified
✅ RAG pipeline code audited
✅ Supabase already running

---

## 🏗️ **STEP-BY-STEP IMPLEMENTATION**

### **STEP 1: Copy RAG Pipeline Code** (15 mins)

**What**: Move the RAG pipeline from ai-agent-mastery to hume-dspy-agent

**Files to Copy**:
```
Source: /Users/joshisrael/Downloads/odyssey/ai-agent-mastery/4_Pydantic_AI_Agent/RAG_Pipeline/

Copy These:
├── Google_Drive/
│   ├── drive_watcher.py      (18 KB - Main pipeline)
│   ├── config.json            (1 KB - Configuration)
│   └── main.py                (1.5 KB - Entry point)
├── common/
│   ├── db_handler.py          (9 KB - Supabase ops)
│   └── text_processor.py      (6 KB - Text extraction)
└── requirements.txt           (2.5 KB - Dependencies)

Destination: /Users/joshisrael/hume-dspy-agent/rag_pipeline/
```

**What Each File Does**:
- `drive_watcher.py` - Monitors Google Drive, detects changes, downloads files
- `text_processor.py` - Extracts text from PDFs/Docs, chunks it, creates embeddings
- `db_handler.py` - Inserts/updates/deletes in Supabase
- `config.json` - Settings (chunk size, file types, etc.)

---

### **STEP 2: Setup Google OAuth** (20 mins)

**What**: Get credentials so the pipeline can access YOUR Google Drive

**Process**:
1. Go to: https://console.cloud.google.com/
2. Create new project (or use existing)
3. Enable Google Drive API
4. Create OAuth 2.0 credentials
5. Download `credentials.json`
6. Run authentication flow (one-time)
7. Generates `token.json` (stores refresh token)

**Commands**:
```bash
cd /Users/joshisrael/hume-dspy-agent/rag_pipeline

# Install dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Place credentials.json in rag_pipeline/
# Run auth flow
python setup_google_auth.py

# This opens browser, you authorize, then token.json is created
```

**Security**:
- `credentials.json` - OAuth client ID (not super sensitive, but don't commit)
- `token.json` - YOUR access token (NEVER commit this!)
- Add both to `.gitignore`

---

### **STEP 3: Configure Supabase** (30 mins)

**What**: Create 3 tables + 2 functions in Supabase

#### **3.1: Create Tables**

**Table 1: `documents`** (stores chunks + embeddings)
```sql
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI embedding dimension
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for vector similarity search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for metadata queries
CREATE INDEX idx_documents_metadata ON documents USING gin(metadata);
```

**Table 2: `document_metadata`** (file info + schema)
```sql
CREATE TABLE document_metadata (
    file_id TEXT PRIMARY KEY,
    file_title TEXT NOT NULL,
    file_url TEXT,
    schema JSONB,  -- For tabular data (CSV/Sheets)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Table 3: `document_rows`** (tabular data from spreadsheets)
```sql
CREATE TABLE document_rows (
    id BIGSERIAL PRIMARY KEY,
    file_id TEXT NOT NULL,
    row_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (file_id) REFERENCES document_metadata(file_id) ON DELETE CASCADE
);

CREATE INDEX idx_document_rows_file_id ON document_rows(file_id);
CREATE INDEX idx_document_rows_data ON document_rows USING gin(row_data);
```

#### **3.2: Create RPC Functions**

**Function 1: `match_documents`** (semantic search)
```sql
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

**Function 2: `execute_custom_sql`** (for tabular queries)
```sql
CREATE OR REPLACE FUNCTION execute_custom_sql(sql_query TEXT)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    -- Validate read-only (already done in Python, but extra safety)
    IF sql_query ~* '(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)' THEN
        RETURN jsonb_build_object('error', 'Only SELECT queries allowed');
    END IF;
    
    -- Execute query and return as JSONB
    EXECUTE format('SELECT jsonb_agg(row_to_json(t)) FROM (%s) t', sql_query) INTO result;
    RETURN COALESCE(result, '[]'::jsonb);
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object('error', SQLERRM);
END;
$$;
```

#### **3.3: Enable pgvector Extension**

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**How to Run These**:
1. Go to Supabase dashboard
2. SQL Editor
3. Paste each block, run
4. Verify tables exist

---

### **STEP 4: Configure Environment Variables** (10 mins)

**What**: Add new env vars to Railway

**Add These to Railway**:
```bash
# Google Drive OAuth (from token.json)
GOOGLE_DRIVE_CREDENTIALS=<paste contents of token.json>

# OpenAI (for embeddings)
OPENAI_API_KEY=<your key>  # You already have this

# Supabase (you already have these)
SUPABASE_URL=<your url>
SUPABASE_SERVICE_KEY=<your key>

# RAG Pipeline Config
RAG_ENABLED=true
RAG_SCAN_INTERVAL=300  # Check for changes every 5 minutes
```

**Update config.json**:
```json
{
  "chunk_size": 400,
  "chunk_overlap": 0,
  "embedding_model": "text-embedding-3-small",
  "max_file_size_mb": 50,
  "supported_mime_types": [
    "application/pdf",
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "text/plain",
    "text/csv",
    "image/png",
    "image/jpeg"
  ],
  "folders_to_scan": ["root"]
}
```

---

### **STEP 5: Add RAG Tools to Agent** (30 mins)

**What**: Give Hume agent 4 new tools to query the knowledge base

**Tools to Add**:

#### **Tool 1: `retrieve_relevant_documents`**
```python
@tool
async def retrieve_relevant_documents(query: str) -> str:
    """
    Search knowledge base for documents relevant to query.
    Returns chunks of text from your business documents.
    
    Use this when you need to answer questions about:
    - Company strategy, OKRs, goals
    - Call notes, customer conversations
    - KPI data, metrics
    - SOPs, processes
    - Any business context
    """
    # Create embedding for query
    embedding = await create_embedding(query)
    
    # Search Supabase
    result = supabase.rpc('match_documents', {
        'query_embedding': embedding,
        'match_threshold': 0.7,
        'match_count': 10
    }).execute()
    
    # Format results
    docs = result.data
    return format_documents(docs)
```

#### **Tool 2: `list_documents`**
```python
@tool
async def list_documents() -> str:
    """
    List all documents in the knowledge base.
    Shows file names, types, and IDs.
    
    Use this to see what's available before querying.
    """
    result = supabase.from_('document_metadata') \
        .select('file_id, file_title, file_url') \
        .execute()
    
    return format_document_list(result.data)
```

#### **Tool 3: `get_document_content`**
```python
@tool
async def get_document_content(document_id: str) -> str:
    """
    Get full content of a specific document.
    
    Use this when you need complete context from one file,
    not just relevant chunks.
    """
    result = supabase.from_('documents') \
        .select('content') \
        .eq('metadata->>file_id', document_id) \
        .order('id') \
        .execute()
    
    # Combine all chunks
    full_content = ' '.join([chunk['content'] for chunk in result.data])
    return full_content
```

#### **Tool 4: `execute_sql_query`**
```python
@tool
async def execute_sql_query(sql_query: str) -> str:
    """
    Query tabular data (CSV files, Google Sheets) using SQL.
    
    Use this for:
    - KPI tracker queries ("Show me conversion rates")
    - Analytics ("Average deal size by month")
    - Structured data analysis
    
    Only SELECT queries allowed.
    """
    # Validate read-only
    if not is_read_only(sql_query):
        return "Error: Only SELECT queries allowed"
    
    # Execute via Supabase RPC
    result = supabase.rpc('execute_custom_sql', {
        'sql_query': sql_query
    }).execute()
    
    return format_sql_results(result.data)
```

**Where to Add**:
```
/Users/joshisrael/hume-dspy-agent/tools/rag_tools.py  (new file)
```

Then import in `agents/strategy_agent.py`:
```python
from tools.rag_tools import (
    retrieve_relevant_documents,
    list_documents,
    get_document_content,
    execute_sql_query
)
```

---

### **STEP 6: Test Locally** (30 mins)

**What**: Verify everything works before deploying

#### **6.1: Test Pipeline**
```bash
cd /Users/joshisrael/hume-dspy-agent/rag_pipeline

# Run one-time scan
python main.py --scan-once

# Expected output:
# ✅ Connected to Google Drive
# ✅ Found 131 files
# 🔄 Processing: julian talk tracks.pdf
# ✅ Extracted 5 pages, 1200 words
# ✅ Created 3 chunks
# ✅ Generated embeddings
# ✅ Inserted to Supabase
# ... (continues for all files)
```

#### **6.2: Test RAG Tools**
```python
# In Python REPL or test script
from tools.rag_tools import retrieve_relevant_documents

# Test query
result = await retrieve_relevant_documents("What are our Q1 goals?")
print(result)

# Expected: Returns chunks from OKR tracker or strategy docs
```

#### **6.3: Test Agent**
```bash
# Start agent locally
python run_agent.py

# In chat:
User: "What's our target for Q1?"
Agent: *calls retrieve_relevant_documents*
Agent: "Based on your OKR tracker, your Q1 targets are..."
```

---

### **STEP 7: Deploy to Railway** (30 mins)

**What**: Run RAG pipeline as a background worker

#### **7.1: Add to Procfile**
```
# Existing
web: python run_slack_bot.py

# Add RAG pipeline worker
worker: python rag_pipeline/main.py
```

#### **7.2: Update railway.toml**
```toml
[deploy]
startCommand = "python run_slack_bot.py"

# Add worker service
[[services]]
name = "rag-worker"
startCommand = "python rag_pipeline/main.py"
```

#### **7.3: Deploy**
```bash
git add .
git commit -m "Add RAG pipeline for knowledge base"
git push origin main

# Railway will deploy 2 services:
# 1. Main agent (Slack bot)
# 2. RAG worker (monitors Google Drive)
```

---

## 📋 **DEPENDENCIES TO ADD**

**New packages needed**:
```txt
# Add to requirements.txt

# Google Drive API
google-auth==2.23.0
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
google-api-python-client==2.100.0

# PDF extraction
pypdf==3.16.2
PyPDF2==3.0.1

# Document processing
python-docx==1.0.1
openpyxl==3.1.2

# Vector embeddings (already have OpenAI)
# No new deps needed

# Supabase pgvector (already have supabase-py)
# No new deps needed
```

---

## 🎯 **WHAT HAPPENS AFTER DEPLOYMENT**

### **Automatic Process**:
```
Every 5 minutes:
1. RAG worker checks Google Drive
2. Finds new/modified files
3. Downloads them
4. Extracts text
5. Chunks text (400 chars each)
6. Creates embeddings (OpenAI)
7. Stores in Supabase
8. Cleans up deleted files
```

### **Agent Capabilities (NEW)**:
```
✅ "What's our Q1 strategy?"
   → Searches OKR tracker, strategy docs

✅ "Show me notes from the Julian call"
   → Retrieves call transcript

✅ "What's our average deal size?"
   → Queries KPI tracker (SQL)

✅ "List all SOPs"
   → Lists operation documents

✅ "How do we handle objections?"
   → Retrieves sales playbooks
```

---

## 💰 **COST ESTIMATE**

### **One-Time Setup (42 files)**:
```
Embeddings: 42 files × ~2000 tokens × $0.00002 per 1K tokens
          = ~$1.68 one-time

Storage: 42 files × 10 chunks × 1536 dims
       = ~2 MB in Supabase (free tier handles this)
```

### **Ongoing (per month)**:
```
New files: ~10 files/month × $0.04 = $0.40
Queries: ~1000 queries/month × $0.00002 = $0.02
Total: ~$0.50/month 💰 (Very cheap!)
```

---

## 🚨 **POTENTIAL ISSUES & SOLUTIONS**

### **Issue 1: Google OAuth Expires**
**Symptom**: Pipeline stops working after 7 days  
**Solution**: Refresh token automatically (already handled in code)

### **Issue 2: File Too Large**
**Symptom**: Pipeline crashes on big PDFs  
**Solution**: Set `max_file_size_mb: 50` in config.json

### **Issue 3: Supabase Free Tier Limit**
**Symptom**: Can't insert more embeddings  
**Solution**: 
- Free tier: 500 MB (plenty for 42 files)
- If needed: Upgrade to Pro ($25/month, 8 GB)

### **Issue 4: Embedding Rate Limits**
**Symptom**: OpenAI API errors  
**Solution**: Add rate limiting in code (already implemented)

---

## ✅ **SUCCESS CRITERIA**

After implementation, you should be able to:

```
☐ RAG pipeline runs on Railway (no errors)
☐ All 42 high-priority files in Supabase
☐ Agent can list documents
☐ Agent can search documents
☐ Agent can query tabular data (KPI tracker)
☐ Agent answers business questions from docs
☐ New files automatically processed (within 5 mins)
```

---

## 📊 **TIMELINE BREAKDOWN**

```
Step 1: Copy files             →  15 mins  ⏱️
Step 2: Google OAuth           →  20 mins  ⏱️
Step 3: Supabase setup         →  30 mins  ⏱️
Step 4: Environment vars       →  10 mins  ⏱️
Step 5: Add RAG tools          →  30 mins  ⏱️
Step 6: Local testing          →  30 mins  ⏱️
Step 7: Deploy to Railway      →  30 mins  ⏱️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL:                         → 165 mins (2.75 hours)
```

**Realistically**: 3-4 hours with debugging/breaks

---

## 🎯 **RECOMMENDED APPROACH**

### **Tonight** (If you have 1 hour):
1. Copy files to repo
2. Setup Google OAuth
3. Test local scan of a few files

### **Tomorrow** (2-3 hours):
1. Setup Supabase tables/functions
2. Add RAG tools to agent
3. Test locally
4. Deploy to Railway

### **This Week**:
1. Monitor RAG worker
2. Verify all 42 files processed
3. Test agent queries
4. Add more files as needed

---

## 💡 **WHAT YOU DON'T NEED TO DO**

❌ **Upload files to a special location**
   → Your 131 files stay in Google Drive where they are!

❌ **Manually convert files**
   → RAG pipeline does this automatically

❌ **Set up complex infrastructure**
   → Uses existing Supabase + Railway

❌ **Manage embeddings yourself**
   → Pipeline handles everything

---

## 🔥 **WHAT MAKES THIS POWERFUL**

### **1. Self-Updating**
```
You add file to Google Drive
    ↓
5 minutes later...
    ↓
Agent already knows about it! ✨
```

### **2. Multi-Format**
```
Supports:
- PDFs (julian talk tracks.pdf)
- Google Docs (Meeting notes)
- Google Sheets (KPI tracker)
- Images (with OCR)
- Plain text
```

### **3. Smart Search**
```
User: "How do we handle pricing objections?"

RAG finds:
1. "Three Types Of Objections" doc
2. "julian talk tracks" PDF
3. Call notes mentioning pricing

Combines context → Perfect answer!
```

### **4. Tabular Queries**
```
User: "What's Steven's conversion rate?"

Agent writes SQL:
SELECT closer_name, 
       SUM(conversions) / SUM(calls) as rate
FROM kpi_tracker
WHERE closer_name = 'Steven'

Returns: "Steven's conversion rate is 34.5%"
```

---

## 🚀 **READY TO START?**

**I can do this now if you want!** 

**Option 1**: Start tonight (1 hour setup)
**Option 2**: Tomorrow morning (full 3-hour session)

**Want me to begin with Step 1 (copying files)?**

---

**Next Steps**: Let me know when you're ready and I'll start implementation! 🎯
