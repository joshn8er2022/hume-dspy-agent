"""Pydantic models for Hume-specific memories.

These models define the structure of different memory types,
enabling type-safe memory operations and structured retrieval.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MemoryArea(str, Enum):
    """Memory areas (from Agent Zero)."""
    MAIN = "main"                    # General memories
    FRAGMENTS = "fragments"          # Conversation fragments
    SOLUTIONS = "solutions"          # Problem-solution pairs
    INSTRUMENTS = "instruments"      # Proven code snippets
    LEADS = "leads"                  # Lead-specific memories (Hume-specific)
    STRATEGIES = "strategies"        # Strategy memories (Hume-specific)


class LeadTier(str, Enum):
    """Lead qualification tiers."""
    HOT = "hot"
    WARM = "warm"
    COOL = "cool"
    COLD = "cold"
    UNQUALIFIED = "unqualified"


class LeadMemory(BaseModel):
    """Memory of a lead interaction.

    Stores complete lead data, qualification, strategy used, and outcome.
    Enables learning from past leads.
    """
    # Lead identification
    lead_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None

    # Firmographics
    practice_size: Optional[str] = None
    patient_volume: Optional[str] = None
    industry: Optional[str] = None

    # Qualification
    qualification_score: int
    tier: LeadTier
    fit_score: Optional[int] = None
    engagement_score: Optional[int] = None

    # Strategy
    strategy_used: Optional[str] = None
    channels_used: List[str] = Field(default_factory=list)

    # Outcome
    converted: Optional[bool] = None
    conversion_date: Optional[datetime] = None
    revenue: Optional[float] = None

    # Learnings
    what_worked: Optional[str] = None
    what_didnt_work: Optional[str] = None
    key_insights: Optional[str] = None

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    area: MemoryArea = MemoryArea.LEADS

    class Config:
        use_enum_values = True


class StrategyMemory(BaseModel):
    """Memory of a successful strategy.

    Stores proven approaches with success rates and use cases.
    """
    strategy_name: str
    description: str

    # Context
    use_cases: List[str] = Field(default_factory=list)
    target_segments: List[str] = Field(default_factory=list)

    # Performance
    success_rate: float = 0.0
    total_uses: int = 0
    successful_uses: int = 0

    # Details
    channels: List[str] = Field(default_factory=list)
    content_type: Optional[str] = None
    timing: Optional[str] = None

    # Examples
    example_leads: List[str] = Field(default_factory=list)

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    area: MemoryArea = MemoryArea.STRATEGIES

    class Config:
        use_enum_values = True


class InstrumentMemory(BaseModel):
    """Memory of a proven code instrument.

    Stores reusable code snippets with success metrics.
    """
    instrument_name: str
    description: str
    code: str

    # Usage
    use_cases: List[str] = Field(default_factory=list)
    success_rate: float = 0.0
    total_executions: int = 0
    successful_executions: int = 0

    # Metadata
    created_by: str  # Agent that created it
    language: str = "python"
    version: str = "1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    area: MemoryArea = MemoryArea.INSTRUMENTS

    class Config:
        use_enum_values = True


class ConversationMemory(BaseModel):
    """Memory of a conversation exchange.

    Stores user interactions for context and learning.
    """
    user_id: str
    user_message: str
    agent_response: str

    # Context
    agent_name: str
    task_type: Optional[str] = None

    # Outcome
    user_satisfied: Optional[bool] = None
    follow_up_needed: Optional[bool] = None

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    area: MemoryArea = MemoryArea.FRAGMENTS

    class Config:
        use_enum_values = True


class ResearchMemory(BaseModel):
    """Memory of research findings.

    Stores research results for reuse.
    """
    query: str
    findings: str

    # Context
    research_type: str  # "company", "person", "market", "competitor"
    sources: List[str] = Field(default_factory=list)

    # Quality
    confidence: float = 0.0
    verified: bool = False

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    area: MemoryArea = MemoryArea.MAIN

    class Config:
        use_enum_values = True
