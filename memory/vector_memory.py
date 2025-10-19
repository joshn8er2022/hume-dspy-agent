"""FAISS-backed semantic memory for agents.

This module provides persistent semantic memory using FAISS vector search,
allowing agents to remember and recall information contextually.
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)

# Check if FAISS is available
try:
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings
    from langchain.docstore.in_memory import InMemoryDocstore
    from langchain_core.documents import Document
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FAISS dependencies not available: {e}")
    FAISS_AVAILABLE = False


class MemoryType(str, Enum):
    """Types of memories that can be stored."""
    SOLUTION = "solution"           # Problem → Solution pairs
    CONVERSATION = "conversation"   # Past conversations
    RESEARCH = "research"           # Research findings
    INSIGHT = "insight"             # Strategic insights
    TOOL_RESULT = "tool_result"     # Tool execution results
    ERROR = "error"                 # Errors and fixes
    STRATEGY = "strategy"           # Strategic decisions
    LEAD_INFO = "lead_info"         # Lead information


class AgentMemory:
    """FAISS-backed semantic memory for agents.
    
    Provides:
    - Semantic search for relevant past experiences
    - Persistent storage to disk
    - Categorized memory types
    - Metadata filtering
    """
    
    def __init__(
        self,
        agent_name: str,
        embedding_dim: int = 1536,
        memory_dir: str = "./memory/storage"
    ):
        """Initialize agent memory.
        
        Args:
            agent_name: Name of the agent (for isolation)
            embedding_dim: Dimension of embeddings (1536 for OpenAI)
            memory_dir: Directory to store persistent memory
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "FAISS dependencies not installed. "
                "Install with: pip install faiss-cpu langchain langchain-openai langchain-community"
            )
        
        self.agent_name = agent_name
        self.embedding_dim = embedding_dim
        self.memory_dir = memory_dir
        self.memory_path = os.path.join(memory_dir, agent_name)
        
        # Initialize embeddings
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY required for embeddings")
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_key,
            model="text-embedding-3-small"  # Cheaper, faster
        )
        
        # Try to load existing memory, otherwise create new
        if os.path.exists(self.memory_path):
            try:
                self.vectorstore = FAISS.load_local(
                    self.memory_path,
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True  # We trust our own data
                )
                logger.info(f"✅ Loaded existing memory for {agent_name}")
            except Exception as e:
                logger.warning(f"Failed to load memory, creating new: {e}")
                self._create_new_vectorstore()
        else:
            self._create_new_vectorstore()
    
    def _create_new_vectorstore(self):
        """Create a new FAISS vectorstore."""
        # Create FAISS index
        index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product (cosine similarity)
        
        # Create empty vectorstore
        self.vectorstore = FAISS(
            embedding_function=self.embeddings,
            index=index,
            docstore=InMemoryDocstore({}),
            index_to_docstore_id={}
        )
        
        logger.info(f"✅ Created new memory for {self.agent_name}")
    
    async def remember(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a memory with semantic embeddings.
        
        Args:
            content: The content to remember
            memory_type: Type of memory (for filtering)
            metadata: Additional metadata
        
        Returns:
            Memory ID
        """
        # Build metadata
        doc_metadata = {
            "agent": self.agent_name,
            "type": memory_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        # Create document
        doc = Document(
            page_content=content,
            metadata=doc_metadata
        )
        
        # Add to vectorstore
        ids = await self.vectorstore.aadd_documents([doc])
        
        logger.debug(f"💾 Remembered ({memory_type}): {content[:100]}...")
        
        return ids[0] if ids else None
    
    def remember_sync(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Synchronous version of remember()."""
        doc_metadata = {
            "agent": self.agent_name,
            "type": memory_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        doc = Document(page_content=content, metadata=doc_metadata)
        ids = self.vectorstore.add_documents([doc])
        
        logger.debug(f"💾 Remembered ({memory_type}): {content[:100]}...")
        
        return ids[0] if ids else None
    
    async def recall(
        self,
        query: str,
        k: int = 5,
        memory_type: Optional[MemoryType] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memories via semantic search.
        
        Args:
            query: Search query
            k: Number of results to return
            memory_type: Filter by memory type (optional)
            min_score: Minimum relevance score (0.0 to 1.0)
        
        Returns:
            List of memory dicts with content, metadata, and relevance_score
        """
        try:
            # Build filter
            filter_dict = {"agent": self.agent_name}
            if memory_type:
                filter_dict["type"] = memory_type.value
            
            # Semantic search with scores
            results = await self.vectorstore.asimilarity_search_with_relevance_scores(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            # Filter by minimum score and format
            memories = []
            for doc, score in results:
                if score >= min_score:
                    memories.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": float(score),
                        "timestamp": doc.metadata.get("timestamp", "unknown")
                    })
            
            logger.debug(f"🔍 Recalled {len(memories)} memories for: {query[:50]}...")
            
            return memories
        
        except Exception as e:
            logger.error(f"Failed to recall memories: {e}")
            return []
    
    def recall_sync(
        self,
        query: str,
        k: int = 5,
        memory_type: Optional[MemoryType] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Synchronous version of recall()."""
        try:
            filter_dict = {"agent": self.agent_name}
            if memory_type:
                filter_dict["type"] = memory_type.value
            
            results = self.vectorstore.similarity_search_with_relevance_scores(
                query=query,
                k=k,
                filter=filter_dict
            )
            
            memories = []
            for doc, score in results:
                if score >= min_score:
                    memories.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": float(score),
                        "timestamp": doc.metadata.get("timestamp", "unknown")
                    })
            
            logger.debug(f"🔍 Recalled {len(memories)} memories for: {query[:50]}...")
            
            return memories
        
        except Exception as e:
            logger.error(f"Failed to recall memories: {e}")
            return []
    
    def save(self):
        """Persist memory to disk."""
        try:
            os.makedirs(self.memory_dir, exist_ok=True)
            self.vectorstore.save_local(self.memory_path)
            logger.info(f"💾 Saved memory for {self.agent_name} to {self.memory_path}")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        try:
            total_memories = self.vectorstore.index.ntotal
            return {
                "agent": self.agent_name,
                "total_memories": total_memories,
                "embedding_dim": self.embedding_dim,
                "memory_path": self.memory_path
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    def clear(self):
        """Clear all memories (use with caution!)."""
        self._create_new_vectorstore()
        logger.warning(f"🗑️ Cleared all memories for {self.agent_name}")


# Singleton instances for each agent
_memory_instances: Dict[str, AgentMemory] = {}


def get_agent_memory(agent_name: str) -> Optional[AgentMemory]:
    """Get or create memory instance for an agent.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        AgentMemory instance or None if FAISS not available
    """
    if not FAISS_AVAILABLE:
        return None
    
    if agent_name not in _memory_instances:
        try:
            _memory_instances[agent_name] = AgentMemory(agent_name)
        except Exception as e:
            logger.error(f"Failed to create memory for {agent_name}: {e}")
            return None
    
    return _memory_instances[agent_name]
