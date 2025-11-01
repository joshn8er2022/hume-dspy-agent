"""Async Supabase client utility for proper async/await operations.

This module provides a singleton async Supabase client that can be properly
awaited throughout the async application. This fixes the sync/async mismatch
that was causing agent_state inserts to fail silently.
"""
import os
import logging
from typing import Optional
from supabase import create_client, Client
from supabase._async.client import AsyncClient, create_async_client

logger = logging.getLogger(__name__)

# Singleton instances
_sync_client: Optional[Client] = None
_async_client: Optional[AsyncClient] = None


def get_sync_supabase_client() -> Client:
    """Get or create synchronous Supabase client (for non-async contexts).

    Returns:
        Synchronous Supabase client

    Note:
        Use this ONLY in synchronous functions. For async functions,
        use get_async_supabase_client() instead.
    """
    global _sync_client

    if _sync_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = (
            os.getenv("SUPABASE_SERVICE_KEY") or
            os.getenv("SUPABASE_KEY") or
            os.getenv("SUPABASE_ANON_KEY")
        )

        if not supabase_url or not supabase_key:
            raise ValueError(
                "Missing Supabase credentials. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
            )

        _sync_client = create_client(supabase_url, supabase_key)
        logger.info("✅ Sync Supabase client initialized")

    return _sync_client


async def get_async_supabase_client() -> AsyncClient:
    """Get or create async Supabase client (for async/await contexts).

    Returns:
        Async Supabase client

    Note:
        This is the RECOMMENDED client for all async functions.
        Properly supports await operations.

    Example:
        async def save_data():
            supabase = await get_async_supabase_client()
            await supabase.table('leads').insert({...}).execute()
    """
    global _async_client

    if _async_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = (
            os.getenv("SUPABASE_SERVICE_KEY") or
            os.getenv("SUPABASE_KEY") or
            os.getenv("SUPABASE_ANON_KEY")
        )

        if not supabase_url or not supabase_key:
            raise ValueError(
                "Missing Supabase credentials. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
            )

        _async_client = await create_async_client(supabase_url, supabase_key)
        logger.info("✅ Async Supabase client initialized")

    return _async_client


async def save_agent_state(
    agent_name: str,
    lead_id: str,
    state_data: dict,
    status: str = "completed"
) -> dict:
    """Save agent execution state to database.

    Args:
        agent_name: Name of the agent (e.g., 'StrategyAgent', 'InboundAgent')
        lead_id: UUID of the lead being processed
        state_data: Dictionary of state data (will be stored as JSONB)
        status: Execution status ('active', 'completed', 'failed')

    Returns:
        dict: Inserted record from database

    Raises:
        Exception: If database insert fails

    Example:
        await save_agent_state(
            agent_name='InboundAgent',
            lead_id=str(lead.id),
            state_data={
                'qualification_tier': 'HOT',
                'qualification_score': 85,
                'reasoning': 'High patient volume, immediate need'
            },
            status='completed'
        )
    """
    try:
        supabase = await get_async_supabase_client()

        result = await supabase.table('agent_state').insert({
            'agent_name': agent_name,
            'lead_id': lead_id,
            'state_data': state_data,
            'status': status
        }).execute()

        logger.info(f"✅ Saved {agent_name} state for lead {lead_id[:8]}... (status: {status})")
        return result.data[0] if result.data else {}

    except Exception as e:
        logger.error(f"❌ Failed to save {agent_name} state for lead {lead_id}: {e}")
        # Re-raise so calling code knows save failed
        raise


async def get_agent_state(agent_name: str, lead_id: str) -> Optional[dict]:
    """Retrieve agent state for a specific lead.

    Args:
        agent_name: Name of the agent
        lead_id: UUID of the lead

    Returns:
        dict: Most recent state record, or None if not found
    """
    try:
        supabase = await get_async_supabase_client()

        result = await supabase.table('agent_state') \
            .select('*') \
            .eq('agent_name', agent_name) \
            .eq('lead_id', lead_id) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()

        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"❌ Failed to get {agent_name} state for lead {lead_id}: {e}")
        return None


async def get_all_agent_states(lead_id: str) -> list[dict]:
    """Retrieve all agent states for a lead (full execution history).

    Args:
        lead_id: UUID of the lead

    Returns:
        list: All state records for this lead, ordered by creation time
    """
    try:
        supabase = await get_async_supabase_client()

        result = await supabase.table('agent_state') \
            .select('*') \
            .eq('lead_id', lead_id) \
            .order('created_at', desc=False) \
            .execute()

        return result.data

    except Exception as e:
        logger.error(f"❌ Failed to get all agent states for lead {lead_id}: {e}")
        return []
