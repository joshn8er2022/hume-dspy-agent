"""Centralized Configuration for Hume DSPy Agent.

This module consolidates all configuration values that were previously
hardcoded throughout the codebase.
"""
import os
from typing import Dict


class Settings:
    """Application configuration settings."""
    
    # ============================================================================
    # SLACK CONFIGURATION
    # ============================================================================
    SLACK_BOT_TOKEN = (
        os.getenv("SLACK_BOT_TOKEN") or
        os.getenv("SLACK_MCP_XOXB_TOKEN") or
        os.getenv("SLACK_MCP_XOXP_TOKEN")
    )
    SLACK_CHANNEL_INBOUND = os.getenv("SLACK_CHANNEL", "C09FZT6T1A5")
    SLACK_CHANNEL_AI_TEST = os.getenv("SLACK_CHANNEL_AI_TEST", "ai-test")
    
    # ============================================================================
    # SUPABASE CONFIGURATION
    # ============================================================================
    SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://umawnwaoahhuttbeyuxs.supabase.co"
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_KEY") or 
        os.getenv("SUPABASE_KEY") or 
        os.getenv("SUPABASE_ANON_KEY")
    )
    
    # ============================================================================
    # LLM API KEYS
    # ============================================================================
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENAI_API_KEY = (
        os.getenv("OPENAI_API_KEY") or
        os.getenv("OPENAI_KEY") or
        os.getenv("OPENAI_API_TOKEN")
    )
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    # ============================================================================
    # QUALIFICATION THRESHOLDS (6-tier system)
    # ============================================================================
    SCORCHING_THRESHOLD = 90
    HOT_THRESHOLD = 75
    WARM_THRESHOLD = 60
    COOL_THRESHOLD = 45
    COLD_THRESHOLD = 30
    
    # ============================================================================
    # FOLLOW-UP AGENT CONFIGURATION
    # ============================================================================
    
    # Maximum follow-up attempts by tier
    FOLLOW_UP_MAX_ATTEMPTS: Dict[str, int] = {
        "SCORCHING": 7,
        "HOT": 5,
        "WARM": 3,
        "COOL": 2,
        "COLD": 2,
    }
    
    # Follow-up cadence (hours between attempts) by tier
    FOLLOW_UP_CADENCE_HOURS: Dict[str, int] = {
        "SCORCHING": 2,   # Every 2 hours
        "HOT": 4,         # Every 4 hours
        "WARM": 24,       # Daily
        "COOL": 48,       # Every 2 days
        "COLD": 48,       # Every 2 days
    }
    
    # ============================================================================
    # EMAIL & CRM CONFIGURATION
    # ============================================================================
    GMASS_API_KEY = os.getenv("GMASS_API_KEY")
    GMASS_API_URL = "https://api.gmass.co/api"
    FROM_EMAIL = os.getenv("FROM_EMAIL", "josh@humehealth.com")  # Authenticated Gmail address
    
    CLOSE_API_KEY = os.getenv("CLOSE_API_KEY")
    
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    
    # ============================================================================
    # MODEL CONFIGURATION
    # ============================================================================
    
    # Primary model (via OpenRouter)
    PRIMARY_MODEL = "anthropic/claude-sonnet-4.5"
    
    # Fallback models
    FALLBACK_MODEL_OPENAI = "openai/gpt-4o"
    FALLBACK_MODEL_ANTHROPIC = "claude-3-5-sonnet-20241022"
    
    # ============================================================================
    # RETRY CONFIGURATION
    # ============================================================================
    MAX_RETRIES = 3
    RETRY_MIN_WAIT_SECONDS = 4
    RETRY_MAX_WAIT_SECONDS = 10
    
    # ============================================================================
    # PROCESSING CONFIGURATION
    # ============================================================================
    WEBHOOK_TIMEOUT_SECONDS = 30
    BACKGROUND_PROCESSING_TIMEOUT_SECONDS = 300
    
    # ============================================================================
    # A2A CONFIGURATION
    # ============================================================================
    A2A_API_KEY = os.getenv("A2A_API_KEY")
    
    # ============================================================================
    # APPLICATION METADATA
    # ============================================================================
    APP_VERSION = "2.1.0-full-pipeline"
    APP_NAME = "Hume DSPy Agent"


# Singleton instance
settings = Settings()

# Export for easy imports
__all__ = ['settings', 'Settings']
