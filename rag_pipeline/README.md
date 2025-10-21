# 🚀 RAG Pipeline - Google Drive Integration

**Status**: ✅ Code Ready | ⏳ Awaiting Google OAuth Setup

This directory contains the RAG (Retrieval Augmented Generation) pipeline that monitors your Google Drive, extracts text from documents, creates embeddings, and stores them in Supabase for semantic search.

---

## 📁 **Files**

```
rag_pipeline/
├── main.py                  # Entry point - runs the pipeline
├── drive_watcher.py         # Monitors Google Drive for changes
├── config.json              # Configuration (file types, chunk size, etc.)
├── common/
│   ├── text_processor.py    # Text extraction, chunking, embeddings
│   └── db_handler.py        # Supabase operations
├── credentials.json         # 🔴 REQUIRED: Google OAuth credentials (YOU NEED TO ADD)
└── token.json              # 🔴 AUTO-GENERATED: After first auth
```

---

## 🎯 **What It Does**

### **Continuous Monitoring**
```
Every 5 minutes:
1. Check Google Drive for new/changed files
2. Download files
3. Extract text (PDF, Docs, Sheets, etc.)
4. Chunk text (400 chars per chunk)
5. Create embeddings (OpenAI)
6. Store in Supabase
7. Detect deleted files → Remove from DB
```

### **Supported File Types**
- 📄 **PDFs** - Extracted with pypdf
- 📝 **Google Docs** - Exported as plain text
- 📊 **Google Sheets** - Exported as CSV (tabular data)
- 🖼️ **Images** - Stored with OCR capability
- 📑 **Plain text, Markdown, HTML**

---

## ⚙️ **Setup Required**

### **Step 1: Google OAuth Credentials** ⏳ **YOU NEED TO DO THIS**

1. Go to: https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable **Google Drive API**
4. Create OAuth 2.0 credentials:
   - Application type: **Desktop app**
   - Download as `credentials.json`
5. Place `credentials.json` in `/Users/joshisrael/hume-dspy-agent/rag_pipeline/`

### **Step 2: First-Time Authentication**

```bash
cd /Users/joshisrael/hume-dspy-agent/rag_pipeline

# Run authentication flow
python main.py --scan-once

# This will:
# 1. Open browser for Google auth
# 2. You approve access
# 3. Creates token.json (stores refresh token)
# 4. Scans your Drive for files
```

### **Step 3: Supabase Setup** ⏳ **NEXT TASK**

Create 3 tables in Supabase:
- `documents` - Stores text chunks + embeddings
- `document_metadata` - File info + schema
- `document_rows` - Tabular data from spreadsheets

SQL scripts will be provided in the next step.

---

## 🚀 **Usage**

### **One-Time Scan** (Testing)
```bash
python rag_pipeline/main.py --scan-once
```
Scans all files once and exits. Good for initial setup.

### **Continuous Monitoring** (Production)
```bash
python rag_pipeline/main.py --interval 300
```
Checks every 5 minutes (300 seconds) for changes.

### **Watch Specific Folder**
```bash
python rag_pipeline/main.py --folder-id "1JbPfUeqLKIHlwlT0FUy1Yj6HM1BI5U4T"
```
Only monitors a specific folder and its subfolders.

---

## 🔐 **Environment Variables**

Add these to `.env`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-...
```

---

## 📊 **Configuration** (`config.json`)

```json
{
  "supported_mime_types": [
    "application/pdf",
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "text/csv",
    "image/png",
    ...
  ],
  "text_processing": {
    "default_chunk_size": 400,
    "default_chunk_overlap": 0
  },
  "watch_folder_id": null,  // Set to watch specific folder
  "last_check_time": "1970-01-01T00:00:00.000Z"  // Auto-updated
}
```

---

## 🗄️ **Supabase Schema** (To Be Created)

### **Table 1: documents**
Stores text chunks with vector embeddings for semantic search.

### **Table 2: document_metadata**
Stores file metadata (title, URL, schema for tabular files).

### **Table 3: document_rows**
Stores individual rows from tabular files (CSV, Sheets) for SQL queries.

SQL creation scripts coming in next step!

---

## 🔍 **How Agent Uses It**

Once setup is complete, the Hume agent will have 4 new RAG tools:

1. **`retrieve_relevant_documents`**
   ```
   User: "What's our Q1 strategy?"
   Agent: *searches vector DB* → Returns relevant chunks
   ```

2. **`list_documents`**
   ```
   Agent: *lists all files in KB*
   ```

3. **`get_document_content`**
   ```
   Agent: *retrieves full content of specific file*
   ```

4. **`execute_sql_query`**
   ```
   User: "What's Steven's conversion rate?"
   Agent: *queries KPI tracker spreadsheet data*
   ```

---

## 📈 **Cost Estimate**

### **One-Time (42 files)**
- Embeddings: ~$1.68
- Storage: 2 MB in Supabase (free tier)

### **Monthly**
- New files: ~$0.40
- Queries: ~$0.02
- **Total: ~$0.50/month** 💰

---

## 🚨 **Next Steps**

1. ✅ **RAG pipeline code** - COMPLETE
2. ⏳ **Google OAuth setup** - YOU NEED TO DO THIS
3. ⏳ **Supabase tables** - SQL scripts coming next
4. ⏳ **Add RAG tools to agent** - Code coming next
5. ⏳ **Test locally** - After OAuth + Supabase setup
6. ⏳ **Deploy to Railway** - Final step

---

## 🐛 **Troubleshooting**

### **Issue: "credentials.json not found"**
**Solution**: Download from Google Cloud Console and place in this directory

### **Issue: "Token expired"**
**Solution**: Delete `token.json` and re-authenticate

### **Issue: "Supabase connection failed"**
**Solution**: Check `.env` file has correct `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`

---

**Status**: Code ready, awaiting your Google OAuth credentials! 🚀
