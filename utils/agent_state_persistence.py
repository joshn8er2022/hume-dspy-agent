"""
Agent state persistence system for Hume DSPy Agent.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4

from supabase import create_client
from config.settings import settings

logger = logging.getLogger(__name__)

class AgentStateManager:
    """Manages agent state persistence in Supabase."""
    
    def __init__(self):
        self.client = None
        self._init_supabase()
    
    def _init_supabase(self):
        """Initialize Supabase client."""
        try:
            if settings.SUPABASE_URL and settings.SUPABASE_KEY:
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                logger.info("✅ Agent state Supabase client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {str(e)}")
    
    async def save_agent_state(self, 
                             agent_name: str, 
                             lead_id: Optional[str] = None,
                             state_data: Dict[str, Any] = None) -> Optional[str]:
        """Save agent state to database."""
        
        if not self.client:
            logger.error("❌ Supabase client not initialized")
            return None
        
        try:
            state_record = {
                "id": str(uuid4()),
                "agent_name": agent_name,
                "lead_id": lead_id,
                "state_data": state_data or {},
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table('agent_state').upsert(state_record).execute()
            
            if result.data:
                state_id = result.data[0]['id']
                logger.info(f"✅ Agent state saved: {agent_name} -> {state_id}")
                return state_id
            else:
                logger.error(f"❌ Failed to save agent state: {agent_name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error saving agent state for {agent_name}: {str(e)}")
            return None

state_manager = AgentStateManager()

async def save_agent_state(agent_name: str, lead_id: Optional[str] = None, state_data: Dict[str, Any] = None):
    """Save agent state - convenience function."""
    return await state_manager.save_agent_state(agent_name, lead_id, state_data)
