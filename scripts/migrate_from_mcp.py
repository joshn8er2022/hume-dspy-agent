#!/usr/bin/env python3
"""Migrate leads from Supabase MCP query to memory.

This version uses the Supabase MCP tool result data directly.
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory import get_agent_memory, LeadMemory, LeadTier
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_supabase_lead(lead_data: Dict) -> LeadMemory:
    """Convert Supabase lead data to LeadMemory."""

    # Map tier string to LeadTier enum
    tier_map = {
        'scorching': LeadTier.SCORCHING,
        'hot': LeadTier.HOT,
        'warm': LeadTier.WARM,
        'cool': LeadTier.COOL,
        'cold': LeadTier.COLD,
        'unqualified': LeadTier.UNQUALIFIED,
    }

    tier_str = lead_data.get('qualification_tier', 'unqualified').lower()
    tier = tier_map.get(tier_str, LeadTier.UNQUALIFIED)

    # Extract form data
    raw_answers = lead_data.get('raw_answers', {})

    # Get business size and patient volume from raw_answers
    business_size = raw_answers.get('business_size') or raw_answers.get('07e7d388-2593-4048-a438-0da986b89fca')
    patient_volume = raw_answers.get('patient_volume') or raw_answers.get('5b8e3d56-1ca5-4ba5-a36e-ad18e09d286b')

    # Create LeadMemory
    return LeadMemory(
        lead_id=lead_data['id'],
        email=lead_data['email'],
        company=lead_data.get('company'),
        qualification_score=lead_data.get('qualification_score', 0),
        tier=tier,
        practice_size=business_size,
        patient_volume=patient_volume,
        industry='Healthcare',  # Default for all leads
        strategy_used=None,  # Will be updated when we track strategies
        converted=lead_data.get('status') == 'converted',
        key_insights=None,  # Can add later from qualification_reasoning
    )


async def migrate_from_json(json_file: str):
    """Migrate leads from JSON file to memory."""

    # Load leads from JSON
    with open(json_file, 'r') as f:
        leads_data = json.load(f)

    logger.info(f"📊 Loaded {len(leads_data)} leads from {json_file}")

    # Initialize memory
    memory = get_agent_memory("inbound_agent")
    logger.info(f"💾 Memory initialized: {memory.agent_name}")

    # Get initial stats
    initial_stats = memory.get_stats()
    logger.info(f"   Initial memories: {initial_stats['total_memories']}")

    # Migrate each lead
    migrated = 0
    errors = 0

    for i, lead_data in enumerate(leads_data, 1):
        try:
            # Parse lead
            lead_memory = parse_supabase_lead(lead_data)

            # Save to memory
            memory_id = await memory.save_lead_memory(lead_memory)
            migrated += 1

            if i % 10 == 0:
                logger.info(f"   Progress: {i}/{len(leads_data)} leads processed...")

        except Exception as e:
            logger.error(f"   ❌ Error migrating {lead_data.get('email')}: {e}")
            errors += 1

    # Final stats
    final_stats = memory.get_stats()

    logger.info("
" + "="*80)
    logger.info("
🎉 MIGRATION COMPLETE!")
    logger.info(f"
📊 Results:")
    logger.info(f"   Total leads: {len(leads_data)}")
    logger.info(f"   Migrated: {migrated}")
    logger.info(f"   Errors: {errors}")
    logger.info(f"
💾 Memory Stats:")
    logger.info(f"   Before: {initial_stats['total_memories']} memories")
    logger.info(f"   After: {final_stats['total_memories']} memories")
    logger.info(f"   Added: {final_stats['total_memories'] - initial_stats['total_memories']}")
    logger.info(f"   By area: {final_stats['by_area']}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python migrate_from_mcp.py <json_file>")
        sys.exit(1)

    asyncio.run(migrate_from_json(sys.argv[1]))
