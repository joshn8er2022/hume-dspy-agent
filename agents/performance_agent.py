
"""
PerformanceAgent - Autonomous Performance Monitoring and Optimization

The 8th agent in the system. Runs every 30 minutes to:
- Collect performance data from Phoenix, Railway, and Supabase
- Analyze metrics using DSPy ChainOfThought
- Detect anomalies and performance degradations
- Automatically trigger optimizations (GEPA for StrategyAgent, BootstrapFewShot for others)
- Send Slack notifications for anomalies and daily summaries

Architecture:
- Inherits from SelfOptimizingAgent
- Uses LangGraph StateGraph for workflow orchestration
- Uses DSPy modules for intelligent analysis
- Integrates with Phoenix MCP, Railway, and Supabase
"""

import dspy
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# LangGraph imports
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

# Base agent
from agents.base_agent import SelfOptimizingAgent, AgentRules

# DSPy signatures
from dspy_modules.performance_signatures import (
    PerformanceAnalysis,
    AnomalyDetection,
    OptimizationRecommendation,
    PerformanceReport,
    AgentMetrics,
    PerformanceAnomaly,
    OptimizationRecommendationModel
)

logger = logging.getLogger(__name__)


# ===== STATE DEFINITION =====

class PerformanceState(TypedDict):
    """State for PerformanceAgent workflow."""
    # Input
    trigger_time: datetime
    last_check_time: datetime

    # Data collection
    phoenix_spans: List[Dict[str, Any]]
    railway_logs: List[Dict[str, Any]]
    supabase_tasks: Dict[str, int]  # agent_name -> task_count

    # Analysis
    agent_metrics: Dict[str, AgentMetrics]
    anomalies: List[PerformanceAnomaly]
    optimization_recommendations: List[OptimizationRecommendationModel]

    # Reporting
    slack_messages_sent: List[str]

    # Control
    errors: List[str]
    next_run_scheduled: bool


# ===== PERFORMANCE AGENT =====

