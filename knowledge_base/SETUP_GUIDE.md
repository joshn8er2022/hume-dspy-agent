# 📚 Knowledge Base Setup Guide

**Complete guide to loading your business knowledge into Hume's RAG system**

Based on your n8n workflow architecture, adapted for Python.

---

## 🎯 **WHAT YOU NEED**

### ✅ **You Already Have**:
1. Supabase (Postgres with pgvector)
2. OpenAI API key
3. Business documents and data

### 🔧 **What We're Adding**:
1. Document loaders (PDF, Docx, Markdown, CSV, etc.)
2. Text chunking (RecursiveCharacterTextSplitter)
3. Embeddings (OpenAI text-embedding-3-small)
4. Loading pipeline (kb_loader.py)

---

## 📋 **SETUP STEPS**

### **Step 1: Install Dependencies**

```bash
# Install knowledge base dependencies
pip install -r knowledge_base/requirements.txt

# OR install individually:
pip install langchain langchain-openai langchain-community supabase pypdf docx2txt unstructured
```

### **Step 2: Configure Environment Variables**

Add to your `.env` file:

```bash
# Already have these:
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
OPENAI_API_KEY=sk-...

# All set! No new keys needed.
```

### **Step 3: Setup Supabase Database**

Run this SQL **ONCE** in your Supabase SQL Editor:

```sql
-- Enable pgvector extension (if not already enabled)
create extension if not exists vector;

-- Create knowledge_base table (separate from agent memory)
create table if not exists knowledge_base (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(1536),
  created_at timestamptz default now()
);

-- Create search function for RAG retrieval
create or replace function match_knowledge_base (
  query_embedding vector(1536),
  match_count int default 5,
  filter jsonb DEFAULT '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    content,
    metadata,
    1 - (knowledge_base.embedding <=> query_embedding) as similarity
  from knowledge_base
  where metadata @> filter
  order by knowledge_base.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Create index for faster similarity search
create index if not exists knowledge_base_embedding_idx 
on knowledge_base 
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
```

**Verify it worked:**
```sql
-- Check if table exists
SELECT * FROM knowledge_base LIMIT 1;

-- Check if function exists
SELECT match_knowledge_base(ARRAY[0.1]::vector(1536), 5);
```

---

## 📁 **ORGANIZING YOUR KNOWLEDGE BASE**

### **Directory Structure**

Create this structure in `/knowledge_base/`:

```
/knowledge_base/
  ├── kb_loader.py          # Loader script (already created)
  ├── requirements.txt      # Dependencies (already created)
  ├── SETUP_GUIDE.md       # This file
  │
  ├── /business/           # Business fundamentals
  │   ├── company_overview.md
  │   ├── unit_economics.md
  │   ├── target_markets.md
  │   └── capacity_infrastructure.md
  │
  ├── /strategy/           # Strategic context
  │   ├── icp_profile.md
  │   ├── messaging_framework.md
  │   ├── competitive_positioning.md
  │   └── value_propositions.md
  │
  ├── /playbooks/          # Sales playbooks
  │   ├── qualification_criteria.md
  │   ├── objection_handling.md
  │   ├── follow_up_sequences.md
  │   └── closing_techniques.md
  │
  ├── /intelligence/       # Market intelligence
  │   ├── competitor_analysis.md
  │   ├── market_trends.md
  │   ├── customer_insights.md
  │   └── segment_performance.md
  │
  └── /derived/           # Auto-generated (by agents)
      └── .gitkeep        # Agents will write here
```

### **Supported File Types**

| Type | Extension | Use Case |
|------|-----------|----------|
| **Markdown** | `.md` | Best for structured business docs |
| **PDF** | `.pdf` | Presentations, reports, case studies |
| **Word** | `.docx` | Legacy docs, proposals |
| **Text** | `.txt` | Simple notes, lists |
| **CSV** | `.csv` | Tabular data (optional) |
| **Excel** | `.xlsx` | Spreadsheets (optional) |

**Recommendation**: Use **Markdown (.md)** for your core knowledge base
- Easy to edit
- Version control friendly
- Clean formatting
- AI-readable

---

