"""
Test script for RAG pipeline

Tests the complete flow:
1. Connect to Google Drive
2. Process a file
3. Store in Supabase
4. Test RAG search
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from drive_watcher import GoogleDriveWatcher
from supabase import create_client
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

async def test_rag_pipeline():
    """Test the complete RAG pipeline"""
    print("=" * 80)
    print("🧪 RAG PIPELINE TEST")
    print("=" * 80)
    
    # Initialize Supabase
    print("\n1️⃣ Connecting to Supabase...")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not set in .env")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Connected to Supabase")
    
    # Initialize OpenAI
    print("\n2️⃣ Connecting to OpenAI...")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        print("❌ Error: OPENAI_API_KEY not set in .env")
        return
    
    openai_client = AsyncOpenAI(api_key=openai_api_key)
    print("✅ Connected to OpenAI")
    
    # Initialize Google Drive watcher
    print("\n3️⃣ Connecting to Google Drive...")
    script_dir = Path(__file__).parent
    watcher = GoogleDriveWatcher(
        credentials_path=str(script_dir / 'credentials.json'),
        token_path=str(script_dir / 'token.json'),
        config_path=str(script_dir / 'config.json')
    )
    watcher.authenticate()
    print("✅ Connected to Google Drive")
    
    # Get changes (this will process files)
    print("\n4️⃣ Scanning Google Drive for files...")
    changed_files = watcher.get_changes()
    
    if not changed_files:
        print("⚠️  No new or changed files found")
        print("   This is expected if you've already run the scan")
    else:
        print(f"✅ Found {len(changed_files)} files to process")
        
        # Process first 3 files as a test
        test_files = changed_files[:3]
        print(f"\n5️⃣ Processing first {len(test_files)} files as test...")
        
        for i, file in enumerate(test_files, 1):
            print(f"\n   Processing {i}/{len(test_files)}: {file['name']}")
            watcher.process_file(file)
    
    # Test RAG search
    print("\n6️⃣ Testing RAG search...")
    
    # Import RAG tools
    sys.path.append(str(Path(__file__).parent.parent / 'tools'))
    from rag_tools import retrieve_relevant_documents, list_documents
    
    # List documents
    print("\n   Listing documents in knowledge base...")
    docs_list = await list_documents(supabase)
    print(docs_list)
    
    # Test search
    print("\n   Testing semantic search...")
    test_query = "KPI tracker conversion rate"
    results = await retrieve_relevant_documents(
        supabase,
        openai_client,
        test_query,
        match_threshold=0.5,
        match_count=3
    )
    print(f"\n   Query: '{test_query}'")
    print(results)
    
    print("\n" + "=" * 80)
    print("✅ RAG PIPELINE TEST COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review the results above")
    print("2. If successful, deploy to Railway")
    print("3. Add RAG tools to the Hume agent")

if __name__ == "__main__":
    asyncio.run(test_rag_pipeline())
