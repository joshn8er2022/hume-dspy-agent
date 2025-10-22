"""Pure Python Agent Memory with FAISS (no LangChain dependencies).

DSPy-aligned architecture: explicit, lean, optimizable.
Direct usage of faiss-cpu and sentence-transformers.
"""

import logging
import os
import json
import pickle
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from memory.models import (
    LeadMemory, StrategyMemory, InstrumentMemory,
    ConversationMemory, ResearchMemory, MemoryArea
)

logger = logging.getLogger(__name__)


class AgentMemory:
    """Pure Python memory system with FAISS vector storage.

    No LangChain dependencies - uses faiss-cpu and sentence-transformers directly.
    Explicit operations, full control, DSPy-aligned philosophy.
    """

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

        # Initialize sentence-transformers model (explicit)
        logger.info(f"Loading embedding model: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        self.dimension = self.embedding_model.get_sentence_embedding_dimension()
        logger.info(f"✅ Embedding model loaded (dimension: {self.dimension})")

        # Initialize FAISS index (explicit)
        self.index = None
        self.metadata = {}  # id -> {area, data, timestamp}
        self.id_to_index = {}  # memory_id -> faiss_index_position
        self.index_to_id = {}  # faiss_index_position -> memory_id

        # Load existing index if available
        self._load_from_disk()

        # Create new index if needed
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dimension)
            logger.info(f"✅ Created new FAISS index (dimension: {self.dimension})")

        logger.info(f"✅ Memory initialized for {agent_name}")

    def _load_from_disk(self):
        """Load FAISS index and metadata from disk (explicit)."""
        index_path = self.db_dir / "index.faiss"
        metadata_path = self.db_dir / "metadata.json"
        mappings_path = self.db_dir / "mappings.pkl"

        if index_path.exists() and metadata_path.exists():
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(index_path))

                # Load metadata
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)

                # Load mappings
                if mappings_path.exists():
                    with open(mappings_path, 'rb') as f:
                        mappings = pickle.load(f)
                        self.id_to_index = mappings['id_to_index']
                        self.index_to_id = mappings['index_to_id']

                logger.info(f"✅ Loaded existing index ({len(self.metadata)} memories)")
            except Exception as e:
                logger.warning(f"Failed to load index: {e}")
                self.index = None

    def _save_to_disk(self):
        """Save FAISS index and metadata to disk (explicit)."""
        try:
            # Save FAISS index
            index_path = self.db_dir / "index.faiss"
            faiss.write_index(self.index, str(index_path))

            # Save metadata
            metadata_path = self.db_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)

            # Save mappings
            mappings_path = self.db_dir / "mappings.pkl"
            with open(mappings_path, 'wb') as f:
                pickle.dump({
                    'id_to_index': self.id_to_index,
                    'index_to_id': self.index_to_id
                }, f)

            logger.debug(f"💾 Saved index to {index_path}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def _lead_to_text(self, lead: LeadMemory) -> str:
        """Convert lead to searchable text (explicit)."""
        parts = [
            f"Email: {lead.email}",
            f"Company: {lead.company or 'Unknown'}",
            f"Practice Size: {lead.practice_size or 'Unknown'}",
            f"Patient Volume: {lead.patient_volume or 'Unknown'}",
            f"Industry: {lead.industry}",
            f"Tier: {lead.tier}",
            f"Score: {lead.qualification_score}",
        ]

        if lead.key_insights:
            parts.append(f"Insights: {lead.key_insights}")

        if lead.strategy_used:
            parts.append(f"Strategy: {lead.strategy_used}")

        return " | ".join(parts)

    async def save_lead_memory(self, lead: LeadMemory) -> str:
        """Save lead to memory (explicit operations)."""
        # Generate embedding (explicit)
        text = self._lead_to_text(lead)
        embedding = self.embedding_model.encode([text])[0]

        # Generate unique ID
        memory_id = str(uuid.uuid4())

        # Add to FAISS index (explicit)
        current_index = self.index.ntotal
        self.index.add(np.array([embedding], dtype=np.float32))

        # Store metadata (explicit)
        self.metadata[memory_id] = {
            'area': MemoryArea.LEADS.value,
            'data': lead.dict(),
            'timestamp': datetime.now().isoformat(),
        }

        # Update mappings (explicit)
        self.id_to_index[memory_id] = current_index
        self.index_to_id[current_index] = memory_id

        # Persist to disk (explicit)
        self._save_to_disk()

        logger.info(f"💾 Saved lead memory: {lead.email} (ID: {memory_id})")
        return memory_id

    async def search_similar_leads(
        self,
        query: str,
        threshold: float = 0.7,
        limit: int = 5,
        only_converted: bool = False,
        filter_dict: Optional[Dict] = None
    ) -> List[LeadMemory]:
        """Search for similar leads (explicit operations)."""
        if self.index.ntotal == 0:
            return []

        # Generate query embedding (explicit)
        query_embedding = self.embedding_model.encode([query])[0]

        # Search FAISS index (explicit)
        # L2 distance: lower is more similar
        distances, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32),
            min(limit * 2, self.index.ntotal)  # Get extra for filtering
        )

        # Convert distances to similarity scores (explicit)
        # Normalize L2 distances to 0-1 similarity
        max_distance = np.max(distances[0]) if len(distances[0]) > 0 else 1.0
        similarities = 1 - (distances[0] / max_distance) if max_distance > 0 else np.ones_like(distances[0])

        # Filter and build results (explicit)
        results = []
        for idx, similarity in zip(indices[0], similarities):
            # Skip if below threshold
            if similarity < threshold:
                continue

            # Get memory ID
            memory_id = self.index_to_id.get(idx)
            if not memory_id:
                continue

            # Get metadata
            meta = self.metadata.get(memory_id)
            if not meta or meta['area'] != MemoryArea.LEADS.value:
                continue

            # Create LeadMemory object
            lead = LeadMemory(**meta['data'])

            # Apply filters (explicit)
            if only_converted and not lead.converted:
                continue

            if filter_dict:
                skip = False
                for key, value in filter_dict.items():
                    if getattr(lead, key, None) != value:
                        skip = True
                        break
                if skip:
                    continue

            results.append(lead)

            # Stop if we have enough
            if len(results) >= limit:
                break

        return results

    async def save_strategy_memory(self, strategy: StrategyMemory) -> str:
        """Save strategy to memory."""
        # Similar to save_lead_memory but for strategies
        text = f"Strategy: {strategy.strategy_name} | {strategy.description} | Success: {strategy.success_rate}"
        embedding = self.embedding_model.encode([text])[0]

        memory_id = str(uuid.uuid4())
        current_index = self.index.ntotal
        self.index.add(np.array([embedding], dtype=np.float32))

        self.metadata[memory_id] = {
            'area': MemoryArea.STRATEGIES.value,
            'data': strategy.dict(),
            'timestamp': datetime.now().isoformat(),
        }

        self.id_to_index[memory_id] = current_index
        self.index_to_id[current_index] = memory_id

        self._save_to_disk()
        return memory_id

    async def save_instrument_memory(self, instrument: InstrumentMemory) -> str:
        """Save instrument to memory."""
        text = f"Instrument: {instrument.instrument_name} | {instrument.description}"
        embedding = self.embedding_model.encode([text])[0]

        memory_id = str(uuid.uuid4())
        current_index = self.index.ntotal
        self.index.add(np.array([embedding], dtype=np.float32))

        self.metadata[memory_id] = {
            'area': MemoryArea.INSTRUMENTS.value,
            'data': instrument.dict(),
            'timestamp': datetime.now().isoformat(),
        }

        self.id_to_index[memory_id] = current_index
        self.index_to_id[current_index] = memory_id

        self._save_to_disk()
        return memory_id

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics (explicit)."""
        by_area = {}
        for meta in self.metadata.values():
            area = meta['area']
            by_area[area] = by_area.get(area, 0) + 1

        return {
            'total_memories': len(self.metadata),
            'by_area': by_area,
            'agent_name': self.agent_name,
        }


# Singleton pattern for memory instances
_memory_instances = {}

def get_agent_memory(agent_name: str) -> AgentMemory:
    """Get or create memory instance for agent (singleton)."""
    if agent_name not in _memory_instances:
        _memory_instances[agent_name] = AgentMemory(agent_name)
    return _memory_instances[agent_name]