## 📝 **CREATING KNOWLEDGE BASE CONTENT**

### **Option 1: Manual Creation** (Most Accurate)

Create markdown files with your business knowledge:

**Example: `/knowledge_base/business/company_overview.md`**

```markdown
# Hume Health - Company Overview

## Business Model
**Product**: Medical aesthetic devices
**Target Markets**: Medical practices, med spas, dental clinics
**Geography**: [Your primary markets]

## Unit Economics
- **Cost**: $35/unit
- **Retail**: $229-290/unit  
- **Margin**: 85% (~$200/unit)

## Deal Structures

### Standard Deal
[Describe your standard pricing]

### Premium Deal
- Offer: 3 free units ($105 value) with $50K purchase
- ROI: 2,100% for customer
- Use case: Large dental practices, multi-location med spas

### Volume Discounts
[Your volume pricing tiers]

## Current Capacity
- **Email**: 35 inboxes × 35 emails/day = 1,225 emails/day
- **LinkedIn**: 5-6 accounts
- **SMS**: Activating (Twilio)
- **Voice**: VAPI calls (testing)
```

**Example: `/knowledge_base/strategy/icp_profile.md`**

```markdown
# Ideal Customer Profile (ICP)

## Primary Segments

### 1. Dental Clinics (Best Performer)
**Conversion Rate**: 32%

**Profile**:
- Revenue: $X+ annually
- Size: X+ chairs/practitioners
- Technology adoption: Early adopters
- Pain points: [Key challenges]

**Decision Makers**:
- Primary: Practice owner / Lead dentist
- Secondary: Office manager
- Buying cycle: X months typical

**Why They Convert**:
1. [Reason 1]
2. [Reason 2]
3. [Reason 3]

**Best Messaging**:
- Focus on: [Key value props]
- Avoid: [What doesn't resonate]

---

### 2. Med Spas
**Conversion Rate**: 18%

**Profile**:
- Revenue: $X+ annually
- Size: X+ treatment rooms
- Technology adoption: Moderate
- Pain points: [Key challenges]

**Decision Makers**:
- Primary: [Who decides]
- Buying cycle: X months typical

**Why Lower Conversion**:
1. [Challenge 1]
2. [Challenge 2]

**Optimization Strategy**:
- [How to improve]
```

---

### **Option 2: Extract from Google Docs** (Fastest)

If you have existing Google Docs:

1. **Export as Markdown**:
   - Use Google Docs → Download → Plain Text (.txt)
   - Convert to Markdown (or just save as .txt)
   - Place in appropriate `/knowledge_base/` folder

2. **Use document_analyst** (once KB is ready):
   ```
   In Slack: "Extract all docs from my Google Drive folder 'Hume Business' 
   and convert them to markdown for knowledge base"
   ```

---

### **Option 3: Agent-Assisted Creation** (Collaborative)

Have the agent interview you:

```
In Slack: "I want to build our knowledge base. Start with company overview. 
Ask me questions and create a markdown file from my answers."
```

Agent will:
1. Ask structured questions
2. Capture your responses
3. Generate markdown file
4. You review and refine

---

## 🚀 **LOADING KNOWLEDGE BASE**

### **Load Your Documents**

```bash
# From hume-dspy-agent directory
cd knowledge_base

# Print database setup SQL (run this once in Supabase)
python kb_loader.py --setup

# Load all documents into Supabase
python kb_loader.py --load

# Clear existing and reload (if updating)
python kb_loader.py --load --clear

# Test retrieval
python kb_loader.py --test "What's our unit economics?"
```

### **What Happens**:

1. **Discovery** (5-10 sec)
   - Scans `/knowledge_base/` for all supported files
   - Finds: Markdown, PDF, Docx, TXT files

2. **Loading** (10-30 sec)
   - Extracts text from each file
   - Adds metadata (source, type, category, timestamp)

3. **Chunking** (5-10 sec)
   - Splits documents into 400-char chunks
   - 50-char overlap for context continuity
   - Preserves semantic boundaries (paragraphs, sentences)

4. **Embedding** (30-60 sec)
   - Generates vector embeddings (OpenAI text-embedding-3-small)
   - 1536 dimensions per chunk
   - Cost: ~$0.0001 per 1,000 chars (very cheap)

