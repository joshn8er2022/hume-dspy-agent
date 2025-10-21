#!/bin/bash
# Knowledge Base Quick Start Script

set -e  # Exit on error

echo "📚 Hume Knowledge Base - Quick Start"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "kb_loader.py" ]; then
    echo "❌ Error: Must run from knowledge_base/ directory"
    echo "   cd knowledge_base && ./quickstart.sh"
    exit 1
fi

# Step 1: Create directory structure
echo "📁 Step 1: Creating directory structure..."
mkdir -p business strategy playbooks intelligence derived
echo "   ✅ Created: business/, strategy/, playbooks/, intelligence/, derived/"

# Step 2: Copy templates
echo ""
echo "📝 Step 2: Setting up template files..."
if [ -f "business/company_overview.md.template" ]; then
    echo "   Templates available in each directory"
    echo "   Copy and customize: cp *.template *.md"
else
    echo "   ⚠️  No templates found (optional)"
fi

# Step 3: Check dependencies
echo ""
echo "🔧 Step 3: Checking dependencies..."
if python3 -c "import langchain" 2>/dev/null; then
    echo "   ✅ LangChain installed"
else
    echo "   ❌ LangChain not installed"
    echo "   Install with: pip install -r requirements.txt"
    exit 1
fi

# Step 4: Check environment variables
echo ""
echo "🔐 Step 4: Checking environment variables..."
if [ -z "$SUPABASE_URL" ]; then
    echo "   ❌ SUPABASE_URL not set"
    echo "   Add to .env: SUPABASE_URL=https://your-project.supabase.co"
    exit 1
else
    echo "   ✅ SUPABASE_URL configured"
fi

if [ -z "$SUPABASE_KEY" ]; then
    echo "   ❌ SUPABASE_KEY not set"
    echo "   Add to .env: SUPABASE_KEY=your-service-role-key"
    exit 1
else
    echo "   ✅ SUPABASE_KEY configured"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "   ❌ OPENAI_API_KEY not set"
    echo "   Add to .env: OPENAI_API_KEY=sk-..."
    exit 1
else
    echo "   ✅ OPENAI_API_KEY configured"
fi

# Step 5: Check if database is setup
echo ""
echo "🗄️  Step 5: Checking database setup..."
echo "   Run this SQL in Supabase SQL Editor (if not done):"
echo ""
python3 kb_loader.py --setup
echo ""

# Step 6: Count documents
echo "📊 Step 6: Checking for documents..."
DOC_COUNT=$(find . -name "*.md" -not -name "*.template" -not -name "README.md" -not -name "SETUP_GUIDE.md" | wc -l | tr -d ' ')
echo "   Found $DOC_COUNT markdown documents"

if [ "$DOC_COUNT" -eq 0 ]; then
    echo ""
    echo "⚠️  No documents found!"
    echo ""
    echo "Next steps:"
    echo "1. Create markdown files in business/, strategy/, etc."
    echo "2. Use templates: cp *.md.template *.md"
    echo "3. Or extract from Google Docs"
    echo "4. Then run: python3 kb_loader.py --load"
    exit 0
fi

# Step 7: Offer to load
echo ""
echo "🚀 Ready to load knowledge base!"
echo ""
read -p "Load $DOC_COUNT documents into Supabase? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Loading knowledge base..."
    python3 kb_loader.py --load
    
    echo ""
    echo "✅ Knowledge base loaded!"
    echo ""
    echo "Test retrieval:"
    echo "  python3 kb_loader.py --test 'What is our ICP?'"
else
    echo ""
    echo "Skipped loading. Run manually:"
    echo "  python3 kb_loader.py --load"
fi

echo ""
echo "======================================"
echo "📚 Quick Start Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Test retrieval: python3 kb_loader.py --test 'your query'"
echo "2. Add more documents to knowledge_base/"
echo "3. Reload: python3 kb_loader.py --load --clear"
echo "4. Test in Slack: 'What's our ICP?'"
echo ""
