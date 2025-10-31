# MASTER IMPLEMENTATION PLAN
## Hybrid DSPy + Agent-Zero Architecture for hume-dspy-agent

**Version:** 1.0
**Date:** 2025-10-30
**Status:** Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Critical Findings](#critical-findings)
4. [Implementation Phases](#implementation-phases)
5. [Phase 0: Bug Fixes (Week 1)](#phase-0-bug-fixes)
6. [Phase 1: Error Handling (Weeks 1-2)](#phase-1-error-handling)
7. [Phase 2: Dynamic Tool Loading (Weeks 2-3)](#phase-2-dynamic-tool-loading)
8. [Phase 3: Enhanced Multi-Agent (Weeks 3-5)](#phase-3-enhanced-multi-agent)
9. [Phase 4: Production Hardening (Weeks 5-6)](#phase-4-production-hardening)
10. [Code Templates & Examples](#code-templates)
11. [Testing Strategy](#testing-strategy)
12. [Success Metrics](#success-metrics)
13. [Rollback Plans](#rollback-plans)

---

## Executive Summary

### What We're Building

A **production-grade hybrid agent system** that combines:
- ✅ **DSPy's reasoning quality** (ChainOfThought, ReAct modules)
- ✅ **Pydantic's type safety** (runtime validation throughout)
- ✅ **agent-zero's extensibility** (dynamic tool loading)
- ✅ **agent-zero's reliability** (3-tier error handling with self-repair)
- ✅ **agent-zero's multi-agent patterns** (superior-subordinate coordination)

### Why This Matters

**Current State:**
- ❌ 2 broken functions returning mock data
- ❌ Hardcoded tool lists (not extensible)
- ❌ Basic error handling (crashes on failures)
- ❌ LangGraph limiting multi-agent flexibility
- ✅ Excellent DSPy reasoning quality
- ✅ Strong Pydantic type safety

**Future State:**
- ✅ All functions querying real data
- ✅ Plugin architecture (drop file, auto-discovered)
- ✅ Self-healing agents (LLM repairs errors)
- ✅ Dynamic multi-agent spawning
- ✅ Preserved DSPy + Pydantic excellence

### Key Principles

1. **Preserve DSPy** - All reasoning stays programmatic, not prompt-based
2. **Preserve Pydantic** - Type safety is non-negotiable
3. **Minimize Breaking Changes** - Old code works during migration
4. **Incremental Rollout** - Ship improvements weekly
5. **Test Everything** - No untested production code

---

## Architecture Overview

### Current Architecture (hume-dspy-agent)

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Webhook                    │
│              (Typeform, Slack, etc.)                │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              InboundAgent (DSPy)                    │
│  ┌──────────────────────────────────────────────┐  │
│  │ analyze_lead() - ChainOfThought              │  │
│  │ generate_email() - Predict                   │  │
│  │ HARDCODED: 7 methods for tools              │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│         FollowUpAgent (LangGraph)                   │
│  ┌──────────────────────────────────────────────┐  │
│  │ State Machine: Assess → Email → Wait → ...  │  │
│  │ PostgreSQL Checkpointer                      │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Problems:**
- Tools are methods in agent classes (not reusable)
- Error handling is basic try/except (no recovery)
- Multi-agent limited to agent delegation pattern

### Target Architecture (Hybrid)

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Webhook                    │
│              (Error Recovery Enabled)                │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│          Enhanced InboundAgent (DSPy)               │
│  ┌──────────────────────────────────────────────┐  │
│  │ analyze_lead() - ChainOfThought              │  │
│  │ generate_email() - Predict                   │  │
│  │                                              │  │
│  │ DYNAMIC TOOLS:                               │  │
│  │   ToolRegistry.get_all()                     │  │
│  │   - Clearbit lookup                          │  │
│  │   - Supabase query                           │  │
│  │   - Wolfram Alpha                            │  │
│  │   - RAG search                               │  │
│  │   + Any new tools (auto-discovered)          │  │
│  │                                              │  │
│  │ ERROR RECOVERY:                              │  │
│  │   @with_retry_logic decorator                │  │
│  │   - InterventionException (user pause)       │  │
│  │   - RepairableException (LLM fixes)          │  │
│  │   - HandledException (graceful fail)         │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│       Enhanced Multi-Agent System                   │
│  ┌──────────────────────────────────────────────┐  │
│  │ Superior Agent (e.g., StrategyAgent)         │  │
│  │   ├─> Subordinate: CompetitorAnalyst         │  │
│  │   ├─> Subordinate: MarketResearcher          │  │
│  │   └─> Subordinate: AccountResearcher         │  │
│  │                                              │  │
│  │ PARALLEL EXECUTION:                          │  │
│  │   await asyncio.gather(                      │  │
│  │     sub1.execute(),                          │  │
│  │     sub2.execute(),                          │  │
│  │     sub3.execute()                           │  │
│  │   )                                          │  │
│  │                                              │  │
│  │ HIERARCHICAL MEMORY:                         │  │
│  │   - Per-agent context                        │  │
│  │   - Cross-agent learning                     │  │
│  │   - Shared knowledge base                    │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Benefits:**
- Tools are modular plugins (reusable, testable)
- Errors trigger LLM self-repair (80% crash reduction)
- Multi-agent supports parallel + hierarchical patterns

---

## Critical Findings

### Issue #1: Two Broken Functions (CRITICAL)

**Location:** `~/hume-dspy-agent/agents/strategy_agent.py`

**Function 1: `analyze_pipeline()`** (Line 1283)
```python
# CURRENT (BROKEN)
async def analyze_pipeline(self, state: StrategyState) -> StrategyState:
    """Analyzes current pipeline state and metrics."""

    # PROBLEM: Returns hardcoded mock data
    state["pipeline_analysis"] = {
        "total_leads": 42,
        "tier_distribution": {
            "SCORCHING": 3,
            "HOT": 8,
            "WARM": 12,
            "COOL": 11,
            "COLD": 8
        },
        "conversion_rates": {
            "qualified_to_meeting": "18%",
            "meeting_to_closed": "31%"
        },
        "bottlenecks": [
            "Low response rate on WARM tier (22%)",
            "Long time-to-first-response (avg 4.2 hours)"
        ]
    }
```

**Function 2: `recommend_outbound_targets()`** (Line 1341)
```python
# CURRENT (BROKEN)
async def recommend_outbound_targets(self, state: StrategyState) -> StrategyState:
    """Recommends similar companies to target for outbound."""

    # PROBLEM: Returns hardcoded fake companies
    state["recommended_targets"] = [
        {
            "company_name": "West Coast Weight Loss Center",
            "similarity_score": 0.89,
            "reasoning": "Similar size practice, same region..."
        },
        {
            "company_name": "Precision Health Clinic",
            "similarity_score": 0.84,
            "reasoning": "High patient volume, uses EHR..."
        }
    ]
```

**Impact:**
- Strategy Agent makes decisions on fake data
- No actionable insights for users
- Blocking production deployment

**Fix Priority:** CRITICAL - Must fix in Week 1

### Issue #2: Tool Architecture

**Current State:**
```python
# tools/strategy_tools.py - HARDCODED LIST
STRATEGY_TOOLS = [
    search_knowledge_base,
    wolfram_strategic_query,
    wolfram_market_analysis,
    query_spreadsheet_data,
    analyze_competitor,
    get_market_trends
]
```

**Problems:**
- Adding tool = modify agent code (not modular)
- Tools can't be tested independently
- No versioning or metadata
- MCP tools mixed with internal tools

**Solution:** Pydantic-based dynamic tool loading (Phase 2)

### Issue #3: Error Handling

**Current State:**
```python
# agents/inbound_agent.py
try:
    result = await self.analyze_business_fit(lead)
except Exception as e:
    logger.error(f"Error analyzing lead: {e}")
    # PROBLEM: Just logs and continues with partial data
    result = {"score": 0, "reasoning": "Error occurred"}
```

**Problems:**
- Errors just logged, agent continues with bad data
- No retry logic for transient failures (API timeouts)
- No way for LLM to self-correct mistakes
- Crashes on unexpected errors

**Solution:** 3-tier error handling (Phase 1)

---

## Implementation Phases

### Overview

| Phase | Duration | Focus | Risk |
|-------|----------|-------|------|
| **Phase 0** | Week 1 | Bug Fixes | Low |
| **Phase 1** | Weeks 1-2 | Error Handling | Medium |
| **Phase 2** | Weeks 2-3 | Dynamic Tools | Medium |
| **Phase 3** | Weeks 3-5 | Multi-Agent | High |
| **Phase 4** | Weeks 5-6 | Production | Low |

**Total Timeline:** 6 weeks
**Team Size:** 1-2 developers
**Success Criteria:** All tests passing, no regressions

---

## Phase 0: Bug Fixes (Week 1)

### Priority: CRITICAL

**Goal:** Fix the 2 broken functions to return real data

### Task 0.1: Fix `analyze_pipeline()`

**File:** `agents/strategy_agent.py:1283`

**Implementation:**

```python
async def analyze_pipeline(self, state: StrategyState) -> StrategyState:
    """Analyzes current pipeline state and metrics from Supabase."""

    try:
        # Query real lead data from Supabase
        leads_response = self.supabase.table('leads') \
            .select('tier, status, created_at, email_sent_count, response_received') \
            .execute()

        leads = leads_response.data

        # Calculate tier distribution
        tier_counts = {}
        for tier in ["SCORCHING", "HOT", "WARM", "COOL", "COLD", "UNQUALIFIED"]:
            tier_counts[tier] = len([l for l in leads if l.get('tier') == tier])

        # Calculate conversion rates
        qualified = len([l for l in leads if l.get('tier') in ['SCORCHING', 'HOT', 'WARM']])
        meetings_booked = len([l for l in leads if l.get('status') == 'meeting_booked'])
        closed_won = len([l for l in leads if l.get('status') == 'closed_won'])

        qualified_to_meeting = (meetings_booked / qualified * 100) if qualified > 0 else 0
        meeting_to_closed = (closed_won / meetings_booked * 100) if meetings_booked > 0 else 0

        # Identify bottlenecks with DSPy reasoning
        bottleneck_analysis = await self.analyze_bottlenecks(
            leads=leads,
            tier_counts=tier_counts,
            conversion_rates={
                "qualified_to_meeting": qualified_to_meeting,
                "meeting_to_closed": meeting_to_closed
            }
        )

        state["pipeline_analysis"] = {
            "total_leads": len(leads),
            "tier_distribution": tier_counts,
            "conversion_rates": {
                "qualified_to_meeting": f"{qualified_to_meeting:.1f}%",
                "meeting_to_closed": f"{meeting_to_closed:.1f}%"
            },
            "bottlenecks": bottleneck_analysis.bottlenecks,
            "recommendations": bottleneck_analysis.recommendations
        }

        return state

    except Exception as e:
        logger.error(f"Error analyzing pipeline: {e}")
        # Graceful fallback
        state["pipeline_analysis"] = {
            "error": str(e),
            "total_leads": 0,
            "tier_distribution": {},
            "conversion_rates": {},
            "bottlenecks": ["Unable to analyze - database error"]
        }
        return state
```

**New DSPy Signature:**

```python
class AnalyzeBottlenecks(dspy.Signature):
    """Analyze pipeline data to identify bottlenecks and recommend improvements."""

    tier_distribution: dict = dspy.InputField(desc="Count of leads per tier")
    conversion_rates: dict = dspy.InputField(desc="Conversion percentages")
    recent_activity: str = dspy.InputField(desc="Summary of recent lead activity")

    bottlenecks: list[str] = dspy.OutputField(desc="List of identified bottlenecks")
    recommendations: list[str] = dspy.OutputField(desc="Actionable recommendations")
```

**Testing:**

```python
# tests/test_strategy_agent.py
@pytest.mark.asyncio
async def test_analyze_pipeline_real_data():
    """Test pipeline analysis with real Supabase data."""
    agent = StrategyAgent(config=test_config)
    state = {"message_history": []}

    result = await agent.analyze_pipeline(state)

    # Verify real data, not mocks
    assert "pipeline_analysis" in result
    assert isinstance(result["pipeline_analysis"]["total_leads"], int)
    assert result["pipeline_analysis"]["total_leads"] >= 0  # Real count
    assert "SCORCHING" in result["pipeline_analysis"]["tier_distribution"]

    # Should have bottlenecks from DSPy analysis
    assert len(result["pipeline_analysis"]["bottlenecks"]) > 0
```

---

### Task 0.2: Fix `recommend_outbound_targets()`

**File:** `agents/strategy_agent.py:1341`

**Implementation:**

```python
async def recommend_outbound_targets(self, state: StrategyState) -> StrategyState:
    """Recommends similar companies based on successful lead patterns."""

    try:
        # 1. Get high-quality leads (SCORCHING/HOT that converted)
        success_leads = self.supabase.table('leads') \
            .select('company, industry, business_size, patient_volume, location') \
            .in_('tier', ['SCORCHING', 'HOT']) \
            .eq('status', 'meeting_booked') \
            .execute()

        # 2. Extract common patterns
        patterns = self._extract_success_patterns(success_leads.data)

        # 3. Use Clearbit or Apollo API to find similar companies
        similar_companies = await self._find_similar_companies(patterns)

        # 4. Score with DSPy reasoning
        scored_targets = []
        for company in similar_companies:
            scoring = await self.score_target_similarity(
                company_data=company,
                success_patterns=patterns
            )

            scored_targets.append({
                "company_name": company["name"],
                "website": company.get("domain"),
                "similarity_score": scoring.similarity_score,
                "reasoning": scoring.reasoning,
                "contact_info": company.get("contacts", [])
            })

        # Sort by score
        scored_targets.sort(key=lambda x: x["similarity_score"], reverse=True)

        state["recommended_targets"] = scored_targets[:10]  # Top 10
        return state

    except Exception as e:
        logger.error(f"Error recommending targets: {e}")
        state["recommended_targets"] = []
        state["error"] = str(e)
        return state

def _extract_success_patterns(self, leads: list[dict]) -> dict:
    """Extract common attributes from successful leads."""
    patterns = {
        "industries": {},
        "business_sizes": {},
        "locations": {},
        "avg_patient_volume": 0
    }

    for lead in leads:
        # Count industry frequency
        industry = lead.get("industry")
        if industry:
            patterns["industries"][industry] = patterns["industries"].get(industry, 0) + 1

        # Count business size
        size = lead.get("business_size")
        if size:
            patterns["business_sizes"][size] = patterns["business_sizes"].get(size, 0) + 1

        # Count locations
        location = lead.get("location")
        if location:
            patterns["locations"][location] = patterns["locations"].get(location, 0) + 1

    return patterns

async def _find_similar_companies(self, patterns: dict) -> list[dict]:
    """Find companies matching success patterns using Clearbit/Apollo."""

    # Use Clearbit Discovery API or similar
    # This is a placeholder - implement with your enrichment service

    top_industry = max(patterns["industries"].items(), key=lambda x: x[1])[0]
    top_size = max(patterns["business_sizes"].items(), key=lambda x: x[1])[0]

    # Example Clearbit API call
    params = {
        "industry": top_industry,
        "size": top_size,
        "limit": 20
    }

    # TODO: Implement actual API call
    # For now, return empty - this ensures no fake data
    return []
```

**New DSPy Signature:**

```python
class ScoreTargetSimilarity(dspy.Signature):
    """Score how similar a target company is to successful leads."""

    company_data: dict = dspy.InputField(desc="Target company information")
    success_patterns: dict = dspy.InputField(desc="Patterns from successful leads")

    similarity_score: float = dspy.OutputField(desc="Similarity score 0.0-1.0")
    reasoning: str = dspy.OutputField(desc="Explanation of score")
    match_factors: list[str] = dspy.OutputField(desc="What factors matched")
```

**Testing:**

```python
@pytest.mark.asyncio
async def test_recommend_outbound_targets_real():
    """Test target recommendations with real pattern extraction."""
    agent = StrategyAgent(config=test_config)
    state = {"message_history": []}

    result = await agent.recommend_outbound_targets(state)

    # Should return list (may be empty if no API configured)
    assert "recommended_targets" in result
    assert isinstance(result["recommended_targets"], list)

    # If targets exist, verify structure
    if result["recommended_targets"]:
        target = result["recommended_targets"][0]
        assert "company_name" in target
        assert "similarity_score" in target
        assert "reasoning" in target
        assert 0 <= target["similarity_score"] <= 1
```

---

### Acceptance Criteria (Phase 0)

- ✅ `analyze_pipeline()` queries real Supabase data
- ✅ `recommend_outbound_targets()` uses real lead patterns (or returns empty)
- ✅ No hardcoded mock data anywhere
- ✅ All existing tests still pass
- ✅ New tests for both functions pass
- ✅ Strategy Agent returns actionable insights

**Time Estimate:** 5-7 hours
**Risk:** Low (isolated changes)
**Rollback:** Revert 2 function implementations

---

## Phase 1: Error Handling (Weeks 1-2)

### Priority: HIGH

**Goal:** Implement agent-zero's 3-tier error handling with DSPy integration

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Exception Hierarchy                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  AgentException (Base)                              │
│    ├─> InterventionException (User paused)         │
│    ├─> RepairableException (LLM can fix)           │
│    └─> HandledException (Terminal)                 │
│                                                     │
│  Specialized:                                       │
│    ├─> APICallException (extends Repairable)       │
│    ├─> ValidationException (extends Repairable)    │
│    └─> RateLimitException (extends Repairable)     │
└─────────────────────────────────────────────────────┘
```

### Task 1.1: Create Exception Hierarchy

**New File:** `core/exceptions.py`

```python
from typing import Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

class ErrorSeverity(str, Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorContext(BaseModel):
    """Pydantic model capturing error context for recovery."""

    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Human-readable error message")
    severity: ErrorSeverity = Field(default=ErrorSeverity.MEDIUM)

    # Context for recovery
    agent_name: str = Field(..., description="Which agent encountered error")
    operation: str = Field(..., description="What operation failed")
    input_data: dict = Field(default_factory=dict, description="Input that caused error")
    stack_trace: Optional[str] = Field(default=None)

    # Recovery hints
    recovery_hints: list[str] = Field(default_factory=list, description="Suggestions for LLM")
    max_retry_attempts: int = Field(default=3)
    current_attempt: int = Field(default=1)

    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    correlation_id: Optional[str] = Field(default=None)

class AgentException(Exception):
    """Base exception for all agent errors with Pydantic context."""

    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        self.message = message
        self.context = context or ErrorContext(
            error_type=self.__class__.__name__,
            error_message=message,
            agent_name="unknown",
            operation="unknown"
        )
        super().__init__(message)

class InterventionException(AgentException):
    """User intervention - pause and wait for input."""
    pass

class RepairableException(AgentException):
    """Error that LLM can potentially repair through reasoning."""
    pass

class HandledException(AgentException):
    """Terminal error - stop gracefully."""
    pass

# Specialized exceptions
class APICallException(RepairableException):
    """API call failed - LLM can retry with different parameters."""
    pass

class ValidationException(RepairableException):
    """Data validation failed - LLM can correct input."""
    pass

class RateLimitException(RepairableException):
    """Rate limit hit - LLM can wait and retry."""
    pass

class ToolExecutionException(RepairableException):
    """Tool execution failed - LLM can try different tool or parameters."""
    pass
```

---

### Task 1.2: Create DSPy Error Recovery Module

**New File:** `dspy_modules/error_recovery.py`

```python
import dspy
from typing import Optional
from pydantic import BaseModel, Field
from core.exceptions import ErrorContext, RepairableException

class ErrorAnalysis(dspy.Signature):
    """Analyze an error and determine recovery strategy."""

    error_context: ErrorContext = dspy.InputField(
        desc="Complete context about the error"
    )
    previous_attempts: list[str] = dspy.InputField(
        default_factory=list,
        desc="Previous recovery attempts that failed"
    )

    can_recover: bool = dspy.OutputField(
        desc="Whether error is recoverable"
    )
    recovery_strategy: str = dspy.OutputField(
        desc="How to recover from this error"
    )
    recovery_confidence: float = dspy.OutputField(
        desc="Confidence in recovery (0.0-1.0)"
    )
    alternative_approaches: list[str] = dspy.OutputField(
        desc="Alternative ways to accomplish the goal"
    )

class RecoveryAction(BaseModel):
    """Pydantic model for recovery actions."""

    action_type: str = Field(..., description="Type of recovery action")
    parameters: dict = Field(default_factory=dict)
    reasoning: str = Field(..., description="Why this action was chosen")
    confidence: float = Field(..., ge=0.0, le=1.0)

class ErrorRecoveryResult(BaseModel):
    """Result of error recovery attempt."""

    success: bool
    action_taken: Optional[RecoveryAction] = None
    error_resolved: bool = False
    new_error: Optional[str] = None
    attempts_made: int = 1

class DSPyErrorRecovery:
    """Orchestrates error recovery using DSPy reasoning."""

    def __init__(self, config):
        self.config = config
        self.error_analyzer = dspy.ChainOfThought(ErrorAnalysis)

    async def attempt_recovery(
        self,
        error: RepairableException,
        context: dict,
        previous_attempts: list[str] = None
    ) -> ErrorRecoveryResult:
        """Use DSPy to analyze error and attempt recovery."""

        previous_attempts = previous_attempts or []

        # Use DSPy to analyze error
        analysis = self.error_analyzer(
            error_context=error.context,
            previous_attempts=previous_attempts
        )

        if not analysis.can_recover or analysis.recovery_confidence < 0.3:
            return ErrorRecoveryResult(
                success=False,
                error_resolved=False,
                attempts_made=len(previous_attempts) + 1
            )

        # Execute recovery strategy
        try:
            action = RecoveryAction(
                action_type="retry_with_modification",
                parameters=self._parse_recovery_strategy(analysis.recovery_strategy),
                reasoning=analysis.recovery_strategy,
                confidence=analysis.recovery_confidence
            )

            # Log recovery attempt
            logger.info(f"Attempting recovery: {action.reasoning}")

            return ErrorRecoveryResult(
                success=True,
                action_taken=action,
                error_resolved=True,
                attempts_made=len(previous_attempts) + 1
            )

        except Exception as e:
            return ErrorRecoveryResult(
                success=False,
                error_resolved=False,
                new_error=str(e),
                attempts_made=len(previous_attempts) + 1
            )

    def _parse_recovery_strategy(self, strategy: str) -> dict:
        """Parse LLM's recovery strategy into actionable parameters."""
        # Simple parsing - can be enhanced
        return {"strategy_text": strategy}
```

---

### Task 1.3: Create Retry Decorator

**New File:** `core/decorators.py`

```python
import asyncio
import functools
from typing import Callable, Optional
from core.exceptions import (
    RepairableException,
    InterventionException,
    HandledException,
    ErrorContext,
    ErrorSeverity
)
from dspy_modules.error_recovery import DSPyErrorRecovery
import logging

logger = logging.getLogger(__name__)

def with_retry_logic(
    max_attempts: int = 3,
    enable_llm_recovery: bool = True,
    fallback_value: Optional[any] = None
):
    """Decorator that adds 3-tier error handling to agent methods.

    Args:
        max_attempts: Maximum retry attempts for RepairableException
        enable_llm_recovery: Use DSPy to analyze and fix errors
        fallback_value: Value to return if all recovery fails

    Example:
        @with_retry_logic(max_attempts=3, enable_llm_recovery=True)
        async def analyze_lead(self, lead: Lead) -> QualificationResult:
            # ... implementation that might fail
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            attempts = []
            error_recovery = DSPyErrorRecovery(self.config) if enable_llm_recovery else None

            for attempt in range(max_attempts):
                try:
                    # Execute the original function
                    result = await func(self, *args, **kwargs)

                    # Success!
                    if attempts:
                        logger.info(f"✅ Recovered after {len(attempts)} attempts")
                    return result

                except InterventionException as e:
                    # User intervention - re-raise immediately
                    logger.warning(f"User intervention: {e.message}")
                    raise

                except RepairableException as e:
                    # LLM can potentially fix this
                    logger.warning(f"Repairable error (attempt {attempt + 1}/{max_attempts}): {e.message}")

                    if attempt < max_attempts - 1 and error_recovery:
                        # Use DSPy to analyze and recover
                        recovery_result = await error_recovery.attempt_recovery(
                            error=e,
                            context={"args": args, "kwargs": kwargs},
                            previous_attempts=attempts
                        )

                        attempts.append({
                            "attempt": attempt + 1,
                            "error": e.message,
                            "recovery_action": recovery_result.action_taken
                        })

                        if recovery_result.error_resolved:
                            logger.info(f"Recovery succeeded: {recovery_result.action_taken.reasoning}")
                            # Retry with modifications
                            await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                            continue
                        else:
                            logger.warning(f"Recovery failed: trying again...")
                            await asyncio.sleep(1.0 * (attempt + 1))
                            continue
                    else:
                        # Max attempts reached or no LLM recovery
                        if fallback_value is not None:
                            logger.warning(f"Returning fallback value after {attempt + 1} attempts")
                            return fallback_value
                        raise HandledException(
                            f"Failed after {max_attempts} attempts",
                            context=e.context
                        )

                except HandledException as e:
                    # Terminal error - stop immediately
                    logger.error(f"Terminal error: {e.message}")
                    if fallback_value is not None:
                        return fallback_value
                    raise

                except Exception as e:
                    # Unexpected error - wrap and handle
                    logger.error(f"Unexpected error: {str(e)}", exc_info=True)

                    # Create error context
                    error_context = ErrorContext(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        severity=ErrorSeverity.HIGH,
                        agent_name=self.__class__.__name__,
                        operation=func.__name__,
                        input_data={"args": str(args)[:200], "kwargs": str(kwargs)[:200]},
                        current_attempt=attempt + 1,
                        max_retry_attempts=max_attempts
                    )

                    if fallback_value is not None:
                        return fallback_value

                    raise HandledException(
                        f"Unexpected error in {func.__name__}: {str(e)}",
                        context=error_context
                    )

            # Should never reach here
            if fallback_value is not None:
                return fallback_value
            raise HandledException(f"Max attempts ({max_attempts}) exceeded")

        return wrapper
    return decorator
```

---

### Task 1.4: Integrate with InboundAgent

**File:** `agents/inbound_agent.py` (modifications)

```python
from core.decorators import with_retry_logic
from core.exceptions import (
    RepairableException,
    APICallException,
    ValidationException,
    ErrorContext,
    ErrorSeverity
)

class InboundAgent:
    # ... existing code ...

    @with_retry_logic(max_attempts=3, enable_llm_recovery=True)
    async def qualify_lead(self, lead: Lead) -> QualificationResult:
        """Qualify a lead with error recovery."""

        try:
            # Analyze business fit
            business_fit = await self._analyze_business_fit(lead)

            # Score response quality
            response_score = await self._score_response_quality(lead)

            # Calculate total score
            total_score = business_fit["score"] + response_score["score"]

            # Classify tier
            tier = self._classify_tier(total_score)

            # Generate recommendations
            next_actions = await self._generate_next_actions(lead, tier)

            return QualificationResult(
                is_qualified=(tier in ["SCORCHING", "HOT", "WARM"]),
                score=total_score,
                tier=tier,
                reasoning=f"{business_fit['reasoning']} {response_score['reasoning']}",
                next_actions=next_actions
            )

        except ValidationError as e:
            # Pydantic validation failed - repairable
            raise ValidationException(
                f"Lead data validation failed: {str(e)}",
                context=ErrorContext(
                    error_type="ValidationError",
                    error_message=str(e),
                    severity=ErrorSeverity.MEDIUM,
                    agent_name="InboundAgent",
                    operation="qualify_lead",
                    input_data=lead.dict(),
                    recovery_hints=[
                        "Check if required fields are missing",
                        "Verify email format is valid",
                        "Ensure score values are within range"
                    ]
                )
            )

        except Exception as e:
            # Unexpected error - let decorator handle
            raise

    @with_retry_logic(max_attempts=3, enable_llm_recovery=True)
    async def _analyze_business_fit(self, lead: Lead) -> dict:
        """Analyze business fit with API error handling."""

        try:
            # Call DSPy module
            result = self.business_analyzer(
                company_context=get_company_context(),
                business_size=lead.get_field('business_size'),
                patient_volume=lead.get_field('patient_volume'),
                company=lead.get_field('company')
            )

            return {
                "score": result.fit_score,
                "reasoning": result.reasoning
            }

        except requests.exceptions.Timeout:
            # API timeout - repairable
            raise APICallException(
                "OpenRouter API timeout",
                context=ErrorContext(
                    error_type="APITimeout",
                    error_message="OpenRouter took too long to respond",
                    severity=ErrorSeverity.MEDIUM,
                    agent_name="InboundAgent",
                    operation="_analyze_business_fit",
                    recovery_hints=[
                        "Retry with shorter timeout",
                        "Try fallback model (Haiku instead of Sonnet)",
                        "Use cached result if available"
                    ]
                )
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limit - repairable
                raise RateLimitException(
                    "OpenRouter rate limit exceeded",
                    context=ErrorContext(
                        error_type="RateLimitError",
                        error_message="Too many API requests",
                        severity=ErrorSeverity.HIGH,
                        agent_name="InboundAgent",
                        operation="_analyze_business_fit",
                        recovery_hints=[
                            "Wait 60 seconds before retrying",
                            "Switch to backup API key",
                            "Use cheaper model to conserve quota"
                        ]
                    )
                )
            else:
                # Other HTTP error
                raise APICallException(
                    f"API error: {e.response.status_code}",
                    context=ErrorContext(
                        error_type="APIError",
                        error_message=str(e),
                        severity=ErrorSeverity.HIGH,
                        agent_name="InboundAgent",
                        operation="_analyze_business_fit"
                    )
                )
```

---

### Testing Strategy (Phase 1)

```python
# tests/test_error_handling.py

import pytest
from core.exceptions import *
from core.decorators import with_retry_logic
from dspy_modules.error_recovery import DSPyErrorRecovery

@pytest.mark.asyncio
async def test_repairable_exception_recovery():
    """Test that RepairableException triggers recovery."""

    attempts = []

    class TestAgent:
        def __init__(self):
            self.config = test_config

        @with_retry_logic(max_attempts=3, enable_llm_recovery=True)
        async def failing_method(self):
            attempts.append(1)
            if len(attempts) < 2:
                raise RepairableException(
                    "Temporary failure",
                    context=ErrorContext(
                        error_type="TempError",
                        error_message="This should be fixed",
                        agent_name="TestAgent",
                        operation="failing_method"
                    )
                )
            return "success"

    agent = TestAgent()
    result = await agent.failing_method()

    assert result == "success"
    assert len(attempts) == 2  # Failed once, succeeded on retry

@pytest.mark.asyncio
async def test_intervention_exception_not_retried():
    """Test that InterventionException immediately re-raises."""

    class TestAgent:
        def __init__(self):
            self.config = test_config

        @with_retry_logic(max_attempts=3)
        async def intervention_method(self):
            raise InterventionException("User paused")

    agent = TestAgent()

    with pytest.raises(InterventionException):
        await agent.intervention_method()

@pytest.mark.asyncio
async def test_fallback_value_on_failure():
    """Test fallback value returned when all retries fail."""

    class TestAgent:
        def __init__(self):
            self.config = test_config

        @with_retry_logic(max_attempts=2, fallback_value={"fallback": True})
        async def always_fails(self):
            raise RepairableException("Always fails")

    agent = TestAgent()
    result = await agent.always_fails()

    assert result == {"fallback": True}

@pytest.mark.asyncio
async def test_error_context_captured():
    """Test that ErrorContext captures all necessary info."""

    context = ErrorContext(
        error_type="APIError",
        error_message="API call failed",
        severity=ErrorSeverity.HIGH,
        agent_name="TestAgent",
        operation="test_operation",
        input_data={"key": "value"},
        recovery_hints=["Try again", "Use fallback"]
    )

    assert context.error_type == "APIError"
    assert context.severity == ErrorSeverity.HIGH
    assert len(context.recovery_hints) == 2
    assert context.timestamp is not None
```

---

### Acceptance Criteria (Phase 1)

- ✅ Exception hierarchy created with Pydantic models
- ✅ DSPy error recovery module functional
- ✅ `@with_retry_logic` decorator working
- ✅ InboundAgent uses error handling
- ✅ All error handling tests pass
- ✅ Existing functionality preserved
- ✅ Error logs are structured JSON

**Time Estimate:** 1-2 weeks
**Risk:** Medium (touches core agent logic)
**Rollback:** Remove decorator, use old try/except

---

## Phase 2: Dynamic Tool Loading (Weeks 2-3)

### Priority: HIGH

**Goal:** Replace hardcoded tool lists with plugin architecture

### Architecture

```
tools/
├── __init__.py
├── base.py                    # BaseTool, ToolMetadata
├── registry.py                # ToolRegistry
├── adapters.py                # DSPyToolAdapter
│
├── internal/                  # Internal tools
│   ├── clearbit_lookup.py
│   ├── supabase_query.py
│   ├── wolfram_query.py
│   └── rag_search.py
│
└── mcp/                       # MCP tools (auto-discovered)
    └── (dynamically loaded)
```

### Task 2.1: Create Pydantic Tool Base

**New File:** `tools/base.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Any, Callable
from enum import Enum
import inspect

class ToolParameterType(str, Enum):
    """Supported parameter types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DICT = "dict"
    LIST = "list"

class ToolParameter(BaseModel):
    """Pydantic model for tool parameters."""

    name: str = Field(..., description="Parameter name")
    type: ToolParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="What this parameter does")
    required: bool = Field(default=True, description="Is parameter required")
    default: Optional[Any] = Field(default=None, description="Default value if optional")

    @validator('default')
    def validate_default(cls, v, values):
        """Ensure default is only set for optional parameters."""
        if v is not None and values.get('required', True):
            raise ValueError("Default value only allowed for optional parameters")
        return v

class ToolMetadata(BaseModel):
    """Metadata describing a tool."""

    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="What the tool does")
    parameters: list[ToolParameter] = Field(default_factory=list)
    return_type: str = Field(default="dict", description="What the tool returns")
    category: str = Field(default="general", description="Tool category")
    version: str = Field(default="1.0.0", description="Tool version")
    author: Optional[str] = Field(default=None)
    examples: list[str] = Field(default_factory=list)

class ToolResult(BaseModel):
    """Result from tool execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    result: Any = Field(default=None, description="Tool output")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: dict = Field(default_factory=dict, description="Additional info")

class BaseTool:
    """Base class for all tools (agent-zero pattern with Pydantic)."""

    # Class attributes (set by subclasses or decorator)
    metadata: ToolMetadata

    def __init__(self):
        """Initialize tool."""
        if not hasattr(self, 'metadata'):
            raise NotImplementedError("Tool must define metadata")

    async def before_execution(self, **kwargs) -> dict:
        """Hook before execution (for logging, validation)."""
        return kwargs

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool. Must be implemented by subclasses."""
        raise NotImplementedError("Tool must implement execute()")

    async def after_execution(self, result: ToolResult) -> ToolResult:
        """Hook after execution (for logging, cleanup)."""
        return result

    async def __call__(self, **kwargs) -> ToolResult:
        """Execute tool with lifecycle hooks."""

        try:
            # Before hook
            kwargs = await self.before_execution(**kwargs)

            # Main execution
            result = await self.execute(**kwargs)

            # After hook
            result = await self.after_execution(result)

            return result

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"exception_type": type(e).__name__}
            )

    def to_dspy_callable(self) -> Callable:
        """Convert to DSPy-compatible callable."""
        from tools.adapters import DSPyToolAdapter
        return DSPyToolAdapter.adapt(self)
```

---

### Task 2.2: Create Tool Registry

**New File:** `tools/registry.py`

```python
import importlib
import inspect
import os
from pathlib import Path
from typing import Optional, Type
from tools.base import BaseTool, ToolMetadata
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Singleton registry for all tools (dynamic discovery)."""

    _instance = None
    _tools: dict[str, BaseTool] = {}
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, tool: BaseTool):
        """Register a tool instance."""
        instance = cls()
        instance._tools[tool.metadata.name] = tool
        logger.info(f"Registered tool: {tool.metadata.name}")

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        """Get tool by name."""
        instance = cls()
        return instance._tools.get(name)

    @classmethod
    def get_all(cls) -> dict[str, BaseTool]:
        """Get all registered tools."""
        instance = cls()
        if not instance._loaded:
            instance._discover_tools()
        return instance._tools

    @classmethod
    def get_by_category(cls, category: str) -> dict[str, BaseTool]:
        """Get all tools in a category."""
        instance = cls()
        return {
            name: tool
            for name, tool in instance.get_all().items()
            if tool.metadata.category == category
        }

    def _discover_tools(self):
        """Auto-discover tools from tools/internal directory."""

        tools_dir = Path(__file__).parent / "internal"
        if not tools_dir.exists():
            logger.warning(f"Tools directory not found: {tools_dir}")
            return

        # Find all Python files
        for tool_file in tools_dir.glob("*.py"):
            if tool_file.name.startswith("_"):
                continue

            try:
                # Import module
                module_name = f"tools.internal.{tool_file.stem}"
                module = importlib.import_module(module_name)

                # Find BaseTool subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseTool) and
                        obj is not BaseTool and
                        hasattr(obj, 'metadata')):

                        # Instantiate and register
                        tool_instance = obj()
                        self._tools[tool_instance.metadata.name] = tool_instance
                        logger.info(f"Discovered tool: {tool_instance.metadata.name}")

            except Exception as e:
                logger.error(f"Failed to load tool from {tool_file}: {e}")

        self._loaded = True
        logger.info(f"Loaded {len(self._tools)} tools")

    @classmethod
    def clear(cls):
        """Clear all tools (for testing)."""
        instance = cls()
        instance._tools = {}
        instance._loaded = False
```

---

### Task 2.3: Create DSPy Adapter

**New File:** `tools/adapters.py`

```python
import dspy
from tools.base import BaseTool, ToolResult
from typing import Callable
import json
import asyncio

class DSPyToolAdapter:
    """Adapts Pydantic BaseTool to DSPy-compatible callable."""

    @staticmethod
    def adapt(tool: BaseTool) -> Callable:
        """Convert BaseTool to function that DSPy ReAct can use."""

        async def tool_callable(**kwargs) -> str:
            """Async wrapper for tool execution."""

            # Execute tool
            result: ToolResult = await tool(**kwargs)

            # Format for DSPy
            if result.success:
                # Return JSON string for DSPy
                if isinstance(result.result, dict):
                    return json.dumps(result.result, indent=2)
                else:
                    return str(result.result)
            else:
                # Return error as JSON
                return json.dumps({
                    "error": result.error,
                    "metadata": result.metadata
                }, indent=2)

        # Set docstring for DSPy (used in prompts)
        tool_callable.__name__ = tool.metadata.name
        tool_callable.__doc__ = f"{tool.metadata.description}\n\nParameters:\n"

        for param in tool.metadata.parameters:
            required = " (required)" if param.required else " (optional)"
            tool_callable.__doc__ += f"  - {param.name}: {param.description}{required}\n"

        return tool_callable

    @staticmethod
    def adapt_all(tools: dict[str, BaseTool]) -> dict[str, Callable]:
        """Adapt all tools in a registry."""
        return {
            name: DSPyToolAdapter.adapt(tool)
            for name, tool in tools.items()
        }
```

---

### Task 2.4: Example Tool Implementation

**New File:** `tools/internal/clearbit_lookup.py`

```python
from tools.base import BaseTool, ToolMetadata, ToolParameter, ToolParameterType, ToolResult
import httpx
from config.settings import settings

class ClearbitPersonLookup(BaseTool):
    """Enriches lead data using Clearbit Person API."""

    metadata = ToolMetadata(
        name="clearbit_person_lookup",
        description="Lookup person information using email via Clearbit Person API",
        parameters=[
            ToolParameter(
                name="email",
                type=ToolParameterType.STRING,
                description="Email address to lookup",
                required=True
            ),
            ToolParameter(
                name="enrich_company",
                type=ToolParameterType.BOOLEAN,
                description="Also fetch company information",
                required=False,
                default=False
            )
        ],
        return_type="dict",
        category="enrichment",
        version="1.0.0",
        examples=[
            '{"email": "john@example.com", "enrich_company": true}',
            '{"email": "jane@company.io"}'
        ]
    )

    def __init__(self):
        super().__init__()
        self.api_key = settings.CLEARBIT_API_KEY
        self.base_url = "https://person.clearbit.com/v2"

    async def execute(self, email: str, enrich_company: bool = False) -> ToolResult:
        """Execute Clearbit person lookup."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/people/find",
                    params={"email": email},
                    auth=(self.api_key, ""),
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()

                    result = {
                        "name": data.get("name", {}).get("fullName"),
                        "title": data.get("employment", {}).get("title"),
                        "company": data.get("employment", {}).get("name"),
                        "location": data.get("location"),
                        "bio": data.get("bio"),
                        "linkedin": data.get("linkedin", {}).get("handle"),
                        "avatar": data.get("avatar")
                    }

                    if enrich_company and data.get("employment", {}).get("domain"):
                        company_data = await self._fetch_company(
                            data["employment"]["domain"]
                        )
                        result["company_details"] = company_data

                    return ToolResult(
                        success=True,
                        result=result,
                        metadata={"source": "clearbit"}
                    )

                elif response.status_code == 404:
                    return ToolResult(
                        success=True,
                        result={"found": False},
                        metadata={"reason": "Person not found in Clearbit"}
                    )

                else:
                    return ToolResult(
                        success=False,
                        error=f"Clearbit API error: {response.status_code}",
                        metadata={"status_code": response.status_code}
                    )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                error="Clearbit API timeout",
                metadata={"timeout": 10.0}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"exception_type": type(e).__name__}
            )

    async def _fetch_company(self, domain: str) -> dict:
        """Fetch company details from Clearbit Company API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://company.clearbit.com/v2/companies/find",
                params={"domain": domain},
                auth=(self.api_key, ""),
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "name": data.get("name"),
                    "domain": data.get("domain"),
                    "industry": data.get("category", {}).get("industry"),
                    "employees": data.get("metrics", {}).get("employees"),
                    "founded": data.get("foundedYear"),
                    "location": data.get("location")
                }

            return {}
```

---

### Task 2.5: Refactor ResearchAgent

**File:** `agents/research_agent.py` (BEFORE - 600 lines)

```python
class ResearchAgent:
    def __init__(self, ...):
        # 50+ lines of initialization

    async def search_knowledge_base(self, query: str) -> str:
        # 100 lines implementing RAG search

    async def wolfram_query(self, query: str) -> str:
        # 80 lines calling Wolfram Alpha

    async def clearbit_lookup(self, email: str) -> dict:
        # 70 lines calling Clearbit

    # ... 8 more tool methods (400+ lines)

    async def research(self, topic: str) -> str:
        # 50 lines calling tools manually
```

**File:** `agents/research_agent.py` (AFTER - 200 lines)

```python
from tools.registry import ToolRegistry
from tools.adapters import DSPyToolAdapter
import dspy

class ResearchAgent:
    def __init__(self, config: AgentConfig):
        self.config = config

        # Get all tools from registry
        all_tools = ToolRegistry.get_all()

        # Filter to research tools
        self.tools = {
            name: tool
            for name, tool in all_tools.items()
            if tool.metadata.category in ["research", "enrichment"]
        }

        # Convert to DSPy callables
        dspy_tools = DSPyToolAdapter.adapt_all(self.tools)

        # Create DSPy ReAct module
        self.react = dspy.ReAct(
            signature="question -> answer",
            tools=list(dspy_tools.values())
        )

    async def research(self, topic: str) -> str:
        """Research a topic using available tools."""

        # DSPy ReAct automatically selects and uses tools
        result = self.react(question=topic)

        return result.answer
```

**Reduction:** 600 lines → 200 lines (67% reduction)

---

### Acceptance Criteria (Phase 2)

- ✅ `BaseTool` class with Pydantic validation
- ✅ `ToolRegistry` discovers tools automatically
- ✅ `DSPyToolAdapter` converts tools to DSPy callables
- ✅ At least 3 example tools implemented
- ✅ ResearchAgent refactored to use registry
- ✅ All existing tests pass
- ✅ New tools can be added by dropping file in `tools/internal/`

**Time Estimate:** 1 week
**Risk:** Medium (major refactor)
**Rollback:** Keep old tool methods as fallback

---

## Phase 3: Enhanced Multi-Agent (Weeks 3-5)

### Priority: MEDIUM

**Goal:** Add agent-zero's superior-subordinate patterns to existing delegation

### Task 3.1: Parallel Agent Execution

**File:** `core/multi_agent.py` (new)

```python
import asyncio
from typing import List, Dict, Any
from pydantic import BaseModel
import dspy

class AgentTask(BaseModel):
    """Task for subordinate agent."""
    agent_profile: str
    task_description: str
    context: Dict[str, Any]
    timeout: int = 300  # 5 minutes

class AgentResult(BaseModel):
    """Result from subordinate agent."""
    agent_profile: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float

class ParallelAgentExecutor:
    """Execute multiple subordinate agents in parallel."""

    async def execute_parallel(
        self,
        tasks: List[AgentTask],
        superior_agent: Any
    ) -> List[AgentResult]:
        """Execute multiple agent tasks in parallel."""

        # Create coroutines for each task
        coroutines = [
            self._execute_single_task(task, superior_agent)
            for task in tasks
        ]

        # Run in parallel with timeout
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Convert to AgentResult
        return [
            result if isinstance(result, AgentResult) else AgentResult(
                agent_profile="unknown",
                success=False,
                result=None,
                error=str(result),
                execution_time=0.0
            )
            for result in results
        ]

    async def _execute_single_task(
        self,
        task: AgentTask,
        superior_agent: Any
    ) -> AgentResult:
        """Execute a single agent task."""

        import time
        start_time = time.time()

        try:
            # Spawn subordinate using existing delegation
            result = await superior_agent.delegation.call_subordinate(
                profile=task.agent_profile,
                message=task.task_description,
                reset=False
            )

            execution_time = time.time() - start_time

            return AgentResult(
                agent_profile=task.agent_profile,
                success=True,
                result=result,
                execution_time=execution_time
            )

        except asyncio.TimeoutError:
            return AgentResult(
                agent_profile=task.agent_profile,
                success=False,
                result=None,
                error=f"Timeout after {task.timeout}s",
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return AgentResult(
                agent_profile=task.agent_profile,
                success=False,
                result=None,
                error=str(e),
                execution_time=time.time() - start_time
            )
```

---

### Task 3.2: Update StrategyAgent

**File:** `agents/strategy_agent.py` (add parallel execution)

```python
from core.multi_agent import ParallelAgentExecutor, AgentTask

class StrategyAgent:
    # ... existing code ...

    async def comprehensive_market_analysis(
        self,
        state: StrategyState
    ) -> StrategyState:
        """Run comprehensive analysis using parallel subordinates."""

        # Define parallel tasks
        tasks = [
            AgentTask(
                agent_profile="competitor_analyst",
                task_description="Analyze top 3 competitors in healthcare practice management",
                context={"industry": "healthcare"}
            ),
            AgentTask(
                agent_profile="market_researcher",
                task_description="Research market trends in medical practice software",
                context={"market": "healthcare_software"}
            ),
            AgentTask(
                agent_profile="account_researcher",
                task_description="Find 10 high-potential accounts matching our ICP",
                context={"icp": state.get("ideal_customer_profile")}
            )
        ]

        # Execute in parallel (5-10x faster than sequential)
        executor = ParallelAgentExecutor()
        results = await executor.execute_parallel(tasks, self)

        # Synthesize results with DSPy
        synthesis = await self.synthesize_research(results)

        state["market_analysis"] = {
            "competitor_insights": results[0].result if results[0].success else None,
            "market_trends": results[1].result if results[1].success else None,
            "target_accounts": results[2].result if results[2].success else None,
            "synthesis": synthesis,
            "execution_time": sum(r.execution_time for r in results)
        }

        return state
```

---

### Acceptance Criteria (Phase 3)

- ✅ Parallel agent execution working
- ✅ StrategyAgent uses parallel tasks
- ✅ Performance improvement measured (5-10x faster)
- ✅ Error handling for parallel failures
- ✅ Tests for parallel execution
- ✅ Existing delegation still works

**Time Estimate:** 2 weeks
**Risk:** High (complex async coordination)
**Rollback:** Remove parallel executor, use sequential

---

## Phase 4: Production Hardening (Weeks 5-6)

### Priority: LOW (but important)

**Goal:** Ensure system is production-ready

### Task 4.1: Comprehensive Testing

```python
# tests/test_integration_e2e.py

@pytest.mark.asyncio
async def test_full_lead_qualification_flow():
    """End-to-end test of lead qualification with error recovery."""

    # 1. Receive webhook
    webhook_data = {...}
    response = await client.post("/webhooks/typeform", json=webhook_data)
    assert response.status_code == 200

    # 2. Verify event stored
    event = await supabase.table('raw_events').select().eq('id', event_id).single()
    assert event is not None

    # 3. Wait for processing
    await asyncio.sleep(5)

    # 4. Verify lead qualified
    lead = await supabase.table('leads').select().eq('typeform_id', ...).single()
    assert lead['tier'] in ['SCORCHING', 'HOT', 'WARM', 'COOL', 'COLD']
    assert lead['score'] >= 0 and lead['score'] <= 100

    # 5. Verify Slack notification
    # ... check Slack API mock

    # 6. Verify follow-up scheduled
    # ... check LangGraph state

@pytest.mark.asyncio
async def test_error_recovery_with_api_failure():
    """Test that API failures trigger recovery."""

    with patch('httpx.AsyncClient.get', side_effect=httpx.TimeoutException):
        # Should recover and return partial result
        result = await agent.qualify_lead(test_lead)
        assert result is not None
        # Should have used fallback or retry

@pytest.mark.asyncio
async def test_tool_registration_discovery():
    """Test that new tools are auto-discovered."""

    # Clear registry
    ToolRegistry.clear()

    # Load tools
    tools = ToolRegistry.get_all()

    # Should have all internal tools
    assert "clearbit_person_lookup" in tools
    assert "wolfram_strategic_query" in tools
    assert "search_knowledge_base" in tools
```

---

### Task 4.2: Monitoring & Observability

**File:** `core/monitoring.py` (new)

```python
from prometheus_client import Counter, Histogram, Gauge
import logging

# Metrics
agent_calls_total = Counter(
    'agent_calls_total',
    'Total agent method calls',
    ['agent_name', 'method', 'status']
)

agent_duration_seconds = Histogram(
    'agent_duration_seconds',
    'Agent method execution time',
    ['agent_name', 'method']
)

error_recovery_attempts = Counter(
    'error_recovery_attempts_total',
    'Total error recovery attempts',
    ['error_type', 'success']
)

tool_executions_total = Counter(
    'tool_executions_total',
    'Total tool executions',
    ['tool_name', 'success']
)

def track_agent_call(agent_name: str, method: str):
    """Decorator to track agent metrics."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with agent_duration_seconds.labels(
                agent_name=agent_name,
                method=method
            ).time():
                try:
                    result = await func(*args, **kwargs)
                    agent_calls_total.labels(
                        agent_name=agent_name,
                        method=method,
                        status='success'
                    ).inc()
                    return result
                except Exception as e:
                    agent_calls_total.labels(
                        agent_name=agent_name,
                        method=method,
                        status='error'
                    ).inc()
                    raise
        return wrapper
    return decorator
```

---

### Acceptance Criteria (Phase 4)

- ✅ 90%+ test coverage
- ✅ End-to-end tests passing
- ✅ Prometheus metrics exposed
- ✅ Error recovery metrics tracked
- ✅ Performance benchmarks documented
- ✅ Production deployment checklist complete

**Time Estimate:** 1 week
**Risk:** Low
**Rollback:** N/A (testing doesn't break prod)

---

## Code Templates

### Template 1: Creating a New Tool

```python
# tools/internal/my_new_tool.py

from tools.base import BaseTool, ToolMetadata, ToolParameter, ToolParameterType, ToolResult

class MyNewTool(BaseTool):
    """Description of what this tool does."""

    metadata = ToolMetadata(
        name="my_new_tool",
        description="One-line description",
        parameters=[
            ToolParameter(
                name="param1",
                type=ToolParameterType.STRING,
                description="What param1 does",
                required=True
            )
        ],
        return_type="dict",
        category="category_name",
        version="1.0.0"
    )

    async def execute(self, param1: str) -> ToolResult:
        """Execute the tool logic."""

        try:
            # Your logic here
            result = do_something(param1)

            return ToolResult(
                success=True,
                result=result
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
```

**That's it!** Tool is auto-discovered and available to all agents.

---

### Template 2: Adding Error Handling to Agent Method

```python
from core.decorators import with_retry_logic
from core.exceptions import RepairableException, ErrorContext, ErrorSeverity

class MyAgent:

    @with_retry_logic(max_attempts=3, enable_llm_recovery=True)
    async def my_method(self, data: MyData) -> MyResult:
        """Method with automatic error recovery."""

        try:
            # Your logic
            result = await self._process(data)
            return result

        except SpecificError as e:
            # Wrap in RepairableException for LLM recovery
            raise RepairableException(
                f"Processing failed: {str(e)}",
                context=ErrorContext(
                    error_type="ProcessingError",
                    error_message=str(e),
                    severity=ErrorSeverity.MEDIUM,
                    agent_name=self.__class__.__name__,
                    operation="my_method",
                    input_data=data.dict(),
                    recovery_hints=[
                        "Try with different parameters",
                        "Validate input data format"
                    ]
                )
            )
```

---

### Template 3: Using Tools in Agent

```python
from tools.registry import ToolRegistry
from tools.adapters import DSPyToolAdapter

class MyAgent:
    def __init__(self, config):
        self.config = config

        # Get tools you need
        self.tools = ToolRegistry.get_by_category("research")

        # Convert to DSPy callables
        dspy_tools = DSPyToolAdapter.adapt_all(self.tools)

        # Use with DSPy ReAct
        self.react = dspy.ReAct(
            signature="question -> answer",
            tools=list(dspy_tools.values())
        )

    async def research(self, question: str) -> str:
        # DSPy automatically selects and uses tools
        result = self.react(question=question)
        return result.answer
```

---

## Testing Strategy

### Unit Tests (Per Phase)

**Phase 0 (Bug Fixes):**
- Test `analyze_pipeline()` with mock Supabase
- Test `recommend_outbound_targets()` with mock API
- Verify no hardcoded data returned

**Phase 1 (Error Handling):**
- Test exception hierarchy
- Test DSPy error recovery
- Test `@with_retry_logic` decorator
- Test fallback values

**Phase 2 (Tools):**
- Test tool registration
- Test tool discovery
- Test DSPy adapter
- Test each tool individually

**Phase 3 (Multi-Agent):**
- Test parallel execution
- Test error handling in parallel
- Test result synthesis

**Phase 4 (Production):**
- End-to-end integration tests
- Performance benchmarks
- Load testing

### Integration Tests

```python
@pytest.mark.integration
async def test_tool_integration():
    """Test tools work end-to-end with agents."""

    # Register tools
    registry = ToolRegistry()
    tools = registry.get_all()

    # Create agent with tools
    agent = ResearchAgent(config)

    # Execute research
    result = await agent.research("What is DSPy?")

    # Should have used tools
    assert result is not None
    assert len(result) > 0
```

---

## Success Metrics

### Phase 0 (Bug Fixes)
- ✅ `analyze_pipeline()` returns real Supabase data
- ✅ `recommend_outbound_targets()` uses real patterns
- ✅ No regressions in existing tests

### Phase 1 (Error Handling)
- ✅ 80% reduction in unhandled exceptions
- ✅ 90%+ errors recovered automatically
- ✅ Mean time to recovery < 5 seconds

### Phase 2 (Tools)
- ✅ 67% reduction in agent code size
- ✅ 100% tools testable independently
- ✅ New tool added in < 30 minutes

### Phase 3 (Multi-Agent)
- ✅ 5-10x speedup for parallel tasks
- ✅ 100% error handling coverage
- ✅ Memory usage within limits

### Phase 4 (Production)
- ✅ 90%+ test coverage
- ✅ < 5% error rate
- ✅ < 200ms p95 latency

---

## Rollback Plans

### Phase 0
**Rollback:** Revert 2 function changes
**Time:** 5 minutes
**Risk:** None

### Phase 1
**Rollback:** Remove `@with_retry_logic` decorators
**Time:** 30 minutes
**Risk:** Low (decorators are opt-in)

### Phase 2
**Rollback:** Keep old tool methods, disable registry
**Time:** 1 hour
**Risk:** Medium (refactored agents need old code)

### Phase 3
**Rollback:** Remove parallel executor, use sequential
**Time:** 30 minutes
**Risk:** Low (parallel is additive)

### Phase 4
**Rollback:** N/A (tests don't affect production)
**Time:** N/A
**Risk:** None

---

## Critical Path

**Must Be Done First:**
1. Phase 0: Bug fixes (blocks everything)
2. Phase 1: Error handling (foundation for reliability)

**Can Be Done in Parallel:**
- Phase 2 (Tools) + Phase 3 (Multi-Agent) - independent

**Must Be Done Last:**
- Phase 4 (Production) - validates everything

---

## Quick Wins (Week 1)

**Day 1-2:**
- Fix `analyze_pipeline()` - 3 hours
- Fix `recommend_outbound_targets()` - 4 hours

**Day 3-4:**
- Create exception hierarchy - 4 hours
- Create DSPy error recovery - 4 hours

**Day 5:**
- Add `@with_retry_logic` decorator - 3 hours
- Test error handling - 2 hours

**Ship by Friday:**
- ✅ Both broken functions fixed
- ✅ Basic error handling working
- ✅ Zero regressions

---

## Next Steps

1. **Read this plan** - Understand the full scope
2. **Review broken functions** - Verify the diagnosis
3. **Start Phase 0** - Fix bugs first (5-7 hours)
4. **Deploy to staging** - Test with real data
5. **Begin Phase 1** - Add error handling
6. **Iterate weekly** - Ship improvements incrementally

---

## Conclusion

This plan provides a complete roadmap to transform hume-dspy-agent into a production-grade system that combines:

✅ **DSPy's reasoning excellence** (preserved)
✅ **Pydantic's type safety** (preserved)
✅ **agent-zero's extensibility** (added)
✅ **agent-zero's reliability** (added)
✅ **agent-zero's multi-agent patterns** (added)

**Timeline:** 6 weeks
**Risk:** Medium (managed through phased rollout)
**Reward:** Production-ready autonomous agent system

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Status:** ✅ Ready for Implementation