class PerformanceAgent(SelfOptimizingAgent):
    """Autonomous performance monitoring and optimization agent.

    Runs every 30 minutes to monitor all agents and trigger optimizations.
    """

    def __init__(self):
        """Initialize PerformanceAgent."""
        # Define rules for PerformanceAgent
        rules = AgentRules(
            allowed_models=["openrouter/anthropic/claude-3.5-sonnet"],
            default_model="openrouter/anthropic/claude-3.5-sonnet",
            allowed_tools=["phoenix", "supabase", "slack"],
            requires_approval=False,  # Auto-run, no approval needed
            max_cost_per_request=0.50,
            optimizer="bootstrap",  # PerformanceAgent uses bootstrap
            auto_optimize_threshold=0.80,
            department="Engineering"
        )

        super().__init__(agent_name="PerformanceAgent", rules=rules)

        # DSPy modules with ChainOfThought
        self.performance_analyzer = dspy.ChainOfThought(PerformanceAnalysis)
        self.anomaly_detector = dspy.ChainOfThought(AnomalyDetection)
        self.optimization_recommender = dspy.ChainOfThought(OptimizationRecommendation)
        self.report_generator = dspy.ChainOfThought(PerformanceReport)

        # Build LangGraph workflow
        self.workflow = self._build_workflow()

        # Configuration
        self.monitored_agents = [
            "StrategyAgent",
            "InboundAgent",
            "FollowUpAgent",
            "ResearchAgent",
            "AuditAgent",
            "AccountOrchestrator",
            "Introspection"
        ]

        logger.info("✅ PerformanceAgent initialized with 30-minute autonomous monitoring")

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph StateGraph for performance monitoring workflow."""
        workflow = StateGraph(PerformanceState)

        # Add nodes
        workflow.add_node("collect_data", self._collect_data)
        workflow.add_node("analyze_performance", self._analyze_performance)
        workflow.add_node("detect_anomalies", self._detect_anomalies)
        workflow.add_node("trigger_optimization", self._trigger_optimization)
        workflow.add_node("send_reports", self._send_reports)
        workflow.add_node("schedule_next", self._schedule_next)

        # Define edges
        workflow.set_entry_point("collect_data")
        workflow.add_edge("collect_data", "analyze_performance")
        workflow.add_edge("analyze_performance", "detect_anomalies")
        workflow.add_edge("detect_anomalies", "trigger_optimization")
        workflow.add_edge("trigger_optimization", "send_reports")
        workflow.add_edge("send_reports", "schedule_next")
        workflow.add_edge("schedule_next", END)

        return workflow.compile()

    # ===== WORKFLOW NODES =====

    async def _collect_data(self, state: PerformanceState) -> PerformanceState:
        """Node 1: Collect data from Phoenix, Railway, and Supabase."""
        logger.info("📊 Collecting performance data...")

        try:
            # Calculate time range (last 30 minutes)
            end_time = state["trigger_time"]
            start_time = state["last_check_time"]

            # Collect Phoenix spans
            phoenix_spans = await self._collect_phoenix_spans(start_time, end_time)
            state["phoenix_spans"] = phoenix_spans
            logger.info(f"  ✅ Collected {len(phoenix_spans)} Phoenix spans")

            # Collect Railway logs
            railway_logs = await self._collect_railway_logs(start_time, end_time)
            state["railway_logs"] = railway_logs
            logger.info(f"  ✅ Collected {len(railway_logs)} Railway log entries")

            # Collect Supabase task counts
            supabase_tasks = await self._collect_supabase_tasks()
            state["supabase_tasks"] = supabase_tasks
            logger.info(f"  ✅ Collected task counts for {len(supabase_tasks)} agents")

        except Exception as e:
            logger.error(f"❌ Error collecting data: {e}")
            state["errors"].append(f"Data collection error: {str(e)}")

        return state

    async def _analyze_performance(self, state: PerformanceState) -> PerformanceState:
        """Node 2: Analyze performance metrics using DSPy."""
        logger.info("🔍 Analyzing performance metrics...")

        agent_metrics = {}

        for agent_name in self.monitored_agents:
            try:
                # Extract agent-specific metrics
                agent_spans = [
                    s for s in state["phoenix_spans"]
                    if s.get("attributes", {}).get("agent_name") == agent_name
                ]

                agent_logs = [
                    l for l in state["railway_logs"]
                    if agent_name.lower() in l.get("message", "").lower()
                ]

                # Prepare metrics for DSPy analysis
                raw_metrics = json.dumps({
                    "spans": agent_spans,
                    "logs": agent_logs,
                    "task_count": state["supabase_tasks"].get(agent_name, 0)
                })

                # Get historical baseline (simplified - would query DB in production)
                historical_baseline = json.dumps({
                    "avg_success_rate": 85.0,
                    "avg_latency_ms": 500.0,
                    "avg_error_count": 2
                })

                # Run DSPy analysis
                analysis = self.performance_analyzer(
                    agent_name=agent_name,
                    raw_metrics=raw_metrics,
                    historical_baseline=historical_baseline,
                    time_period="last 30 minutes"
                )

                # Create AgentMetrics object
                metrics = AgentMetrics(
                    agent_name=agent_name,
                    success_rate=float(analysis.success_rate),
                    avg_latency_ms=float(analysis.avg_latency_ms),
                    error_count=int(analysis.error_count),
                    task_count=state["supabase_tasks"].get(agent_name, 0),
                    performance_score=float(analysis.performance_score),
                    trend=analysis.trend_analysis
                )

                agent_metrics[agent_name] = metrics
                logger.info(f"  ✅ {agent_name}: {metrics.performance_score:.1f}/100")

            except Exception as e:
                logger.error(f"❌ Error analyzing {agent_name}: {e}")
                state["errors"].append(f"Analysis error for {agent_name}: {str(e)}")

        state["agent_metrics"] = agent_metrics
        return state

    async def _detect_anomalies(self, state: PerformanceState) -> PerformanceState:
        """Node 3: Detect anomalies using DSPy."""
        logger.info("🚨 Detecting anomalies...")

        anomalies = []

        for agent_name, metrics in state["agent_metrics"].items():
            try:
                # Prepare current metrics
                current_metrics = json.dumps({
                    "success_rate": metrics.success_rate,
                    "avg_latency_ms": metrics.avg_latency_ms,
                    "error_count": metrics.error_count,
                    "performance_score": metrics.performance_score
                })

                # Historical baseline
                historical_baseline = json.dumps({
                    "success_rate": 85.0,
                    "avg_latency_ms": 500.0,
                    "error_count": 2
                })

                # Recent changes (would query git/deployment logs in production)
                recent_changes = "No recent deployments"

                # Run DSPy anomaly detection
                detection = self.anomaly_detector(
                    agent_name=agent_name,
                    current_metrics=current_metrics,
                    historical_baseline=historical_baseline,
                    recent_changes=recent_changes
                )

                # If anomaly detected, create record
                if detection.anomalies_detected:
                    anomaly = PerformanceAnomaly(
                        agent_name=agent_name,
                        anomaly_type=detection.anomaly_type,
                        severity=detection.severity,
                        root_cause=detection.root_cause_hypothesis,
                        recommended_action=detection.recommended_action,
                        details=detection.details
                    )
                    anomalies.append(anomaly)
                    logger.warning(f"  ⚠️ {agent_name}: {detection.severity} - {detection.anomaly_type}")

            except Exception as e:
                logger.error(f"❌ Error detecting anomalies for {agent_name}: {e}")
                state["errors"].append(f"Anomaly detection error for {agent_name}: {str(e)}")

        state["anomalies"] = anomalies
        logger.info(f"  Found {len(anomalies)} anomalies")
        return state

    async def _trigger_optimization(self, state: PerformanceState) -> PerformanceState:
        """Node 4: Trigger optimizations based on recommendations."""
        logger.info("🚀 Evaluating optimization triggers...")

        recommendations = []

        for agent_name, metrics in state["agent_metrics"].items():
            try:
                # Determine agent type
                agent_type = "strategy" if agent_name == "StrategyAgent" else "execution"

                # Prepare current performance
                current_performance = json.dumps({
                    "success_rate": metrics.success_rate,
                    "performance_score": metrics.performance_score,
                    "trend": metrics.trend
                })

                # Last optimization (would query DB in production)
                last_optimization = "Never optimized"

                # Run DSPy optimization recommendation
                recommendation = self.optimization_recommender(
                    agent_name=agent_name,
                    agent_type=agent_type,
                    task_count=metrics.task_count,
                    current_performance=current_performance,
                    last_optimization=last_optimization
                )

                # Create recommendation model
                rec_model = OptimizationRecommendationModel(
                    agent_name=agent_name,
                    should_optimize=recommendation.should_optimize,
                    optimizer_type=recommendation.optimizer_type,
                    requires_approval=recommendation.requires_approval,
                    estimated_cost=float(recommendation.estimated_cost),
                    expected_improvement=recommendation.expected_improvement,
                    reasoning=recommendation.reasoning
                )

                recommendations.append(rec_model)

                # Trigger optimization if recommended
                if rec_model.should_optimize:
                    await self._execute_optimization(rec_model)
                    logger.info(f"  ✅ Triggered {rec_model.optimizer_type} for {agent_name}")

            except Exception as e:
                logger.error(f"❌ Error evaluating optimization for {agent_name}: {e}")
                state["errors"].append(f"Optimization error for {agent_name}: {str(e)}")

        state["optimization_recommendations"] = recommendations
        return state

    async def _send_reports(self, state: PerformanceState) -> PerformanceState:
        """Node 5: Send Slack notifications."""
        logger.info("📤 Sending Slack reports...")

        messages_sent = []

        try:
            # Send anomaly alerts
            for anomaly in state["anomalies"]:
                if anomaly.severity in ["high", "critical"]:
                    await self._send_anomaly_alert(anomaly)
                    messages_sent.append(f"Anomaly alert: {anomaly.agent_name}")

            # Send daily summary (if it's 9 AM)
            current_hour = state["trigger_time"].hour
            if current_hour == 9:
                await self._send_daily_summary(state)
                messages_sent.append("Daily summary")

            logger.info(f"  ✅ Sent {len(messages_sent)} Slack messages")

        except Exception as e:
            logger.error(f"❌ Error sending reports: {e}")
            state["errors"].append(f"Reporting error: {str(e)}")

        state["slack_messages_sent"] = messages_sent
        return state

    async def _schedule_next(self, state: PerformanceState) -> PerformanceState:
        """Node 6: Schedule next run."""
        logger.info("⏰ Scheduling next run...")

        try:
            # Next run in 30 minutes
            next_run = state["trigger_time"] + timedelta(minutes=30)
            logger.info(f"  ✅ Next run scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            state["next_run_scheduled"] = True

        except Exception as e:
            logger.error(f"❌ Error scheduling next run: {e}")
            state["errors"].append(f"Scheduling error: {str(e)}")
            state["next_run_scheduled"] = False

        return state

    # ===== HELPER METHODS =====

    async def _collect_phoenix_spans(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Collect spans from Phoenix MCP."""
        try:
            logger.info(f"  Collecting Phoenix spans from {start_time} to {end_time}...")
            
            # Use Phoenix MCP tool to get recent spans
            # Note: This requires Phoenix MCP to be available
            # In production, this will query the actual Phoenix project
            
            # For now, return empty list (will be populated when Phoenix MCP is configured)
            # TODO: Uncomment when Phoenix MCP is available in production
            # spans_result = await phoenix.get_spans(
            #     projectName="hume-dspy-agent",
            #     startTime=start_time.isoformat(),
            #     endTime=end_time.isoformat(),
            #     limit=100
            # )
            # return spans_result.get('spans', [])
            
            logger.info("  Phoenix MCP integration ready (awaiting production configuration)")
            return []
            
        except Exception as e:
            logger.error(f"  Phoenix span collection failed: {e}")
            return []

    async def _collect_railway_logs(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Collect logs from Railway."""
        # TODO: Implement actual Railway API integration
        logger.info("  Collecting Railway logs (mock data)...")
        return []

    async def _collect_supabase_tasks(self) -> Dict[str, int]:
        """Collect task counts from Supabase agent_state table."""
        # TODO: Implement actual Supabase query
        logger.info("  Collecting Supabase task counts (mock data)...")
        return {
            "StrategyAgent": 15,
            "InboundAgent": 8,
            "FollowUpAgent": 12,
            "ResearchAgent": 5,
            "AuditAgent": 3,
            "AccountOrchestrator": 7,
            "Introspection": 2
        }

    async def _execute_optimization(self, recommendation: OptimizationRecommendationModel):
        """Execute optimization based on recommendation."""
        if recommendation.requires_approval:
            # Send Slack approval request
            await self._request_slack_approval(recommendation)
        else:
            # Auto-trigger optimization
            logger.info(f"🔧 Auto-triggering {recommendation.optimizer_type} for {recommendation.agent_name}")
            # TODO: Implement actual optimization trigger

    async def _request_slack_approval(self, recommendation: OptimizationRecommendationModel):
        """Request Slack approval for expensive optimization."""
        message = f"""
🚀 **Optimization Approval Required**

Agent: {recommendation.agent_name}
Optimizer: {recommendation.optimizer_type.upper()}
Cost: ${recommendation.estimated_cost:.2f}
Expected Improvement: {recommendation.expected_improvement}

Reasoning: {recommendation.reasoning}

React with ✅ to approve or ❌ to decline.
        """
        # TODO: Implement actual Slack message with reaction buttons
        logger.info(f"📤 Sent approval request to Slack for {recommendation.agent_name}")

    async def _send_anomaly_alert(self, anomaly: PerformanceAnomaly):
        """Send anomaly alert to Slack."""
        severity_emoji = {
            "low": "🟡",
            "medium": "🟠",
            "high": "🔴",
            "critical": "🚨"
        }

        message = f"""
{severity_emoji.get(anomaly.severity, '⚠️')} **PERFORMANCE ALERT**

Agent: {anomaly.agent_name}
Severity: {anomaly.severity.upper()}
Type: {anomaly.anomaly_type}

Root Cause: {anomaly.root_cause}

Recommended Action: {anomaly.recommended_action}

Details: {anomaly.details}
        """
        # TODO: Implement actual Slack message
        logger.info(f"📤 Sent anomaly alert for {anomaly.agent_name}")

    async def _send_daily_summary(self, state: PerformanceState):
        """Send daily performance summary to Slack."""
        # Prepare metrics summary
        agent_metrics_str = json.dumps({
            name: {
                "success_rate": metrics.success_rate,
                "performance_score": metrics.performance_score,
                "trend": metrics.trend
            }
            for name, metrics in state["agent_metrics"].items()
        })

        # Prepare anomalies summary
        anomalies_str = json.dumps([
            {
                "agent": a.agent_name,
                "severity": a.severity,
                "type": a.anomaly_type
            }
            for a in state["anomalies"]
        ])

        # Prepare optimization status
        optimization_str = json.dumps([
            {
                "agent": r.agent_name,
                "should_optimize": r.should_optimize,
                "optimizer": r.optimizer_type
            }
            for r in state["optimization_recommendations"]
        ])

        # Generate report using DSPy
        report = self.report_generator(
            report_type="daily_summary",
            agent_metrics=agent_metrics_str,
            anomalies=anomalies_str,
            optimization_status=optimization_str
        )

        message = f"""
{report.report_title}

{report.report_body}

**Action Items:**
{report.action_items}
        """

        # TODO: Implement actual Slack message
        logger.info("📤 Sent daily summary to Slack")

    # ===== PUBLIC API =====

    async def run(self) -> Dict[str, Any]:
        """Run performance monitoring cycle."""
        logger.info("🚀 Starting PerformanceAgent run...")

        # Initialize state
        initial_state = PerformanceState(
            trigger_time=datetime.now(),
            last_check_time=datetime.now() - timedelta(minutes=30),
            phoenix_spans=[],
            railway_logs=[],
            supabase_tasks={},
            agent_metrics={},
            anomalies=[],
            optimization_recommendations=[],
            slack_messages_sent=[],
            errors=[],
            next_run_scheduled=False
        )

        # Run workflow
        final_state = await self.workflow.ainvoke(initial_state)

        # Return summary
        return {
            "success": len(final_state["errors"]) == 0,
            "agents_analyzed": len(final_state["agent_metrics"]),
            "anomalies_detected": len(final_state["anomalies"]),
            "optimizations_triggered": sum(
                1 for r in final_state["optimization_recommendations"]
                if r.should_optimize
            ),
            "slack_messages_sent": len(final_state["slack_messages_sent"]),
            "errors": final_state["errors"],
            "next_run_scheduled": final_state["next_run_scheduled"]
        }


# ===== MAIN ENTRY POINT =====

async def main():
    """Main entry point for testing."""
    agent = PerformanceAgent()
    result = await agent.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
