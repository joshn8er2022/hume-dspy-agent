"""
Strategy Agent Tools - Complete Toolkit

Combines all tools available to the Strategy Agent:
- Pipeline analysis
- Supabase queries
- CRM operations
- RAG knowledge base queries (NEW!)
- Wolfram Alpha strategic intelligence (NEW!)
- MCP tool orchestration
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

# Initialize clients (lazy load)
_supabase_client = None
_openai_client = None

def get_supabase() -> Client:
    """Get or create Supabase client"""
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if url and key:
            _supabase_client = create_client(url, key)
    return _supabase_client

def get_openai() -> AsyncOpenAI:
    """Get or create OpenAI client"""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


# ============================================================================
# RAG KNOWLEDGE BASE TOOLS
# ============================================================================

async def search_knowledge_base(query: str, limit: int = 5) -> str:
    """
    Search the knowledge base (87 indexed Google Drive files) for relevant information.
    
    Uses semantic search across 11,325 text chunks from business documents including:
    - Strategy documents
    - Meeting notes
    - KPI trackers
    - Operations docs
    - Product specs
    
    Args:
        query: What to search for (e.g., "Q1 strategy", "Julian's feedback", "KPI trends")
        limit: Maximum number of results (default: 5)
        
    Returns:
        Relevant document excerpts with sources
        
    Example:
        results = await search_knowledge_base("What did Julian say about Q1 plans?")
    """
    try:
        supabase = get_supabase()
        openai = get_openai()
        
        if not supabase or not openai:
            return "❌ Knowledge base not configured (missing Supabase or OpenAI credentials)"
        
        # Create embedding for query
        response = await openai.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Search knowledge base
        result = supabase.rpc('match_documents', {
            'query_embedding': query_embedding,
            'match_threshold': 0.7,
            'match_count': limit
        }).execute()
        
        if not result.data:
            return f"📭 No relevant documents found for: '{query}'\n\nTry:\n- Broader search terms\n- Different phrasing\n- Check if document was indexed"
        
        # Format results
        output = f"🔍 **Knowledge Base Search**: '{query}'\n\n"
        output += f"**Found {len(result.data)} relevant documents:**\n\n"
        
        for i, doc in enumerate(result.data, 1):
            output += f"**{i}. {doc.get('file_title', 'Untitled')}**\n"
            output += f"   Relevance: {doc.get('similarity', 0):.0%}\n"
            output += f"   Content: {doc.get('content', 'No content')[:300]}...\n"
            output += f"   Source: {doc.get('file_url', 'No URL')}\n\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return f"❌ Error searching knowledge base: {str(e)}"


async def list_indexed_documents() -> str:
    """
    List all documents currently in the knowledge base.
    
    Shows:
    - File names
    - File types
    - When indexed
    - Number of chunks/rows
    
    Returns:
        Formatted list of all indexed documents
    """
    try:
        supabase = get_supabase()
        if not supabase:
            return "❌ Knowledge base not configured"
        
        # Get all document metadata
        result = supabase.table('document_metadata').select('*').order('created_at', desc=True).execute()
        
        if not result.data:
            return "📭 No documents indexed yet"
        
        output = f"📚 **Knowledge Base Inventory** ({len(result.data)} files)\n\n"
        
        for doc in result.data:
            output += f"**{doc['file_title']}**\n"
            output += f"   ID: {doc['file_id']}\n"
            output += f"   Indexed: {doc['created_at']}\n"
            output += f"   URL: {doc.get('file_url', 'N/A')}\n\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return f"❌ Error: {str(e)}"


async def query_spreadsheet_data(file_name: str, query_description: str) -> str:
    """
    Query data from indexed spreadsheets using natural language.
    
    Works with KPI trackers, appointment logs, order data, etc.
    
    Args:
        file_name: Name of spreadsheet (e.g., "Steven Closer KPI Tracker")
        query_description: What to find (e.g., "conversion rate last week")
        
    Returns:
        Query results from spreadsheet
        
    Example:
        data = await query_spreadsheet_data("KPI Tracker", "Steven's stats this month")
    """
    try:
        supabase = get_supabase()
        if not supabase:
            return "❌ Knowledge base not configured"
        
        # Find file ID
        file_result = supabase.table('document_metadata').select('file_id').ilike('file_title', f'%{file_name}%').execute()
        
        if not file_result.data:
            return f"❌ Spreadsheet not found: '{file_name}'\n\nTry: list_indexed_documents() to see available files"
        
        file_id = file_result.data[0]['file_id']
        
        # Get spreadsheet rows
        rows_result = supabase.table('document_rows').select('*').eq('file_id', file_id).limit(100).execute()
        
        if not rows_result.data:
            return f"📭 No data found in: '{file_name}'"
        
        output = f"📊 **{file_name}** ({len(rows_result.data)} rows)\n\n"
        output += f"Query: {query_description}\n\n"
        
        # Show first 10 rows as sample
        for i, row in enumerate(rows_result.data[:10], 1):
            output += f"Row {i}: {json.dumps(row.get('row_data', {}), indent=2)[:200]}...\n\n"
        
        if len(rows_result.data) > 10:
            output += f"... and {len(rows_result.data) - 10} more rows\n"
        
        return output
        
    except Exception as e:
        logger.error(f"Error querying spreadsheet: {e}")
        return f"❌ Error: {str(e)}"


# ============================================================================
# WOLFRAM ALPHA STRATEGIC INTELLIGENCE
# ============================================================================

async def wolfram_market_insight(query: str) -> str:
    """
    Get strategic market intelligence from Wolfram Alpha.
    
    Use for:
    - Market size comparisons
    - Economic indicators
    - Demographic data
    - Healthcare spending patterns
    - Income statistics
    
    Args:
        query: Strategic question (e.g., "healthcare spending US vs Europe")
        
    Returns:
        Computational analysis from Wolfram Alpha
        
    Example:
        data = await wolfram_market_insight("median income California vs Texas")
    """
    try:
        from tools.wolfram_alpha import wolfram_strategic_query
        return await wolfram_strategic_query(query)
    except ImportError:
        return "❌ Wolfram Alpha not installed (pip install tools/wolfram_alpha.py)"
    except Exception as e:
        logger.error(f"Wolfram error: {e}")
        return f"❌ Error: {str(e)}"


# ============================================================================
# TOOL REGISTRY
# ============================================================================

STRATEGY_TOOLS = {
    # RAG Knowledge Base (NEW!)
    "search_knowledge_base": search_knowledge_base,
    "list_indexed_documents": list_indexed_documents,
    "query_spreadsheet_data": query_spreadsheet_data,
    
    # Strategic Intelligence (NEW!)
    "wolfram_market_insight": wolfram_market_insight,
}


# Export all tools for easy import
__all__ = [
    "search_knowledge_base",
    "list_indexed_documents",
    "query_spreadsheet_data",
    "wolfram_market_insight",
    "STRATEGY_TOOLS"
]
