#!/usr/bin/env python3
"""Migrate existing leads from Supabase to Agent Zero memory system.

This script backfills 60+ existing leads into the memory system so agents
can immediately start learning from past interactions.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from config.settings import settings
from memory import get_agent_memory, LeadMemory, LeadTier
from models import LeadStatus
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_leads():
    """Migrate all existing leads to memory."""

    # Initialize Supabase client
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    # Initialize memory
    memory = get_agent_memory("inbound_agent")

    logger.info("🚀 Starting lead migration to memory...")
    logger.info(f"   Memory agent: {memory.agent_name}")

    # Get initial stats
    initial_stats = memory.get_stats()
    logger.info(f"   Initial memories: {initial_stats['total_memories']}")

    # Query all leads from Supabase
    logger.info("
📊 Querying leads from Supabase...")
    response = supabase.table('leads').select('*').execute()
    leads = response.data

    logger.info(f"   Found {len(leads)} leads to migrate")

    # Migrate each lead
    migrated = 0
    skipped = 0
    errors = 0

    for i, lead_data in enumerate(leads, 1):
        try:
            # Map Supabase lead to LeadMemory
            # Extract qualification data from lead
            qualification_score = lead_data.get('qualification_score', 0)
            tier_str = lead_data.get('tier', 'UNQUALIFIED')

            # Map tier string to LeadTier enum
            tier_map = {
                'SCORCHING': LeadTier.SCORCHING,
                'HOT': LeadTier.HOT,
                'WARM': LeadTier.WARM,
                'COOL': LeadTier.COOL,
                'COLD': LeadTier.COLD,
                'UNQUALIFIED': LeadTier.UNQUALIFIED,
            }
            tier = tier_map.get(tier_str.upper(), LeadTier.UNQUALIFIED)

            # Extract form data (stored as JSON)
            form_data = lead_data.get('form_data', {}) or {}

            # Create LeadMemory
            lead_memory = LeadMemory(
                lead_id=lead_data['id'],
                email=lead_data['email'],
                company=form_data.get('company'),
                qualification_score=qualification_score,
                tier=tier,
                practice_size=form_data.get('business_size'),
                patient_volume=form_data.get('patient_volume'),
                industry=form_data.get('industry', 'Healthcare'),
                strategy_used=lead_data.get('strategy_used'),
                converted=lead_data.get('status') == LeadStatus.CONVERTED.value,
                key_insights=lead_data.get('notes', '')[:500] if lead_data.get('notes') else None,
            )

            # Save to memory
            memory_id = await memory.save_lead_memory(lead_memory)
            migrated += 1

            if i % 10 == 0:
                logger.info(f"   Progress: {i}/{len(leads)} leads processed...")

        except Exception as e:
            logger.error(f"   ❌ Error migrating lead {lead_data.get('email', 'unknown')}: {e}")
            errors += 1

    # Final stats
    final_stats = memory.get_stats()

    logger.info("
" + "="*80)
    logger.info("
🎉 MIGRATION COMPLETE!")
    logger.info(f"
📊 Results:")
    logger.info(f"   Total leads: {len(leads)}")
    logger.info(f"   Migrated: {migrated}")
    logger.info(f"   Skipped: {skipped}")
    logger.info(f"   Errors: {errors}")
    logger.info(f"
💾 Memory Stats:")
    logger.info(f"   Before: {initial_stats['total_memories']} memories")
    logger.info(f"   After: {final_stats['total_memories']} memories")
    logger.info(f"   Added: {final_stats['total_memories'] - initial_stats['total_memories']} memories")
    logger.info(f"   By area: {final_stats['by_area']}")
    logger.info("
✅ Agents can now learn from all past leads!")


if __name__ == "__main__":
    asyncio.run(migrate_leads())
