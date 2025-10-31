"""DSPy-compatible memory tools for Hume agents."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from memory.agent_memory import get_agent_memory
from memory.models import LeadMemory, StrategyMemory, InstrumentMemory, LeadTier

logger = logging.getLogger(__name__)


async def save_lead_to_memory(
    lead_id: str,
    email: str,
    qualification_score: int,
    tier: str,
    practice_size: Optional[str] = None,
    patient_volume: Optional[str] = None,
    industry: Optional[str] = None,
    strategy_used: Optional[str] = None,
    converted: Optional[bool] = None,
    key_insights: Optional[str] = None,
    **kwargs
) -> str:
    """Save lead memory for future learning."""
    memory = get_agent_memory("inbound_agent")

    lead_memory = LeadMemory(
        lead_id=lead_id,
        email=email,
        qualification_score=qualification_score,
        tier=LeadTier(tier.lower()),
        practice_size=practice_size,
        patient_volume=patient_volume,
        industry=industry,
        strategy_used=strategy_used,
        converted=converted,
        key_insights=key_insights,
        **kwargs
    )

    memory_id = await memory.save_lead_memory(lead_memory)
    return "Saved lead memory: " + email + " (ID: " + memory_id + ")"


async def search_similar_leads(
    query: str,
    threshold: float = 0.7,
    limit: int = 5,
    only_converted: bool = False,
    tier_filter: Optional[str] = None
) -> str:
    """Search for similar past leads."""
    memory = get_agent_memory("inbound_agent")

    filter_dict = {}
    if only_converted:
        filter_dict['converted'] = True
    if tier_filter:
        filter_dict['tier'] = tier_filter.lower()

    similar_leads = await memory.search_similar_leads(
        query=query,
        threshold=threshold,
        limit=limit,
        filter_dict=filter_dict if filter_dict else None
    )

    if not similar_leads:
        return "No similar leads found in memory."

    parts = ["Found " + str(len(similar_leads)) + " similar leads:", ""]

    for i, lead in enumerate(similar_leads, 1):
        parts.append(str(i) + ". " + lead.email + " (" + (lead.company or "Unknown") + ")")
        parts.append("   Practice: " + (lead.practice_size or "Unknown") + ", Patients: " + (lead.patient_volume or "Unknown"))
        parts.append("   Score: " + str(lead.qualification_score) + ", Tier: " + str(lead.tier))
        parts.append("   Strategy: " + (lead.strategy_used or "None"))
        parts.append("   Converted: " + str(lead.converted or "Unknown"))
        if lead.key_insights:
            parts.append("   Insights: " + lead.key_insights)
        parts.append("")

    return "\n".join(parts)


async def save_strategy_to_memory(
    strategy_name: str,
    description: str,
    success_rate: float,
    use_cases: List[str],
    target_segments: List[str],
    channels: List[str]
) -> str:
    """Save successful strategy to memory."""
    memory = get_agent_memory("strategy_agent")

    strategy_memory = StrategyMemory(
        strategy_name=strategy_name,
        description=description,
        success_rate=success_rate,
        use_cases=use_cases,
        target_segments=target_segments,
        channels=channels
    )

    memory_id = await memory.save_strategy_memory(strategy_memory)
    return "Saved strategy: " + strategy_name + " (" + str(int(success_rate*100)) + "% success)"


async def save_instrument_to_memory(
    instrument_name: str,
    description: str,
    code: str,
    created_by: str,
    use_cases: List[str],
    success_rate: float = 0.0
) -> str:
    """Save code instrument to memory."""
    memory = get_agent_memory("strategy_agent")

    instrument_memory = InstrumentMemory(
        instrument_name=instrument_name,
        description=description,
        code=code,
        created_by=created_by,
        use_cases=use_cases,
        success_rate=success_rate
    )

    memory_id = await memory.save_instrument_memory(instrument_memory)
    return "Saved instrument: " + instrument_name


def get_memory_stats(agent_name: str = "inbound_agent") -> str:
    """Get memory statistics for an agent."""
    memory = get_agent_memory(agent_name)
    stats = memory.get_stats()

    parts = ["Memory Stats for " + agent_name + ":", "Total Memories: " + str(stats['total_memories']), "", "By Area:"]
    for area, count in stats['by_area'].items():
        parts.append("  " + area + ": " + str(count))

    return "\n".join(parts)
