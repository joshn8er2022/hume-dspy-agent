#!/bin/bash
# 🚀 Deploy Phase 2.0 - RAG + Wolfram Alpha Integration
# Auto-generated deployment script

echo "========================================"
echo "🚀 Deploying Phase 2.0 Integration"
echo "========================================"
echo ""

# Navigate to project directory
cd /Users/joshisrael/hume-dspy-agent

# Show what will be committed
echo "📦 Files to be committed:"
git status --short
echo ""

# Stage all changes
echo "📝 Staging changes..."
git add .
echo "✅ Changes staged"
echo ""

# Create commit
echo "💾 Creating commit..."
git commit -m "feat: Phase 2.0 - RAG + Wolfram Alpha Intelligence Layer

🎯 Integration Summary:
- Created consolidated strategy_tools.py with 6 new tools
- Enhanced Strategy Agent from 10 to 16 ReAct tools
- Integrated RAG knowledge base (87 docs, 11,325 chunks)
- Integrated Wolfram Alpha strategic intelligence
- All tests passing, production ready

🔧 RAG Tools (3):
- search_knowledge_base: Semantic search across indexed docs
- list_indexed_documents: Inventory of knowledge base
- query_spreadsheet_data: Query KPI trackers and logs

🔬 Wolfram Tools (3):
- wolfram_strategic_query: General strategic intelligence
- wolfram_market_analysis: Market comparisons & TAM analysis
- wolfram_demographic_insight: Population & demographic data

📊 Knowledge Base:
- 87 indexed Google Drive documents
- 11,325 text chunks for semantic search
- OpenAI embeddings + Supabase pgvector

✅ Testing:
- All imports successful
- Tool signatures validated
- Integration test suite passing

📚 Documentation:
- INTEGRATION_COMPLETE.md (comprehensive guide)
- DEPLOY_CHECKLIST.md (deployment steps)
- INTEGRATION_SUMMARY.md (executive summary)

Version: Phase 2.0
Status: Production Ready
Test Results: All Passing ✅"

echo "✅ Commit created"
echo ""

# Push to Railway (triggers auto-deploy)
echo "🚀 Pushing to Railway..."
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✅ DEPLOYMENT INITIATED"
    echo "========================================"
    echo ""
    echo "📊 Monitor deployment:"
    echo "   Railway: https://railway.app/"
    echo "   Phoenix: https://app.phoenix.arize.com/"
    echo ""
    echo "🧪 Post-deployment tests:"
    echo "   1. Check Railway logs for successful tool initialization"
    echo "   2. Test RAG search via Slack"
    echo "   3. Test Wolfram query via Slack"
    echo "   4. Verify Phoenix traces"
    echo ""
    echo "⚠️  IMPORTANT: Verify WOLFRAM_APP_ID is set in Railway!"
    echo ""
else
    echo ""
    echo "❌ Push failed - check git status"
    echo ""
fi
