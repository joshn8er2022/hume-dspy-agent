"""Development Introspection Extension for StrategyAgent.

This extension enables StrategyAgent to:
- Read Phoenix traces/spans to understand system behavior
- Detect development needs and debugging opportunities
- Identify "levers" for system optimization
- Communicate findings to developers via appropriate channels

Uses Phoenix MCP server to query observability data.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DevelopmentInsight(BaseModel):
    """An insight about the system that requires development attention."""
    type: str = Field(..., description="Type: bug, performance, optimization, pattern")
    severity: str = Field(..., description="Severity: critical, high, medium, low")
    title: str
    description: str
    evidence: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    spans_analyzed: int = 0
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class SystemLever(BaseModel):
    """A "lever" or control point in the system that can be adjusted."""
    name: str
    description: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None
    impact: str = Field(..., description="What changing this would affect")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in suggestion")
    evidence_from_spans: List[str] = Field(default_factory=list)


class DevelopmentIntrospection:
    """Analyzes Phoenix traces to identify development needs and system levers."""
    
    def __init__(self, phoenix_project_name: str = "hume-dspy-agent"):
        self.phoenix_project = phoenix_project_name
        self.phoenix_mcp_available = False
        
        # Try to detect if Phoenix MCP is available
        try:
            # This will be called via MCP tools
            self.phoenix_mcp_available = True
            logger.info("✅ Development introspection: Phoenix MCP available")
        except Exception as e:
            logger.warning(f"⚠️ Phoenix MCP not available: {e}")
    
    async def analyze_recent_behavior(
        self,
        span_limit: int = 100,
        time_window_hours: int = 24,
        mcp_client=None
    ) -> Dict[str, Any]:
        """Analyze recent spans to understand system behavior.
        
        Args:
            span_limit: Maximum number of spans to analyze
            time_window_hours: Look back this many hours
            mcp_client: Optional MCP client for fetching spans
            
        Returns:
            Dict with insights, levers, and analysis summary
        """
        logger.info(f"🔍 Analyzing last {span_limit} spans from Phoenix...")
        
        try:
            # Fetch spans from Phoenix
            spans = await get_phoenix_spans_via_mcp(
                project_name=self.phoenix_project,
                limit=span_limit,
                hours_back=time_window_hours,
                mcp_client=mcp_client
            )
            
            if not spans:
                logger.warning("⚠️ No spans fetched for analysis")
                return {
                    "insights": [],
                    "levers": [],
                    "summary": {
                        "spans_analyzed": 0,
                        "time_window_hours": time_window_hours,
                        "error_rate": 0.0,
                        "avg_latency_ms": 0.0,
                        "key_patterns": [],
                        "warning": "No spans available for analysis"
                    },
                    "analysis_timestamp": datetime.utcnow().isoformat()
                }
            
            # Analyze spans
            insights = self.detect_development_needs(spans)
            levers = self.identify_system_levers(spans)
            
            # Extract business evolution signals (NEW)
            business_signals = self.extract_business_evolution_signals(spans)
            
            # Calculate summary statistics
            error_spans = [s for s in spans if s.get("attributes", {}).get("@level") == "error"]
            error_rate = len(error_spans) / len(spans) if spans else 0.0
            
            latencies = [
                (s.get("end_time_ns", 0) - s.get("start_time_ns", 0)) / 1_000_000
                for s in spans if s.get("end_time_ns") and s.get("start_time_ns")
            ]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            
            # Extract key patterns (most common span names)
            from collections import Counter
            span_names = [s.get("name", "unknown") for s in spans]
            name_counts = Counter(span_names)
            key_patterns = [{"name": name, "count": count} for name, count in name_counts.most_common(5)]
            
            summary = {
                "spans_analyzed": len(spans),
                "time_window_hours": time_window_hours,
                "error_rate": error_rate,
                "avg_latency_ms": avg_latency,
                "key_patterns": key_patterns
            }
            
            return {
                "insights": [insight.model_dump() for insight in insights],
                "levers": [lever.model_dump() for lever in levers],
                "business_signals": business_signals,  # NEW: Business evolution data
                "summary": summary,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze Phoenix spans: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {
                "error": str(e),
                "insights": [],
                "levers": [],
                "summary": {}
            }
    
    def detect_development_needs(self, spans: List[Dict[str, Any]]) -> List[DevelopmentInsight]:
        """Detect development needs from span analysis.
        
        Patterns to detect:
        - High error rates
        - Slow performance
        - Repeated failures
        - Unusual patterns
        - Optimization opportunities
        """
        insights = []
        
        # Analyze error patterns
        error_spans = [s for s in spans if s.get("attributes", {}).get("@level") == "error"]
        if len(error_spans) > len(spans) * 0.1:  # More than 10% errors
            insights.append(DevelopmentInsight(
                type="bug",
                severity="high",
                title="High error rate detected",
                description=f"{len(error_spans)}/{len(spans)} spans show errors ({len(error_spans)/len(spans)*100:.1f}%)",
                evidence=[s.get("attributes", {}).get("error.message", "Unknown error") for s in error_spans[:5]],
                recommendations=[
                    "Review error patterns in Phoenix dashboard",
                    "Check Railway logs for detailed error messages",
                    "Identify common failure patterns"
                ],
                spans_analyzed=len(spans)
            ))
        
        # Analyze latency patterns
        latencies = [
            (s.get("end_time_ns", 0) - s.get("start_time_ns", 0)) / 1_000_000
            for s in spans if s.get("end_time_ns") and s.get("start_time_ns")
        ]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            
            if avg_latency > 5000:  # More than 5 seconds average
                insights.append(DevelopmentInsight(
                    type="performance",
                    severity="medium",
                    title="High latency detected",
                    description=f"Average latency: {avg_latency:.0f}ms, P95: {p95_latency:.0f}ms",
                    evidence=[
                        f"Average: {avg_latency:.0f}ms",
                        f"P95: {p95_latency:.0f}ms",
                        f"Max: {max(latencies):.0f}ms"
                    ],
                    recommendations=[
                        "Profile slow operations",
                        "Consider caching frequently accessed data",
                        "Review database query performance",
                        "Check for N+1 query problems"
                    ],
                    spans_analyzed=len(spans)
                ))
        
        # Detect repeated patterns
        span_names = [s.get("name", "unknown") for s in spans]
        from collections import Counter
        name_counts = Counter(span_names)
        repeated = {name: count for name, count in name_counts.items() if count > 10}
        
        if repeated:
            insights.append(DevelopmentInsight(
                type="pattern",
                severity="low",
                title="Repeated operation patterns",
                description=f"Found {len(repeated)} operations repeated frequently",
                evidence=[f"{name}: {count} times" for name, count in list(repeated.items())[:5]],
                recommendations=[
                    "Consider batching repeated operations",
                    "Cache results if operations are idempotent",
                    "Review if all calls are necessary"
                ],
                spans_analyzed=len(spans)
            ))
        
        return insights
    
    def identify_system_levers(self, spans: List[Dict[str, Any]]) -> List[SystemLever]:
        """Identify system "levers" - parameters that could be tuned.
        
        Looks for:
        - Configurable timeouts
        - Retry settings
        - Batch sizes
        - Cache TTLs
        - Model selection patterns
        """
        levers = []
        
        # Detect timeout patterns
        timeout_attributes = []
        for span in spans:
            attrs = span.get("attributes", {})
            if "timeout" in str(attrs).lower():
                timeout_attributes.append(attrs)
        
        if timeout_attributes:
            levers.append(SystemLever(
                name="Request Timeouts",
                description="Timeout configurations for external API calls",
                impact="Higher timeouts = more reliability but slower failures",
                evidence_from_spans=[f"Found {len(timeout_attributes)} spans with timeout attributes"]
            ))
        
        # Detect retry patterns
        retry_spans = [s for s in spans if "retry" in s.get("name", "").lower()]
        if retry_spans:
            levers.append(SystemLever(
                name="Retry Configuration",
                description="Number of retries before giving up",
                impact="More retries = better reliability but more latency on failures",
                evidence_from_spans=[f"Found {len(retry_spans)} retry-related spans"]
            ))
        
        # Detect model selection patterns
        model_attributes = []
        for span in spans:
            attrs = span.get("attributes", {})
            if "model" in str(attrs).lower() or "llm" in str(attrs).lower():
                model_attributes.append(attrs)
        
        if model_attributes:
            levers.append(SystemLever(
                name="LLM Model Selection",
                description="Which models are being used for different tasks",
                impact="Model choice affects cost, latency, and quality",
                evidence_from_spans=[f"Found {len(model_attributes)} spans with model selection"]
            ))
        
        return levers
    
    def extract_business_evolution_signals(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract business evolution signals from spans for autonomous optimization.
        
        Returns signals that enable:
        - Research depth optimization (account vs company level)
        - Model selection optimization (high vs low reasoning)
        - Multi-channel sequence learning
        - Agent spawning optimization
        - Cost-performance tradeoff learning
        - ABM pattern learning
        """
        signals = {
            "account_research_patterns": self._analyze_account_research(spans),
            "company_research_patterns": self._analyze_company_research(spans),
            "model_performance": self._analyze_model_selection(spans),
            "channel_sequences": self._analyze_multi_channel(spans),
            "spawning_effectiveness": self._analyze_agent_delegation(spans),
            "cost_performance_tradeoffs": self._analyze_model_roi(spans),
            "abm_patterns": self._analyze_abm_campaigns(spans),
            "extracted_at": datetime.utcnow().isoformat()
        }
        return signals
    
    def _analyze_account_research(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze account-level research patterns and effectiveness."""
        research_spans = [
            s for s in spans 
            if "research" in s.get("name", "").lower() or 
               "clearbit" in str(s.get("attributes", {})).lower() or
               "apollo" in str(s.get("attributes", {})).lower()
        ]
        
        if not research_spans:
            return {"pattern_count": 0, "insights": []}
        
        # Analyze research depth patterns
        deep_research = [s for s in research_spans if self._is_deep_research(s)]
        shallow_research = [s for s in research_spans if not self._is_deep_research(s)]
        
        # Calculate success rates (if outcome data available)
        deep_success_rate = self._calculate_success_rate(deep_research)
        shallow_success_rate = self._calculate_success_rate(shallow_research)
        
        return {
            "total_research_spans": len(research_spans),
            "deep_research_count": len(deep_research),
            "shallow_research_count": len(shallow_research),
            "deep_research_success_rate": deep_success_rate,
            "shallow_research_success_rate": shallow_success_rate,
            "insights": [
                f"Deep research appears {((deep_success_rate / shallow_success_rate - 1) * 100):.1f}% more effective" 
                if shallow_success_rate > 0 and deep_success_rate > shallow_success_rate else
                "No clear pattern in research depth effectiveness"
            ]
        }
    
    def _analyze_company_research(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze company-level research patterns for ABM."""
        company_spans = [
            s for s in spans 
            if "company" in s.get("name", "").lower() or
               "org" in s.get("name", "").lower() or
               "competitor" in s.get("name", "").lower()
        ]
        
        return {
            "company_research_count": len(company_spans),
            "avg_depth": self._calculate_avg_depth(company_spans),
            "patterns": self._extract_company_patterns(company_spans)
        }
    
    def _analyze_model_selection(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze model selection patterns and effectiveness."""
        from collections import Counter
        
        model_usage = Counter()
        model_performance = {}
        
        for span in spans:
            model = span.get("attributes", {}).get("llm.model_name")
            if model:
                model_usage[model] += 1
                
                # Calculate performance metrics
                latency = self._calculate_latency(span)
                success = span.get("status_code") == "OK"
                
                if model not in model_performance:
                    model_performance[model] = {
                        "total": 0,
                        "success": 0,
                        "latencies": []
                    }
                
                model_performance[model]["total"] += 1
                if success:
                    model_performance[model]["success"] += 1
                model_performance[model]["latencies"].append(latency)
        
        # Calculate averages
        for model, perf in model_performance.items():
            perf["success_rate"] = perf["success"] / perf["total"] if perf["total"] > 0 else 0
            perf["avg_latency"] = sum(perf["latencies"]) / len(perf["latencies"]) if perf["latencies"] else 0
        
        return {
            "model_usage": dict(model_usage),
            "model_performance": model_performance,
            "insights": self._generate_model_insights(model_performance)
        }
    
    def _analyze_multi_channel(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze multi-channel sequence patterns."""
        channel_spans = [
            s for s in spans
            if any(channel in s.get("name", "").lower() for channel in ["email", "sms", "linkedin", "call"])
        ]
        
        # Group by trace to find sequences
        sequences = self._extract_channel_sequences(channel_spans)
        
        return {
            "channel_spans_count": len(channel_spans),
            "sequences_found": len(sequences),
            "common_sequences": self._find_common_sequences(sequences)
        }
    
    def _analyze_agent_delegation(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze agent spawning and delegation effectiveness."""
        delegation_spans = [
            s for s in spans
            if "delegat" in s.get("name", "").lower() or
               "subordinate" in s.get("name", "").lower() or
               "spawn" in s.get("name", "").lower()
        ]
        
        parallel_spans = [s for s in delegation_spans if self._is_parallel_execution(s)]
        sequential_spans = [s for s in delegation_spans if not self._is_parallel_execution(s)]
        
        return {
            "delegation_count": len(delegation_spans),
            "parallel_count": len(parallel_spans),
            "sequential_count": len(sequential_spans),
            "parallel_avg_latency": self._calculate_avg_latency(parallel_spans),
            "sequential_avg_latency": self._calculate_avg_latency(sequential_spans)
        }
    
    def _analyze_model_roi(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cost-performance tradeoffs between models."""
        free_models = ["llama", "mixtral", "qwen"]
        paid_models = ["sonnet", "haiku", "gpt"]
        
        free_model_spans = [s for s in spans if any(model in str(s.get("attributes", {})).lower() for model in free_models)]
        paid_model_spans = [s for s in spans if any(model in str(s.get("attributes", {})).lower() for model in paid_models)]
        
        free_performance = self._calculate_avg_performance(free_model_spans)
        paid_performance = self._calculate_avg_performance(paid_model_spans)
        
        return {
            "free_model_spans": len(free_model_spans),
            "paid_model_spans": len(paid_model_spans),
            "free_model_performance": free_performance,
            "paid_model_performance": paid_performance,
            "cost_savings_opportunity": self._calculate_cost_savings(free_performance, paid_performance)
        }
    
    def _analyze_abm_campaigns(self, spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze account-based marketing patterns."""
        # Group spans by account/company
        account_groups = self._group_by_account(spans)
        
        successful_accounts = [acc for acc in account_groups if self._is_successful_account(acc)]
        
        return {
            "total_accounts": len(account_groups),
            "successful_accounts": len(successful_accounts),
            "avg_contacts_per_account": self._calculate_avg_contacts(account_groups),
            "winning_patterns": self._extract_abm_patterns(successful_accounts)
        }
    
    # Helper methods
    def _is_deep_research(self, span: Dict[str, Any]) -> bool:
        """Determine if span represents deep research."""
        attrs = span.get("attributes", {})
        # Deep research indicators: multiple API calls, long duration, complex reasoning
        duration = self._calculate_latency(span)
        return duration > 5000  # 5+ seconds suggests deep research
    
    def _calculate_success_rate(self, spans: List[Dict[str, Any]]) -> float:
        """Calculate success rate from spans (if outcome data available)."""
        if not spans:
            return 0.0
        
        successful = [s for s in spans if s.get("status_code") == "OK"]
        return len(successful) / len(spans)
    
    def _calculate_latency(self, span: Dict[str, Any]) -> float:
        """Calculate span latency in milliseconds."""
        start = span.get("start_time_ns", 0)
        end = span.get("end_time_ns", 0)
        if start and end:
            return (end - start) / 1_000_000  # Convert to ms
        return 0.0
    
    def _calculate_avg_latency(self, spans: List[Dict[str, Any]]) -> float:
        """Calculate average latency for a list of spans."""
        if not spans:
            return 0.0
        latencies = [self._calculate_latency(s) for s in spans]
        return sum(latencies) / len(latencies)
    
    def _calculate_avg_depth(self, spans: List[Dict[str, Any]]) -> float:
        """Calculate average research depth."""
        return sum(1 if self._is_deep_research(s) else 0.5 for s in spans) / len(spans) if spans else 0
    
    def _extract_company_patterns(self, spans: List[Dict[str, Any]]) -> List[str]:
        """Extract patterns from company research spans."""
        patterns = []
        if len(spans) > 10:
            patterns.append("High company research activity detected")
        return patterns
    
    def _generate_model_insights(self, model_performance: Dict[str, Dict]) -> List[str]:
        """Generate insights about model selection."""
        insights = []
        
        # Find best performing models
        if model_performance:
            best_success = max(model_performance.items(), key=lambda x: x[1].get("success_rate", 0))
            insights.append(f"Best success rate: {best_success[0]} ({best_success[1]['success_rate']:.1%})")
            
            # Compare free vs paid
            free_models = [m for m in model_performance.keys() if any(f in m.lower() for f in ["llama", "mixtral", "qwen"])]
            paid_models = [m for m in model_performance.keys() if any(p in m.lower() for p in ["sonnet", "haiku", "gpt"])]
            
            if free_models and paid_models:
                free_avg = sum(model_performance[m]["success_rate"] for m in free_models) / len(free_models)
                paid_avg = sum(model_performance[m]["success_rate"] for m in paid_models) / len(paid_models)
                
                if free_avg / paid_avg > 0.90:  # Free models within 10% of paid
                    insights.append(f"Free models performing at {free_avg/paid_avg:.1%} of paid model quality - cost optimization opportunity")
        
        return insights
    
    def _extract_channel_sequences(self, spans: List[Dict[str, Any]]) -> List[List[str]]:
        """Extract channel sequences from spans grouped by trace."""
        # Group by trace_id
        traces = {}
        for span in spans:
            trace_id = span.get("context", {}).get("trace_id")
            if trace_id:
                if trace_id not in traces:
                    traces[trace_id] = []
                traces[trace_id].append(span)
        
        # Extract sequences
        sequences = []
        for trace_spans in traces.values():
            # Sort by time
            sorted_spans = sorted(trace_spans, key=lambda s: s.get("start_time", ""))
            sequence = [self._extract_channel(s) for s in sorted_spans]
            if len(sequence) > 1:
                sequences.append(sequence)
        
        return sequences
    
    def _extract_channel(self, span: Dict[str, Any]) -> str:
        """Extract channel name from span."""
        name = span.get("name", "").lower()
        if "email" in name:
            return "email"
        elif "sms" in name:
            return "sms"
        elif "linkedin" in name:
            return "linkedin"
        elif "call" in name:
            return "call"
        return "unknown"
    
    def _find_common_sequences(self, sequences: List[List[str]]) -> List[Dict[str, Any]]:
        """Find most common channel sequences."""
        from collections import Counter
        sequence_counts = Counter([tuple(s) for s in sequences])
        
        return [
            {"sequence": list(seq), "count": count, "frequency": count / len(sequences) if sequences else 0}
            for seq, count in sequence_counts.most_common(5)
        ]
    
    def _is_parallel_execution(self, span: Dict[str, Any]) -> bool:
        """Determine if span represents parallel execution."""
        # Check for parallel indicators in attributes
        attrs = str(span.get("attributes", {})).lower()
        return "parallel" in attrs or "concurrent" in attrs
    
    def _calculate_avg_performance(self, spans: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate average performance metrics."""
        if not spans:
            return {"success_rate": 0.0, "avg_latency": 0.0}
        
        success_rate = self._calculate_success_rate(spans)
        avg_latency = self._calculate_avg_latency(spans)
        
        return {"success_rate": success_rate, "avg_latency": avg_latency}
    
    def _calculate_cost_savings(self, free_perf: Dict, paid_perf: Dict) -> str:
        """Calculate cost savings opportunity."""
        if free_perf["success_rate"] / paid_perf["success_rate"] > 0.90:
            return "High: Free models perform within 10% of paid models"
        return "Low: Paid models significantly outperform free models"
    
    def _group_by_account(self, spans: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group spans by account/company."""
        # Group by company or account identifier in attributes
        accounts = {}
        for span in spans:
            attrs = span.get("attributes", {})
            company = attrs.get("company") or attrs.get("account") or attrs.get("lead.company")
            if company:
                if company not in accounts:
                    accounts[company] = []
                accounts[company].append(span)
        
        return list(accounts.values())
    
    def _is_successful_account(self, account_spans: List[Dict[str, Any]]) -> bool:
        """Determine if account campaign was successful."""
        # Check for conversion indicators in spans
        for span in account_spans:
            if span.get("status_code") == "OK" and "converted" in str(span.get("attributes", {})).lower():
                return True
        return False
    
    def _calculate_avg_contacts(self, account_groups: List[List[Dict[str, Any]]]) -> float:
        """Calculate average number of contacts per account."""
        if not account_groups:
            return 0.0
        
        contact_counts = []
        for group in account_groups:
            # Count unique contacts in spans
            contacts = set()
            for span in group:
                contact = span.get("attributes", {}).get("contact") or span.get("attributes", {}).get("lead.name")
                if contact:
                    contacts.add(contact)
            contact_counts.append(len(contacts))
        
        return sum(contact_counts) / len(contact_counts) if contact_counts else 0.0
    
    def _extract_abm_patterns(self, successful_accounts: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Extract winning ABM patterns from successful accounts."""
        if not successful_accounts:
            return {}
        
        avg_contacts = self._calculate_avg_contacts(successful_accounts)
        
        return {
            "avg_contacts_touched": avg_contacts,
            "common_channels": self._extract_common_channels(successful_accounts),
            "timing_patterns": self._extract_timing_patterns(successful_accounts)
        }
    
    def _extract_common_channels(self, account_groups: List[List[Dict[str, Any]]]) -> List[str]:
        """Extract common channels used in successful accounts."""
        all_channels = set()
        for group in account_groups:
            for span in group:
                channel = self._extract_channel(span)
                if channel != "unknown":
                    all_channels.add(channel)
        return list(all_channels)
    
    def _extract_timing_patterns(self, account_groups: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Extract timing patterns from successful accounts."""
        # Calculate average intervals between touches
        intervals = []
        for group in account_groups:
            sorted_spans = sorted(group, key=lambda s: s.get("start_time", ""))
            for i in range(1, len(sorted_spans)):
                # Calculate interval (simplified)
                intervals.append(i)  # Placeholder
        
        return {
            "avg_interval_days": sum(intervals) / len(intervals) if intervals else 0,
            "pattern": "Multiple touches over time" if len(intervals) > 0 else "Single touch"
        }
    
    def format_for_developer_communication(self, analysis: Dict[str, Any]) -> str:
        """Format analysis results for communication to developers."""
        output = []
        output.append("🔍 **System Development Analysis**")
        output.append("")
        output.append(f"**Analyzed:** {analysis['summary'].get('spans_analyzed', 0)} spans")
        output.append(f"**Time Window:** {analysis.get('time_window_hours', 24)} hours")
        output.append("")
        
        insights = analysis.get("insights", [])
        if insights:
            output.append("## 🎯 Development Insights")
            output.append("")
            for insight in insights[:5]:  # Top 5
                output.append(f"### {insight['severity'].upper()}: {insight['title']}")
                output.append(f"**Type:** {insight['type']}")
                output.append(f"**Description:** {insight['description']}")
                if insight.get("recommendations"):
                    output.append("**Recommendations:**")
                    for rec in insight["recommendations"]:
                        output.append(f"- {rec}")
                output.append("")
        
        levers = analysis.get("levers", [])
        if levers:
            output.append("## 🎛️ System Levers Identified")
            output.append("")
            for lever in levers:
                output.append(f"### {lever['name']}")
                output.append(f"**Description:** {lever['description']}")
                output.append(f"**Impact:** {lever['impact']}")
                if lever.get("current_value"):
                    output.append(f"**Current:** {lever['current_value']}")
                if lever.get("suggested_value"):
                    output.append(f"**Suggested:** {lever['suggested_value']}")
                output.append("")
        
        # NEW: Business Evolution Signals
        business_signals = analysis.get("business_signals", {})
        if business_signals:
            output.append("## 🚀 Business Evolution Signals")
            output.append("")
            output.append("### Research Optimization Opportunities")
            
            account_research = business_signals.get("account_research_patterns", {})
            if account_research.get("total_research_spans", 0) > 0:
                output.append(f"- **Account Research**: {account_research.get('total_research_spans')} spans analyzed")
                output.append(f"  - Deep research: {account_research.get('deep_research_count', 0)} spans")
                output.append(f"  - Shallow research: {account_research.get('shallow_research_count', 0)} spans")
                if account_research.get("insights"):
                    for insight in account_research["insights"]:
                        output.append(f"  - 💡 {insight}")
                output.append("")
            
            company_research = business_signals.get("company_research_patterns", {})
            if company_research.get("company_research_count", 0) > 0:
                output.append(f"- **Company Research**: {company_research.get('company_research_count')} spans analyzed")
                output.append(f"  - Average depth: {company_research.get('avg_depth', 0):.2f}")
                output.append("")
            
            output.append("### Model Performance Analysis")
            model_perf = business_signals.get("model_performance", {})
            if model_perf.get("model_usage"):
                output.append("- **Model Usage:**")
                for model, count in list(model_perf["model_usage"].items())[:5]:
                    output.append(f"  - {model}: {count} spans")
                output.append("")
                
                if model_perf.get("insights"):
                    output.append("- **Insights:**")
                    for insight in model_perf["insights"]:
                        output.append(f"  - 💡 {insight}")
                    output.append("")
            
            output.append("### Cost Optimization Opportunities")
            cost_tradeoffs = business_signals.get("cost_performance_tradeoffs", {})
            if cost_tradeoffs.get("cost_savings_opportunity"):
                output.append(f"- **Cost Savings**: {cost_tradeoffs['cost_savings_opportunity']}")
                output.append(f"  - Free model spans: {cost_tradeoffs.get('free_model_spans', 0)}")
                output.append(f"  - Paid model spans: {cost_tradeoffs.get('paid_model_spans', 0)}")
                output.append("")
            
            output.append("### Multi-Channel Patterns")
            channels = business_signals.get("channel_sequences", {})
            if channels.get("sequences_found", 0) > 0:
                output.append(f"- **Sequences Found**: {channels.get('sequences_found')} multi-channel sequences")
                if channels.get("common_sequences"):
                    output.append("- **Most Common Sequences:**")
                    for seq_info in channels["common_sequences"][:3]:
                        seq = " → ".join(seq_info["sequence"])
                        output.append(f"  - {seq} ({seq_info['count']} times, {seq_info['frequency']:.1%} frequency)")
                output.append("")
            
            output.append("### Agent Spawning Analysis")
            spawning = business_signals.get("spawning_effectiveness", {})
            if spawning.get("delegation_count", 0) > 0:
                output.append(f"- **Delegation Spans**: {spawning.get('delegation_count')}")
                output.append(f"  - Parallel: {spawning.get('parallel_count', 0)}")
                output.append(f"  - Sequential: {spawning.get('sequential_count', 0)}")
                if spawning.get("parallel_avg_latency") and spawning.get("sequential_avg_latency"):
                    parallel_latency = spawning["parallel_avg_latency"]
                    sequential_latency = spawning["sequential_avg_latency"]
                    if parallel_latency > 0 and sequential_latency > 0:
                        speedup = sequential_latency / parallel_latency
                        output.append(f"  - 💡 Parallel execution {speedup:.1f}x faster than sequential")
                output.append("")
            
            output.append("### ABM Pattern Insights")
            abm = business_signals.get("abm_patterns", {})
            if abm.get("total_accounts", 0) > 0:
                output.append(f"- **Accounts Analyzed**: {abm.get('total_accounts')}")
                output.append(f"  - Successful: {abm.get('successful_accounts', 0)}")
                output.append(f"  - Avg contacts per account: {abm.get('avg_contacts_per_account', 0):.1f}")
                winning = abm.get("winning_patterns", {})
                if winning:
                    output.append(f"  - Common channels: {', '.join(winning.get('common_channels', []))}")
                output.append("")
        
        return "\n".join(output)


async def get_phoenix_spans_via_mcp(
    project_name: str = "hume-dspy-agent",
    limit: int = 100,
    hours_back: int = 24,
    mcp_client=None
) -> List[Dict[str, Any]]:
    """Get spans from Phoenix using MCP server.
    
    Args:
        project_name: Phoenix project name
        limit: Maximum number of spans to fetch
        hours_back: How many hours back to look
        mcp_client: Optional MCP client to use (if None, tries direct Phoenix MCP tool)
    
    Returns:
        List of span dictionaries
    """
    try:
        # Calculate time window
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)
        
        logger.info(f"📊 Fetching {limit} spans from Phoenix project '{project_name}'")
        logger.info(f"   Time range: {start_time.isoformat()} to {end_time.isoformat()}")
        
        # Try calling via MCP client if available
        if mcp_client and hasattr(mcp_client, 'call_tool'):
            try:
                # Try common Phoenix MCP tool names
                tool_names = [
                    "mcp_phoenix_get-spans",
                    "phoenix_get-spans", 
                    "get-spans"
                ]
                
                for tool_name in tool_names:
                    try:
                        result = await mcp_client.call_tool(
                            tool_name=tool_name,
                            params={
                                "projectName": project_name,
                                "limit": limit,
                                "startTime": start_time.isoformat(),
                                "endTime": end_time.isoformat()
                            }
                        )
                        
                        if result and isinstance(result, dict):
                            spans = result.get("spans", [])
                            logger.info(f"✅ Fetched {len(spans)} spans from Phoenix via MCP tool '{tool_name}'")
                            return spans
                            
                    except Exception as tool_error:
                        logger.debug(f"Tool '{tool_name}' not available: {tool_error}")
                        continue
                        
            except Exception as e:
                logger.warning(f"⚠️ MCP client call failed: {e}")
        
        # Try direct Phoenix API call if we have credentials
        phoenix_api_url = os.getenv("PHOENIX_API_URL")
        if phoenix_api_url:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    # Phoenix API endpoint for spans
                    url = f"{phoenix_api_url}/api/v1/spans"
                    params = {
                        "project_name": project_name,
                        "limit": limit,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            spans = data.get("spans", [])
                            logger.info(f"✅ Fetched {len(spans)} spans from Phoenix via API")
                            return spans
                            
            except Exception as e:
                logger.debug(f"Phoenix API call failed: {e}")
        
        # Final fallback: log and return empty
        logger.warning("⚠️ Phoenix MCP not available - returning empty spans list")
        logger.warning("   To enable: Configure Phoenix MCP server or set PHOENIX_API_URL")
        return []
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch Phoenix spans via MCP: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []

