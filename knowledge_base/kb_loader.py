"""
Knowledge Base Loader for Hume Health

Loads business documents into Supabase vector database for RAG.

Supports:
- Markdown (.md)
- PDF (.pdf)
- Word Docs (.docx)
- Google Docs (via export)
- Text files (.txt)
- CSV/Excel (structured data)

Architecture (based on n8n workflow):
1. Load files from /knowledge_base/ directory
2. Extract text content (file-type specific)
3. Chunk text (400 chars, 50 overlap)
4. Generate embeddings (OpenAI text-embedding-3-small)
5. Store in Supabase with pgvector
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check dependencies
try:
    from langchain_community.document_loaders import (
        DirectoryLoader,
        TextLoader,
        UnstructuredMarkdownLoader,
        PyPDFLoader,
        Docx2txtLoader,
        CSVLoader,
        UnstructuredExcelLoader
    )
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import SupabaseVectorStore
    from supabase import create_client, Client
    DEPS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Missing dependencies: {e}")
    logger.error("Install with: pip install langchain langchain-openai langchain-community supabase pypdf docx2txt unstructured")
    DEPS_AVAILABLE = False


class KnowledgeBaseLoader:
    """Load and index business knowledge base for RAG"""
    
    def __init__(
        self,
        kb_dir: str = "./knowledge_base",
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        openai_key: Optional[str] = None
    ):
        """Initialize knowledge base loader
        
        Args:
            kb_dir: Directory containing knowledge base files
            supabase_url: Supabase project URL (or from env)
            supabase_key: Supabase service key (or from env)
            openai_key: OpenAI API key (or from env)
        """
        if not DEPS_AVAILABLE:
            raise ImportError("Required dependencies not installed")
        
        self.kb_dir = Path(kb_dir)
        
        # Get credentials from env if not provided
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        
        if not all([self.supabase_url, self.supabase_key, self.openai_key]):
            raise ValueError(
                "Missing credentials. Set SUPABASE_URL, SUPABASE_KEY, and OPENAI_API_KEY"
            )
        
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Initialize embeddings (same as n8n: text-embedding-3-small)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=self.openai_key
        )
        
        # Initialize text splitter (same as n8n: 400 chars)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=50,  # 50 char overlap for context
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        logger.info(f"✅ Knowledge Base Loader initialized")
        logger.info(f"   Directory: {self.kb_dir}")
        logger.info(f"   Embeddings: text-embedding-3-small")
        logger.info(f"   Chunk size: 400 chars (50 overlap)")
    
    def setup_database(self):
        """Create pgvector extension and documents table in Supabase
        
        This matches the n8n workflow's database setup.
        Run this ONCE to initialize the database.
        """
        logger.info("🔧 Setting up Supabase database for knowledge base...")
        
        # SQL from n8n workflow
        setup_sql = """
        -- Enable pgvector extension
        create extension if not exists vector;
        
        -- Create knowledge_base table (separate from agent memory)
        create table if not exists knowledge_base (
          id bigserial primary key,
          content text,
          metadata jsonb,
          embedding vector(1536),
          created_at timestamptz default now()
        );
        
        -- Create search function for RAG
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
        """
        
        try:
            # Execute via Supabase SQL editor or use psycopg2
            # For now, user should run this manually in Supabase SQL editor
            logger.info("⚠️  Please run the following SQL in Supabase SQL Editor:")
            print("\n" + "="*80)
            print(setup_sql)
            print("="*80 + "\n")
            logger.info("After running SQL, call load_documents() to load files")
            
            return setup_sql
        
        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise
    
    def load_markdown_files(self) -> List[Dict[str, Any]]:
        """Load all markdown files from knowledge base"""
        logger.info("📄 Loading markdown files...")
        
        md_files = list(self.kb_dir.rglob("*.md"))
        logger.info(f"   Found {len(md_files)} markdown files")
        
        documents = []
        for file_path in md_files:
            try:
                loader = UnstructuredMarkdownLoader(str(file_path))
                docs = loader.load()
                
                # Add metadata
                for doc in docs:
                    doc.metadata.update({
                        "source": str(file_path.relative_to(self.kb_dir)),
                        "type": "markdown",
                        "category": file_path.parent.name,
                        "filename": file_path.name,
                        "loaded_at": datetime.utcnow().isoformat()
                    })
                
                documents.extend(docs)
                logger.info(f"   ✅ Loaded: {file_path.name}")
            
            except Exception as e:
                logger.error(f"   ❌ Failed to load {file_path.name}: {e}")
        
        return documents
    
    def load_pdf_files(self) -> List[Dict[str, Any]]:
        """Load all PDF files from knowledge base"""
        logger.info("📑 Loading PDF files...")
        
        pdf_files = list(self.kb_dir.rglob("*.pdf"))
        logger.info(f"   Found {len(pdf_files)} PDF files")
        
        documents = []
        for file_path in pdf_files:
            try:
                loader = PyPDFLoader(str(file_path))
                docs = loader.load()
                
                for doc in docs:
                    doc.metadata.update({
                        "source": str(file_path.relative_to(self.kb_dir)),
                        "type": "pdf",
                        "category": file_path.parent.name,
                        "filename": file_path.name,
                        "loaded_at": datetime.utcnow().isoformat()
                    })
                
                documents.extend(docs)
                logger.info(f"   ✅ Loaded: {file_path.name}")
            
            except Exception as e:
                logger.error(f"   ❌ Failed to load {file_path.name}: {e}")
        
        return documents
    
    def load_docx_files(self) -> List[Dict[str, Any]]:
        """Load all Word documents from knowledge base"""
        logger.info("📝 Loading Word documents...")
        
        docx_files = list(self.kb_dir.rglob("*.docx"))
        logger.info(f"   Found {len(docx_files)} Word files")
        
        documents = []
        for file_path in docx_files:
            try:
                loader = Docx2txtLoader(str(file_path))
                docs = loader.load()
                
                for doc in docs:
                    doc.metadata.update({
                        "source": str(file_path.relative_to(self.kb_dir)),
                        "type": "docx",
                        "category": file_path.parent.name,
                        "filename": file_path.name,
                        "loaded_at": datetime.utcnow().isoformat()
                    })
                
                documents.extend(docs)
                logger.info(f"   ✅ Loaded: {file_path.name}")
            
            except Exception as e:
                logger.error(f"   ❌ Failed to load {file_path.name}: {e}")
        
        return documents
    
    def load_text_files(self) -> List[Dict[str, Any]]:
        """Load all text files from knowledge base"""
        logger.info("📃 Loading text files...")
        
        txt_files = list(self.kb_dir.rglob("*.txt"))
        logger.info(f"   Found {len(txt_files)} text files")
        
        documents = []
        for file_path in txt_files:
            try:
                loader = TextLoader(str(file_path))
                docs = loader.load()
                
                for doc in docs:
                    doc.metadata.update({
                        "source": str(file_path.relative_to(self.kb_dir)),
                        "type": "txt",
                        "category": file_path.parent.name,
                        "filename": file_path.name,
                        "loaded_at": datetime.utcnow().isoformat()
                    })
                
                documents.extend(docs)
                logger.info(f"   ✅ Loaded: {file_path.name}")
            
            except Exception as e:
                logger.error(f"   ❌ Failed to load {file_path.name}: {e}")
        
        return documents
    
    def load_all_documents(self) -> List[Dict[str, Any]]:
        """Load all supported document types"""
        logger.info("\n" + "="*80)
        logger.info("📚 LOADING KNOWLEDGE BASE")
        logger.info("="*80)
        
        all_documents = []
        
        # Load each file type
        all_documents.extend(self.load_markdown_files())
        all_documents.extend(self.load_pdf_files())
        all_documents.extend(self.load_docx_files())
        all_documents.extend(self.load_text_files())
        
        logger.info(f"\n✅ Loaded {len(all_documents)} total documents")
        
        return all_documents
    
    def chunk_documents(self, documents: List[Any]) -> List[Any]:
        """Split documents into chunks for RAG"""
        logger.info(f"\n✂️  Chunking documents (400 chars, 50 overlap)...")
        
        chunks = self.text_splitter.split_documents(documents)
        
        logger.info(f"   {len(documents)} documents → {len(chunks)} chunks")
        logger.info(f"   Average: {len(chunks) / len(documents):.1f} chunks per document")
        
        return chunks
    
    def load_to_supabase(
        self,
        chunks: List[Any],
        clear_existing: bool = False
    ):
        """Load chunks into Supabase vector store
        
        Args:
            chunks: Document chunks to load
            clear_existing: If True, clear existing knowledge base first
        """
        logger.info(f"\n💾 Loading to Supabase...")
        
        if clear_existing:
            logger.info("   🗑️  Clearing existing knowledge base...")
            try:
                self.supabase.table("knowledge_base").delete().neq("id", 0).execute()
                logger.info("   ✅ Cleared existing data")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not clear: {e}")
        
        try:
            # Create vector store
            vector_store = SupabaseVectorStore(
                client=self.supabase,
                embedding=self.embeddings,
                table_name="knowledge_base",
                query_name="match_knowledge_base"
            )
            
            # Add documents in batches (avoid rate limits)
            batch_size = 50
            total = len(chunks)
            
            for i in range(0, total, batch_size):
                batch = chunks[i:i+batch_size]
                vector_store.add_documents(batch)
                logger.info(f"   Loaded batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
            
            logger.info(f"\n✅ Successfully loaded {total} chunks to Supabase!")
            
            return vector_store
        
        except Exception as e:
            logger.error(f"\n❌ Failed to load to Supabase: {e}")
            raise
    
    def load_and_index(self, clear_existing: bool = False):
        """Complete pipeline: load, chunk, embed, and store
        
        Args:
            clear_existing: If True, clear existing knowledge base first
        """
        logger.info("\n" + "="*80)
        logger.info("🚀 STARTING KNOWLEDGE BASE INDEXING PIPELINE")
        logger.info("="*80)
        
        # Step 1: Load documents
        documents = self.load_all_documents()
        
        if not documents:
            logger.error("❌ No documents found! Check your /knowledge_base/ directory")
            return
        
        # Step 2: Chunk documents
        chunks = self.chunk_documents(documents)
        
        # Step 3: Generate embeddings and load to Supabase
        vector_store = self.load_to_supabase(chunks, clear_existing=clear_existing)
        
        logger.info("\n" + "="*80)
        logger.info("🎉 KNOWLEDGE BASE INDEXING COMPLETE!")
        logger.info("="*80)
        logger.info(f"   Documents loaded: {len(documents)}")
        logger.info(f"   Chunks created: {len(chunks)}")
        logger.info(f"   Storage: Supabase (knowledge_base table)")
        logger.info(f"   Embeddings: OpenAI text-embedding-3-small")
        
        return {
            "documents": len(documents),
            "chunks": len(chunks),
            "vector_store": vector_store
        }
    
    def test_retrieval(self, query: str, k: int = 5):
        """Test RAG retrieval
        
        Args:
            query: Test query
            k: Number of results to retrieve
        """
        logger.info(f"\n🔍 Testing retrieval: '{query}'")
        
        try:
            vector_store = SupabaseVectorStore(
                client=self.supabase,
                embedding=self.embeddings,
                table_name="knowledge_base",
                query_name="match_knowledge_base"
            )
            
            results = vector_store.similarity_search_with_relevance_scores(
                query,
                k=k
            )
            
            logger.info(f"\n📊 Found {len(results)} results:")
            for i, (doc, score) in enumerate(results, 1):
                logger.info(f"\n   Result {i} (score: {score:.3f}):")
                logger.info(f"   Source: {doc.metadata.get('source', 'unknown')}")
                logger.info(f"   Content: {doc.page_content[:200]}...")
            
            return results
        
        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            raise


def main():
    """CLI for knowledge base loading"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load knowledge base into Supabase")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Print SQL setup commands"
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Load documents into Supabase"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing knowledge base before loading"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Test retrieval with a query"
    )
    parser.add_argument(
        "--kb-dir",
        type=str,
        default="./knowledge_base",
        help="Knowledge base directory (default: ./knowledge_base)"
    )
    
    args = parser.parse_args()
    
    try:
        loader = KnowledgeBaseLoader(kb_dir=args.kb_dir)
        
        if args.setup:
            loader.setup_database()
        
        elif args.load:
            loader.load_and_index(clear_existing=args.clear)
        
        elif args.test:
            loader.test_retrieval(args.test)
        
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
