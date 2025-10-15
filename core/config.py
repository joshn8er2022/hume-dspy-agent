"""Configuration management with Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional
import os


class Settings(BaseSettings):

    def __post_init__(self):
        """Validate required credentials are set."""
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.supabase_key:
            raise ValueError("SUPABASE_KEY environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
    """Application settings with environment variable support."""
    
    # LLM Configuration (Switchable)
    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # DSPy Configuration
    dspy_model: str = "gpt-4o"
    dspy_max_tokens: int = 4000
    dspy_temperature: float = 0.7
    
    # Supabase (OPTIONAL with defaults)
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    # Close CRM
    close_api_key: Optional[str] = None
    
    # SendGrid
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: str = "noreply@humeprograms.com"
    
    # Twilio
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # Slack
    slack_bot_token: Optional[str] = None
    slack_channel_leads: str = "#leads"
    
    # Vapi
    vapi_api_key: Optional[str] = None
    
    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Environment
    environment: Literal["development", "production"] = "development"
    debug: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    def get_llm_api_key(self) -> str:
        """Get the appropriate LLM API key based on provider."""
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            return self.openai_api_key
        elif self.llm_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            return self.anthropic_api_key
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


# Global settings instance
settings = Settings()
