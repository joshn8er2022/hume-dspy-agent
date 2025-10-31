
"""
DSPy Signatures for PerformanceAgent

Provides intelligent analysis, anomaly detection, and optimization recommendations
for autonomous performance monitoring and self-optimization.
"""

import dspy
from typing import List, Optional
from pydantic import BaseModel, Field


# ===== PERFORMANCE ANALYSIS =====

class PerformanceAnalysis(dspy.Signature):
    """Analyze raw performance metrics and generate insights.

    Takes raw metrics from Phoenix traces, Railway logs, and Supabase
    and produces aggregated analysis with success rates, latencies, and trends.
    """

    # Inputs
    agent_name: str = dspy.InputField(desc="Name of the agent being analyzed")
    raw_metrics: str = dspy.InputField(
        desc="Raw metrics JSON containing traces, logs, and task counts"
    )
    historical_baseline: str = dspy.InputField(
        desc="Historical baseline metrics for comparison"
    )
    time_period: str = dspy.InputField(
        desc="Time period of analysis (e.g., 'last 30 minutes')"
    )

    # Outputs
    success_rate: float = dspy.OutputField(
        desc="Overall success rate as percentage (0-100)"
    )
    avg_latency_ms: float = dspy.OutputField(
        desc="Average latency in milliseconds"
    )
    error_count: int = dspy.OutputField(
        desc="Total number of errors in period"
    )
    performance_score: float = dspy.OutputField(
        desc="Overall performance score (0-100)"
    )
    trend_analysis: str = dspy.OutputField(
        desc="Trend analysis: improving, stable, or degrading"
    )
    key_insights: str = dspy.OutputField(
        desc="Key insights and observations about performance"
    )


# ===== ANOMALY DETECTION =====

class AnomalyDetection(dspy.Signature):
    """Detect performance anomalies and degradations.

    Identifies unusual patterns, error spikes, latency increases,
    and other performance issues requiring attention.
    """

    # Inputs
    agent_name: str = dspy.InputField(desc="Name of the agent")
    current_metrics: str = dspy.InputField(
        desc="Current performance metrics"
    )
    historical_baseline: str = dspy.InputField(
        desc="Historical baseline for comparison"
    )
    recent_changes: str = dspy.InputField(
        desc="Recent code changes or deployments"
    )

    # Outputs
    anomalies_detected: bool = dspy.OutputField(
        desc="Whether anomalies were detected"
    )
    anomaly_type: str = dspy.OutputField(
        desc="Type of anomaly: error_spike, latency_increase, success_drop, or none"
    )
    severity: str = dspy.OutputField(
        desc="Severity level: low, medium, high, or critical"
    )
    root_cause_hypothesis: str = dspy.OutputField(
        desc="Hypothesis about root cause of anomaly"
    )
    recommended_action: str = dspy.OutputField(
        desc="Recommended immediate action"
    )
    details: str = dspy.OutputField(
        desc="Detailed explanation of the anomaly"
    )


# ===== OPTIMIZATION RECOMMENDATION =====

class OptimizationRecommendation(dspy.Signature):
    """Recommend optimization strategy based on agent performance.

    Determines whether to trigger GEPA (for StrategyAgent with 20+ tasks)
    or BootstrapFewShot (for execution agents with 10+ tasks).
    """

    # Inputs
    agent_name: str = dspy.InputField(desc="Name of the agent")
    agent_type: str = dspy.InputField(
        desc="Agent type: strategy or execution"
    )
    task_count: int = dspy.InputField(
        desc="Number of tasks collected for optimization"
    )
    current_performance: str = dspy.InputField(
        desc="Current performance metrics"
    )
    last_optimization: str = dspy.InputField(
        desc="When agent was last optimized"
    )

    # Outputs
    should_optimize: bool = dspy.OutputField(
        desc="Whether optimization should be triggered"
    )
    optimizer_type: str = dspy.OutputField(
        desc="Recommended optimizer: gepa, bootstrap, or none"
    )
    requires_approval: bool = dspy.OutputField(
        desc="Whether Slack approval is required"
    )
    estimated_cost: float = dspy.OutputField(
        desc="Estimated cost in USD"
    )
    expected_improvement: str = dspy.OutputField(
        desc="Expected performance improvement range"
    )
    reasoning: str = dspy.OutputField(
        desc="Reasoning for the recommendation"
    )


# ===== PERFORMANCE REPORT =====

class PerformanceReport(dspy.Signature):
    """Generate formatted performance report for Slack.

    Creates human-readable daily summaries and anomaly alerts
    with proper formatting and actionable insights.
    """

    # Inputs
    report_type: str = dspy.InputField(
        desc="Type of report: daily_summary or anomaly_alert"
    )
    agent_metrics: str = dspy.InputField(
        desc="Metrics for all agents"
    )
    anomalies: str = dspy.InputField(
        desc="Detected anomalies"
    )
    optimization_status: str = dspy.InputField(
        desc="Current optimization status and recommendations"
    )

    # Outputs
    report_title: str = dspy.OutputField(
        desc="Report title with emoji"
    )
    report_body: str = dspy.OutputField(
        desc="Formatted report body with sections"
    )
    priority_level: str = dspy.OutputField(
        desc="Priority: info, warning, or critical"
    )
    action_items: str = dspy.OutputField(
        desc="Specific action items for the team"
    )


# ===== PYDANTIC MODELS FOR TYPE SAFETY =====

class AgentMetrics(BaseModel):
    """Performance metrics for a single agent."""
    agent_name: str
    success_rate: float = Field(ge=0.0, le=100.0)
    avg_latency_ms: float = Field(ge=0.0)
    error_count: int = Field(ge=0)
    task_count: int = Field(ge=0)
    performance_score: float = Field(ge=0.0, le=100.0)
    trend: str = Field(pattern="^(improving|stable|degrading)$")


class PerformanceAnomaly(BaseModel):
    """Detected performance anomaly."""
    agent_name: str
    anomaly_type: str
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    root_cause: str
    recommended_action: str
    details: str


class OptimizationRecommendationModel(BaseModel):
    """Optimization recommendation."""
    agent_name: str
    should_optimize: bool
    optimizer_type: str = Field(pattern="^(gepa|bootstrap|none)$")
    requires_approval: bool
    estimated_cost: float
    expected_improvement: str
    reasoning: str
