"""Agent Zero Memory System for Hume Bot.

Enhanced memory system combining:
- Agent Zero's FAISS architecture (proven, battle-tested)
- DSPy compatibility (Pydantic models, structured returns)
- Hume-specific features (lead learning, strategy optimization)

Usage:
    from memory import get_agent_memory, LeadMemory

    # Get memory instance
    memory = get_agent_memory("inbound_agent")

    # Save lead
    lead_memory = LeadMemory(
        lead_id="123",
        email="test@example.com",
        qualification_score=75,
        tier="warm"
    )
    await memory.save_lead_memory(lead_memory)

    # Search similar leads
    similar = await memory.search_similar_leads(
        query="small practice in healthcare",
        threshold=0.7
    )
"""

from memory.agent_memory import AgentMemory, get_agent_memory
from memory.models import (
    LeadMemory,
    StrategyMemory,
    InstrumentMemory,
    ConversationMemory,
    ResearchMemory,
    MemoryArea,
    LeadTier
)
from memory.memory_tools import (
    save_lead_to_memory,
    search_similar_leads,
    save_strategy_to_memory,
    save_instrument_to_memory,
    get_memory_stats
)

__all__ = [
    # Core classes
    "AgentMemory",
    "get_agent_memory",

    # Models
    "LeadMemory",
    "StrategyMemory",
    "InstrumentMemory",
    "ConversationMemory",
    "ResearchMemory",
    "MemoryArea",
    "LeadTier",

    # Tools
    "save_lead_to_memory",
    "search_similar_leads",
    "save_strategy_to_memory",
    "save_instrument_to_memory",
    "get_memory_stats",
]
