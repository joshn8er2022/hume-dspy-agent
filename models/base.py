"""Base Pydantic models for the Hume DSPy Agent system."""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class TimestampedModel(BaseModel):
    """Base model with automatic timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class BaseResponse(BaseModel):
    """Base response model for API endpoints."""

    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