5. **Storage** (10-20 sec)
   - Stores in Supabase `knowledge_base` table
   - Indexes for fast similarity search

### **Expected Output**:

```
================================================================================
🚀 STARTING KNOWLEDGE BASE INDEXING PIPELINE
================================================================================

📚 LOADING KNOWLEDGE BASE
================================================================================
📄 Loading markdown files...
   Found 12 markdown files
   ✅ Loaded: company_overview.md
   ✅ Loaded: unit_economics.md
   ✅ Loaded: icp_profile.md
   ...

✅ Loaded 12 total documents

✂️  Chunking documents (400 chars, 50 overlap)...
   12 documents → 247 chunks
   Average: 20.6 chunks per document

💾 Loading to Supabase...
   Loaded batch 1/5
   Loaded batch 2/5
   ...

================================================================================
🎉 KNOWLEDGE BASE INDEXING COMPLETE!
================================================================================
   Documents loaded: 12
   Chunks created: 247
   Storage: Supabase (knowledge_base table)
   Embeddings: OpenAI text-embedding-3-small
```

---

## 🔍 **TESTING RETRIEVAL**

### **Test RAG Search**:

```bash
python kb_loader.py --test "What's our ICP for dental clinics?"
```

Expected output:
```
🔍 Testing retrieval: 'What's our ICP for dental clinics?'

📊 Found 5 results:

   Result 1 (score: 0.892):
   Source: strategy/icp_profile.md
   Content: # Ideal Customer Profile (ICP)

## Primary Segments

### 1. Dental Clinics (Best Performer)
**Conversion Rate**: 32%

**Profile**:
- Revenue: $500K+ annually
- Size: 3+ chairs/practitioners
...

   Result 2 (score: 0.856):
   Source: playbooks/qualification_criteria.md
   Content: ## HOT Tier (Immediate Action)

For Dental:
- Revenue: $500K+
- Location: Major metro markets
- Technology: EMR/EHR adoption
...
```

### **Common Test Queries**:

```bash
# Business fundamentals
python kb_loader.py --test "What are our unit economics?"
python kb_loader.py --test "Who are our target customers?"
python kb_loader.py --test "What's our capacity?"

# Strategy
python kb_loader.py --test "What's our ICP?"
python kb_loader.py --test "How do we position against competitors?"
python kb_loader.py --test "What's our messaging for med spas?"

# Sales process
python kb_loader.py --test "How do we qualify HOT leads?"
python kb_loader.py --test "What are common objections?"
python kb_loader.py --test "What's our follow-up sequence?"

# Market intelligence
python kb_loader.py --test "Who are our main competitors?"
python kb_loader.py --test "What's the medical aesthetics market trend?"
```

---

## 🔌 **INTEGRATING WITH AGENT**

### **Step 1: Add Knowledge Base Tool to Strategy Agent**

The agent already has `search_knowledge_base` tool ready (Phase 1.5.5 prep).

