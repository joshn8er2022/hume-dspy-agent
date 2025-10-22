"""Enhanced Agent Memory with Agent Zero Architecture.

Simplified for LangChain 1.0.1 compatibility.
Uses sentence-transformers directly (no caching layer for now).
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.embeddings import HuggingFaceEmbeddings
import faiss
import numpy as np

from memory.models import (
    LeadMemory, StrategyMemory, InstrumentMemory,
    ConversationMemory, ResearchMemory, MemoryArea
)

logger = logging.getLogger(__name__)


class AgentMemory:
    """Enhanced memory system with Agent Zero architecture."""

    def __init__(
        self,
        agent_name: str,
        memory_dir: str = "./memory",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.agent_name = agent_name
        self.memory_dir = Path(memory_dir)
        self.db_dir = self.memory_dir / "db" / agent_name

        # Create directories
        self.db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)

        # Load or create FAISS index
        self.vectorstore = self._load_or_create_vectorstore()

        logger.info(f"✅ Memory initialized for {agent_name}")

    def _load_or_create_vectorstore(self) -> FAISS:
        """Load existing vectorstore or create new one."""
        index_path = self.db_dir / "index.faiss"

        if index_path.exists():
            try:
                vectorstore = FAISS.load_local(
                    str(self.db_dir),
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info(f"Loaded existing memory for {self.agent_name}")
                return vectorstore
            except Exception as e:
                logger.warning(f"Failed to load memory, creating new: {e}")

        # Create new vectorstore
        embedding_dim = len(self.embeddings.embed_query("test"))
        index = faiss.IndexFlatIP(embedding_dim)

        vectorstore = FAISS(
            embedding_function=self.embeddings,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={}
        )

        logger.info(f"Created new memory for {self.agent_name}")
        return vectorstore

    async def save_lead_memory(self, lead_memory: LeadMemory) -> str:
        """Save lead memory."""
        text = f"""Lead: {lead_memory.email}
Company: {lead_memory.company or 'Unknown'}
Practice Size: {lead_memory.practice_size or 'Unknown'}
Patient Volume: {lead_memory.patient_volume or 'Unknown'}
Industry: {lead_memory.industry or 'Unknown'}
Qualification Score: {lead_memory.qualification_score}
Tier: {lead_memory.tier}
Strategy Used: {lead_memory.strategy_used or 'None'}
Converted: {lead_memory.converted or 'Unknown'}
Key Insights: {lead_memory.key_insights or 'None'}
"""

        metadata = lead_memory.dict()
        metadata['id'] = f"lead_{lead_memory.lead_id}_{int(datetime.utcnow().timestamp())}"
        metadata['timestamp'] = datetime.utcnow().isoformat()
        metadata['area'] = MemoryArea.LEADS.value

        doc = Document(page_content=text, metadata=metadata)
        ids = await self.vectorstore.aadd_documents([doc])
        self.vectorstore.save_local(str(self.db_dir))

        logger.info(f"💾 Saved lead memory: {lead_memory.email} (tier: {lead_memory.tier})")
        return ids[0]

    async def search_similar_leads(
        self,
        query: str,
        threshold: float = 0.7,
        limit: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[LeadMemory]:
        """Search for similar past leads."""
        def filter_fn(metadata: dict) -> bool:
            if not filter_dict:
                return metadata.get('area') == MemoryArea.LEADS.value
            if metadata.get('area') != MemoryArea.LEADS.value:
                return False
            for key, value in filter_dict.items():
                if metadata.get(key) != value:
                    return False
            return True

        results = await self.vectorstore.asimilarity_search_with_score(
            query, k=limit, filter=filter_fn
        )

        lead_memories = []
        for doc, score in results:
            if score >= threshold:
                try:
                    lead_memory = LeadMemory(**doc.metadata)
                    lead_memories.append(lead_memory)
                except Exception as e:
                    logger.warning(f"Failed to parse lead memory: {e}")

        logger.info(f"🔍 Found {len(lead_memories)} similar leads")
        return lead_memories

    async def save_strategy_memory(self, strategy_memory: StrategyMemory) -> str:
        """Save strategy memory."""
        text = f"""Strategy: {strategy_memory.strategy_name}
Description: {strategy_memory.description}
Success Rate: {strategy_memory.success_rate:.1%}
Use Cases: {', '.join(strategy_memory.use_cases)}
"""
        metadata = strategy_memory.dict()
        metadata['id'] = f"strategy_{strategy_memory.strategy_name}_{int(datetime.utcnow().timestamp())}"
        metadata['timestamp'] = datetime.utcnow().isoformat()

        doc = Document(page_content=text, metadata=metadata)
        ids = await self.vectorstore.aadd_documents([doc])
        self.vectorstore.save_local(str(self.db_dir))

        logger.info(f"💾 Saved strategy: {strategy_memory.strategy_name}")
        return ids[0]

    async def save_instrument_memory(self, instrument_memory: InstrumentMemory) -> str:
        """Save instrument memory."""
        text = f"""Instrument: {instrument_memory.instrument_name}
Description: {instrument_memory.description}
Code:
{instrument_memory.code}
"""
        metadata = instrument_memory.dict()
        metadata['id'] = f"instrument_{instrument_memory.instrument_name}_{int(datetime.utcnow().timestamp())}"
        metadata['timestamp'] = datetime.utcnow().isoformat()

        doc = Document(page_content=text, metadata=metadata)
        ids = await self.vectorstore.aadd_documents([doc])
        self.vectorstore.save_local(str(self.db_dir))

        logger.info(f"💾 Saved instrument: {instrument_memory.instrument_name}")
        return ids[0]

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        all_docs = self.vectorstore.docstore._dict
        stats = {
            "total_memories": len(all_docs),
            "by_area": {},
            "agent_name": self.agent_name
        }
        for doc_id, doc in all_docs.items():
            area = doc.metadata.get('area', 'unknown')
            stats['by_area'][area] = stats['by_area'].get(area, 0) + 1
        return stats


_memory_instances: Dict[str, AgentMemory] = {}

def get_agent_memory(agent_name: str) -> AgentMemory:
    """Get or create memory instance for an agent."""
    if agent_name not in _memory_instances:
        _memory_instances[agent_name] = AgentMemory(agent_name)
    return _memory_instances[agent_name]
