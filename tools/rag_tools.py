"""
RAG Tools for Knowledge Base Queries

These tools enable the agent to search and query the knowledge base
built from Google Drive documents.
"""
import os
import json
from typing import List, Dict, Any
from supabase import Client
from openai import AsyncOpenAI

async def retrieve_relevant_documents(
    supabase: Client,
    openai_client: AsyncOpenAI,
    query: str,
    match_threshold: float = 0.7,
    match_count: int = 10
) -> str:
    """
    Search knowledge base for documents relevant to the query.
    
    Uses semantic search with embeddings to find the most relevant
    chunks of text from your business documents.
    
    Args:
        supabase: Supabase client
        openai_client: OpenAI client for embeddings
        query: User's search query
        match_threshold: Minimum similarity threshold (0-1)
        match_count: Maximum number of results to return
        
    Returns:
        Formatted string with relevant document chunks
        
    Example:
        query = "What's our Q1 strategy?"
        results = await retrieve_relevant_documents(supabase, openai, query)
    """
    try:
        # Create embedding for the query
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = response.data[0].embedding
        
        # Search Supabase using the match_documents function
        result = supabase.rpc('match_documents', {
            'query_embedding': query_embedding,
            'match_threshold': match_threshold,
            'match_count': match_count
        }).execute()
        
        if not result.data:
            return "No relevant documents found in the knowledge base for this query."
        
        # Format results
        output = f"Found {len(result.data)} relevant document chunks:\n\n"
        
        for i, doc in enumerate(result.data, 1):
            file_title = doc['metadata'].get('file_title', 'Unknown')
            file_url = doc['metadata'].get('file_url', '')
            similarity = doc['similarity']
            content = doc['content']
            
            output += f"**Result {i}** (Similarity: {similarity:.2%})\n"
            output += f"Source: {file_title}\n"
            if file_url:
                output += f"URL: {file_url}\n"
            output += f"Content:\n{content}\n\n"
            output += "-" * 80 + "\n\n"
        
        return output
        
    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"


async def list_documents(supabase: Client) -> str:
    """
    List all documents in the knowledge base.
    
    Returns a list of all files that have been indexed,
    showing their titles and URLs.
    
    Args:
        supabase: Supabase client
        
    Returns:
        Formatted string with document list
        
    Example:
        docs = await list_documents(supabase)
    """
    try:
        result = supabase.table('document_metadata') \
            .select('file_id, file_title, file_url') \
            .execute()
        
        if not result.data:
            return "No documents found in the knowledge base. The knowledge base may be empty."
        
        output = f"**Knowledge Base Contents** ({len(result.data)} documents)\n\n"
        
        for i, doc in enumerate(result.data, 1):
            title = doc['file_title']
            url = doc.get('file_url', 'No URL')
            file_id = doc['file_id']
            
            output += f"{i}. **{title}**\n"
            output += f"   ID: {file_id}\n"
            if url != 'No URL':
                output += f"   URL: {url}\n"
            output += "\n"
        
        return output
        
    except Exception as e:
        return f"Error listing documents: {str(e)}"


async def get_document_content(supabase: Client, document_id: str) -> str:
    """
    Get the full content of a specific document.
    
    Retrieves all chunks of a document and combines them
    to show the complete content.
    
    Args:
        supabase: Supabase client
        document_id: The Google Drive file ID
        
    Returns:
        Full document content
        
    Example:
        content = await get_document_content(supabase, "abc123")
    """
    try:
        # Get document metadata first
        metadata_result = supabase.table('document_metadata') \
            .select('file_title, file_url') \
            .eq('file_id', document_id) \
            .execute()
        
        if not metadata_result.data:
            return f"Document with ID '{document_id}' not found in knowledge base."
        
        doc_info = metadata_result.data[0]
        title = doc_info['file_title']
        url = doc_info.get('file_url', '')
        
        # Get all chunks for this document
        chunks_result = supabase.table('documents') \
            .select('content, metadata') \
            .eq('metadata->>file_id', document_id) \
            .order('id') \
            .execute()
        
        if not chunks_result.data:
            return f"No content found for document '{title}' (ID: {document_id})"
        
        # Combine all chunks
        full_content = ""
        for chunk in chunks_result.data:
            full_content += chunk['content'] + " "
        
        output = f"**Document: {title}**\n"
        if url:
            output += f"URL: {url}\n"
        output += f"ID: {document_id}\n"
        output += f"\n{'-' * 80}\n\n"
        output += full_content.strip()
        
        return output
        
    except Exception as e:
        return f"Error retrieving document content: {str(e)}"


async def execute_sql_query(supabase: Client, sql_query: str) -> str:
    """
    Execute a SQL query on tabular data from the knowledge base.
    
    This allows querying structured data from spreadsheets (like KPI trackers)
    using SQL. Only SELECT queries are allowed for safety.
    
    Args:
        supabase: Supabase client
        sql_query: SQL SELECT query to execute
        
    Returns:
        Query results as formatted string
        
    Example:
        query = "SELECT closer_name, SUM(conversions) as total FROM document_rows WHERE file_id='xyz' GROUP BY closer_name"
        results = await execute_sql_query(supabase, query)
    """
    try:
        # Validate read-only
        write_operations = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']
        upper_query = sql_query.upper()
        
        for op in write_operations:
            if op in upper_query:
                return f"Error: Write operation '{op}' detected. Only read-only SELECT queries are allowed."
        
        # Execute the query using the RPC function
        result = supabase.rpc('execute_custom_sql', {
            'sql_query': sql_query
        }).execute()
        
        # Check for errors
        if isinstance(result.data, dict) and 'error' in result.data:
            return f"SQL Error: {result.data['error']}"
        
        if not result.data:
            return "Query executed successfully but returned no results."
        
        # Format results
        output = f"**Query Results** ({len(result.data)} rows)\n\n"
        output += "```json\n"
        output += json.dumps(result.data, indent=2)
        output += "\n```"
        
        return output
        
    except Exception as e:
        return f"Error executing SQL query: {str(e)}"


# Tool metadata for agent registration
RAG_TOOLS = {
    "retrieve_relevant_documents": {
        "function": retrieve_relevant_documents,
        "description": "Search knowledge base for documents relevant to a query using semantic search",
        "parameters": ["query", "match_threshold", "match_count"]
    },
    "list_documents": {
        "function": list_documents,
        "description": "List all documents in the knowledge base",
        "parameters": []
    },
    "get_document_content": {
        "function": get_document_content,
        "description": "Get the full content of a specific document by ID",
        "parameters": ["document_id"]
    },
    "execute_sql_query": {
        "function": execute_sql_query,
        "description": "Execute SQL query on tabular data from spreadsheets (read-only)",
        "parameters": ["sql_query"]
    }
}