Just needs knowledge base to be populated (which you're doing now).

### **Step 2: Update System Context**

Agent's system context will automatically show:
```json
{
  "knowledge_base": {
    "status": "✅ Populated",
    "documents": 12,
    "chunks": 247,
    "categories": ["business", "strategy", "playbooks", "intelligence"]
  }
}
```

### **Step 3: Test in Slack**

```
You: "What's our ICP for dental clinics?"

Agent: "Querying knowledge base...

Based on our ICP documentation:

**Dental Clinics (Best Performer)**
- Conversion Rate: 32% (vs 18% med spas)
- Profile: $500K+ revenue, 3+ chairs, early tech adopters
- Decision Maker: Practice owner/lead dentist
- Buying Cycle: 3-4 months typical

**Why They Convert**:
1. High margins justify premium equipment
2. Patient volume supports ROI
3. Competitive differentiation in market

**Best Messaging**: Focus on patient outcomes, efficiency gains, and competitive edge."
```

---

## 📊 **WHAT'S DIFFERENT FROM N8N**

Your n8n workflow and this Python implementation are architecturally identical:

| Component | n8n Workflow | Python Implementation |
|-----------|--------------|----------------------|
| **Embeddings** | OpenAI text-embedding-3-small | ✅ Same |
| **Chunk Size** | 400 chars | ✅ Same |
| **Chunk Overlap** | Not specified (default 50) | ✅ 50 chars |
| **Splitter** | RecursiveCharacterTextSplitter | ✅ Same |
| **Vector DB** | Supabase (pgvector) | ✅ Same |
| **Table** | `documents` | `knowledge_base` (separate) |
| **Search Function** | `match_documents` | `match_knowledge_base` |
| **File Support** | PDF, Docx, CSV, Excel | ✅ Same + Markdown |

**Key Difference**: 
- n8n: Watches Google Drive for new files (automated)
- Python: One-time load + manual updates (simpler for KB)

**For Hume**: Python approach is better for knowledge base (static business docs)
- n8n approach is better for dynamic docs (incoming lead files, etc.)

---

## 🔄 **UPDATING KNOWLEDGE BASE**

### **Adding New Documents**:

```bash
# 1. Add new .md file to /knowledge_base/
echo "# New Document" > knowledge_base/strategy/new_doc.md

# 2. Reload (keeps existing, adds new)
python kb_loader.py --load

# OR clear and reload everything
python kb_loader.py --load --clear
```

### **Modifying Existing Documents**:

```bash
# 1. Edit the markdown file
vim knowledge_base/business/company_overview.md

# 2. Reload with --clear to replace
python kb_loader.py --load --clear
```

### **Best Practice**:
- Keep knowledge base in version control (Git)
- Review changes before reloading
- Test retrieval after updates

---

## ⚠️ **TROUBLESHOOTING**

### **Issue: "Missing dependencies"**

```bash
pip install -r knowledge_base/requirements.txt
```

### **Issue: "OPENAI_API_KEY not found"**

Add to `.env`:
```bash
OPENAI_API_KEY=sk-...
```

### **Issue: "Supabase connection failed"**

Check `.env`:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key  # NOT anon key!
```

### **Issue: "No documents found"**

Check directory:
```bash
ls -la knowledge_base/business/
# Should show .md files
```

### **Issue: "Table 'knowledge_base' does not exist"**

Run setup SQL in Supabase SQL Editor (Step 3 above)

---

## 💰 **COST ESTIMATE**

### **Embedding Costs**:
- Model: text-embedding-3-small
- Cost: $0.00002 per 1,000 tokens (~750 words)
- Your KB: ~12 docs × ~2,000 words = 24,000 words
- Tokens: ~32,000 tokens
- **Total Cost: ~$0.64 one-time**

### **Storage**:
- Supabase: Included in free tier (500MB)
- Vectors: ~247 chunks × 6KB = ~1.5MB
- **Cost: $0 (within free tier)**

### **Retrieval**:
- Supabase: Free for all queries
- **Cost: $0**

**Total Setup Cost: ~$0.64** (one-time)  
**Ongoing Cost: $0**

---

## ✅ **CHECKLIST**

- [ ] Install dependencies (`pip install -r knowledge_base/requirements.txt`)
- [ ] Add credentials to `.env` (SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY)
- [ ] Run setup SQL in Supabase SQL Editor
- [ ] Create directory structure (`/business/`, `/strategy/`, etc.)
- [ ] Create/export markdown files with business knowledge
- [ ] Load documents (`python kb_loader.py --load`)
- [ ] Test retrieval (`python kb_loader.py --test "..."`)
- [ ] Test in Slack ("What's our ICP?")

---

## 🎯 **NEXT STEPS**

1. **Create 5 Core Documents** (Start Here):
   - `business/company_overview.md`
   - `business/unit_economics.md`
   - `strategy/icp_profile.md`
   - `playbooks/qualification_criteria.md`
   - `intelligence/competitor_analysis.md`

2. **Load and Test**:
   ```bash
   python kb_loader.py --load
   python kb_loader.py --test "What's our ICP?"
   ```

3. **Iterate**:
   - Add more documents as needed
   - Refine based on agent usage
   - Review agent's retrieval accuracy

---

**Questions?** Check the main docs or ask the agent! 🤖
