"""Proactive Monitoring & Self-Healing System (Phase 0.6)

This system continuously monitors production logs, detects anomalies,
generates fixes using DSPy, and proposes them to Josh via Slack for approval.

Pattern:
1. Monitor logs continuously (Railway + Phoenix)
2. Detect anomalies (errors, performance issues, patterns)
3. Analyze root cause (DSPy-powered)
4. Generate fix (DSPy-powered code generation)
5. Post to Slack for approval
6. Apply fix when approved

Phase 0.6 - October 20, 2025
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import dspy
import httpx

logger = logging.getLogger(__name__)


# ===== Data Structures =====

@dataclass
class LogAnomaly:
    """Detected anomaly in logs."""
    timestamp: datetime
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    category: str  # "error", "performance", "pattern"
    description: str
    log_lines: List[str]
    frequency: int
    context: Dict[str, Any]


@dataclass
class ProposedFix:
    """A fix proposed by the system."""
    anomaly: LogAnomaly
    fix_id: str
    analysis: str
    proposed_changes: List[Dict[str, str]]  # [{"file": "...", "change": "..."}]
    reasoning: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    estimated_impact: str


# ===== DSPy Signatures =====

class AnalyzeAnomaly(dspy.Signature):
    """Analyze a detected log anomaly to understand root cause."""
    
    anomaly_description = dspy.InputField(
        desc="Description of the anomaly detected in logs"
    )
    log_samples = dspy.InputField(
        desc="Sample log lines showing the anomaly"
    )
    system_context = dspy.InputField(
        desc="Current system architecture and recent changes"
    )
    
    root_cause = dspy.OutputField(
        desc="Root cause analysis - what's actually causing this issue"
    )
    severity_assessment = dspy.OutputField(
        desc="Severity: CRITICAL, HIGH, MEDIUM, or LOW with justification"
    )
    affected_components = dspy.OutputField(
        desc="Which system components are affected"
    )


class GenerateFix(dspy.Signature):
    """Generate a code fix for a detected issue."""
    
    root_cause = dspy.InputField(
        desc="The identified root cause of the issue"
    )
    affected_components = dspy.InputField(
        desc="System components that need changes"
    )
    current_code = dspy.InputField(
        desc="Relevant current code that needs fixing"
    )
    
    proposed_fix = dspy.OutputField(
        desc="The exact code changes needed (be specific about file and line changes)"
    )
    reasoning = dspy.OutputField(
        desc="Why this fix addresses the root cause"
    )
    risk_assessment = dspy.OutputField(
        desc="Risk level (LOW/MEDIUM/HIGH) and potential side effects"
    )


# ===== Log Analyzer =====

class LogAnalyzer:
    """Analyzes logs to detect anomalies and patterns."""
    
    def __init__(self):
        """Initialize log analyzer."""
        self.error_counts = defaultdict(int)
        self.error_last_seen = {}
        self.performance_metrics = []
        
    def analyze_logs(self, log_lines: List[str]) -> List[LogAnomaly]:
        """Analyze log lines and detect anomalies.
        
        Args:
            log_lines: Recent log lines to analyze
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Detect error patterns
        anomalies.extend(self._detect_error_patterns(log_lines))
        
        # Detect performance issues
        anomalies.extend(self._detect_performance_issues(log_lines))
        
        # Detect unusual patterns
        anomalies.extend(self._detect_unusual_patterns(log_lines))
        
        return anomalies
    
    def _detect_error_patterns(self, log_lines: List[str]) -> List[LogAnomaly]:
        """Detect error patterns in logs."""
        anomalies = []
        error_patterns = defaultdict(list)
        
        # Group errors by pattern
        for line in log_lines:
            if "ERROR" in line or "❌" in line or "CRITICAL" in line:
                # Extract error pattern (remove timestamps, IDs, etc.)
                pattern = self._extract_error_pattern(line)
                error_patterns[pattern].append(line)
        
        # Check for repeated errors
        for pattern, lines in error_patterns.items():
            if len(lines) >= 3:  # 3+ occurrences = anomaly
                anomalies.append(LogAnomaly(
                    timestamp=datetime.utcnow(),
                    severity="HIGH" if len(lines) >= 5 else "MEDIUM",
                    category="error",
                    description=f"Repeated error pattern detected ({len(lines)} occurrences)",
                    log_lines=lines[:5],  # First 5 samples
                    frequency=len(lines),
                    context={"pattern": pattern}
                ))
        
        return anomalies
    
    def _detect_performance_issues(self, log_lines: List[str]) -> List[LogAnomaly]:
        """Detect performance degradation."""
        anomalies = []
        
        # Look for truncation warnings (sign of inefficiency)
        truncations = [line for line in log_lines if "truncated" in line.lower()]
        if len(truncations) >= 2:
            anomalies.append(LogAnomaly(
                timestamp=datetime.utcnow(),
                severity="MEDIUM",
                category="performance",
                description=f"Token truncation warnings ({len(truncations)} occurrences)",
                log_lines=truncations[:3],
                frequency=len(truncations),
                context={"type": "token_truncation"}
            ))
        
        # Look for slow operations (>10s)
        # TODO: Parse timing from logs
        
        return anomalies
    
    def _detect_unusual_patterns(self, log_lines: List[str]) -> List[LogAnomaly]:
        """Detect unusual patterns that might indicate issues."""
        anomalies = []
        
        # Check for unusually high duplicate detection
        duplicates = [line for line in log_lines if "Duplicate Slack event" in line]
        if len(duplicates) >= 10:  # More than 10 duplicates = potential issue
            anomalies.append(LogAnomaly(
                timestamp=datetime.utcnow(),
                severity="LOW",
                category="pattern",
                description=f"Unusually high duplicate event rate ({len(duplicates)} in logs)",
                log_lines=duplicates[:5],
                frequency=len(duplicates),
                context={"type": "duplicate_spike"}
            ))
        
        return anomalies
    
    def _extract_error_pattern(self, log_line: str) -> str:
        """Extract error pattern by removing variable parts."""
        # Remove timestamps
        pattern = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', '', log_line)
        # Remove event IDs
        pattern = re.sub(r'\d{10,}\.\d+_[A-Z0-9_]+', '[EVENT_ID]', pattern)
        # Remove UUIDs
        pattern = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '[UUID]', pattern)
        # Remove numbers
        pattern = re.sub(r'\b\d+\b', '[NUM]', pattern)
        
        return pattern.strip()


# ===== Proactive Monitor =====

class ProactiveMonitor:
    """Main proactive monitoring system."""
    
    def __init__(self, slack_bot_token: Optional[str] = None):
        """Initialize proactive monitor.
        
        Args:
            slack_bot_token: Slack bot token for posting alerts
        """
        self.slack_bot_token = slack_bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.log_analyzer = LogAnalyzer()
        self.active_anomalies: Dict[str, LogAnomaly] = {}
        self.proposed_fixes: Dict[str, ProposedFix] = {}
        
        # DSPy modules
        self.anomaly_analyzer = dspy.ChainOfThought(AnalyzeAnomaly)
        self.fix_generator = dspy.ChainOfThought(GenerateFix)
        
        logger.info("✅ Proactive Monitor initialized")
        logger.info("   Continuous log analysis enabled")
        logger.info("   Auto-fix generation with approval workflow")
    
    async def fetch_recent_logs(self, lines: int = 100) -> List[str]:
        """Fetch recent logs from Railway.
        
        Args:
            lines: Number of log lines to fetch
        
        Returns:
            List of log lines
        """
        try:
            # Use railway CLI to fetch logs
            import subprocess
            result = subprocess.run(
                ["railway", "logs", "--lines", str(lines)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.split('\n')
            else:
                logger.error(f"Failed to fetch logs: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return []
    
    async def analyze_and_detect(self) -> List[LogAnomaly]:
        """Fetch logs and detect anomalies.
        
        Returns:
            List of new anomalies detected
        """
        logger.debug("🔍 Fetching recent logs...")
        log_lines = await self.fetch_recent_logs(lines=200)
        
        if not log_lines:
            logger.warning("No logs fetched")
            return []
        
        logger.debug(f"📊 Analyzing {len(log_lines)} log lines...")
        anomalies = self.log_analyzer.analyze_logs(log_lines)
        
        # Filter out anomalies we've already seen recently
        new_anomalies = []
        for anomaly in anomalies:
            anomaly_key = f"{anomaly.category}:{anomaly.context.get('pattern', '')[:50]}"
            
            # Check if we've seen this recently
            if anomaly_key in self.active_anomalies:
                last_seen = self.active_anomalies[anomaly_key]
                if (anomaly.timestamp - last_seen.timestamp).seconds < 3600:  # 1 hour
                    continue  # Skip, already active
            
            self.active_anomalies[anomaly_key] = anomaly
            new_anomalies.append(anomaly)
        
        if new_anomalies:
            logger.info(f"🚨 Detected {len(new_anomalies)} new anomalies")
        
        return new_anomalies
    
    async def analyze_root_cause(self, anomaly: LogAnomaly) -> Tuple[str, str, str]:
        """Analyze root cause of anomaly using DSPy.
        
        Args:
            anomaly: The detected anomaly
        
        Returns:
            Tuple of (root_cause, severity, affected_components)
        """
        logger.info(f"🔬 Analyzing root cause for {anomaly.category} anomaly...")
        
        # Build system context
        system_context = """
        Current System Architecture:
        - DSPy agents (Strategy, Audit, Research, Follow-up)
        - MCP Orchestrator (Phase 0.7) for dynamic tool loading
        - Slack integration with message chunking
        - Phoenix observability
        - Railway deployment
        
        Recent Changes:
        - Phase 0.7: Added MCP Orchestrator
        - Increased max_tokens to 5000
        - Improved error logging
        - Added MCP retry logic
        """
        
        try:
            result = self.anomaly_analyzer(
                anomaly_description=anomaly.description,
                log_samples="\n".join(anomaly.log_lines),
                system_context=system_context
            )
            
            return (
                result.root_cause,
                result.severity_assessment,
                result.affected_components
            )
        except Exception as e:
            logger.error(f"Failed to analyze root cause: {e}")
            return (
                f"Analysis failed: {e}",
                anomaly.severity,
                "Unknown"
            )
    
    async def generate_fix(
        self,
        anomaly: LogAnomaly,
        root_cause: str,
        affected_components: str
    ) -> Optional[ProposedFix]:
        """Generate a fix for the detected issue.
        
        Args:
            anomaly: The detected anomaly
            root_cause: Identified root cause
            affected_components: Components that need fixing
        
        Returns:
            Proposed fix or None if unable to generate
        """
        logger.info("🔧 Generating fix proposal...")
        
        # TODO: Fetch relevant code for context
        current_code = "# Relevant code will be fetched based on affected_components"
        
        try:
            result = self.fix_generator(
                root_cause=root_cause,
                affected_components=affected_components,
                current_code=current_code
            )
            
            fix_id = f"fix_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            proposed_fix = ProposedFix(
                anomaly=anomaly,
                fix_id=fix_id,
                analysis=root_cause,
                proposed_changes=[{
                    "description": result.proposed_fix,
                    "risk": result.risk_assessment
                }],
                reasoning=result.reasoning,
                risk_level=result.risk_assessment.split()[0] if result.risk_assessment else "MEDIUM",
                estimated_impact="TBD - requires manual review"
            )
            
            self.proposed_fixes[fix_id] = proposed_fix
            return proposed_fix
            
        except Exception as e:
            logger.error(f"Failed to generate fix: {e}")
            return None
    
    async def post_to_slack(self, proposed_fix: ProposedFix) -> bool:
        """Post proposed fix to Slack for approval.
        
        Args:
            proposed_fix: The fix to propose
        
        Returns:
            True if posted successfully
        """
        if not self.slack_bot_token:
            logger.warning("⚠️ Slack token not configured, cannot post fix proposal")
            return False
        
        # Format message
        message = f"""🔧 **Proactive Fix Proposal** - {proposed_fix.fix_id}

**Issue Detected**:
{proposed_fix.anomaly.description}
Frequency: {proposed_fix.anomaly.frequency} occurrences
Severity: {proposed_fix.anomaly.severity}

**Root Cause Analysis**:
{proposed_fix.analysis}

**Proposed Fix**:
{proposed_fix.proposed_changes[0]['description']}

**Reasoning**:
{proposed_fix.reasoning}

**Risk Assessment**: {proposed_fix.risk_level}
{proposed_fix.proposed_changes[0]['risk']}

**To approve this fix**, reply with: `@Agent implement {proposed_fix.fix_id}`
**To reject**, reply with: `@Agent reject {proposed_fix.fix_id}`

_This is an automatically generated fix proposal from Phase 0.6 Proactive Monitoring_
"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {self.slack_bot_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": "#alerts",  # Or configured channel
                        "text": message,
                        "unfurl_links": False
                    },
                    timeout=10.0
                )
                
                data = response.json()
                if data.get("ok"):
                    logger.info(f"✅ Posted fix proposal to Slack: {proposed_fix.fix_id}")
                    return True
                else:
                    logger.error(f"Failed to post to Slack: {data.get('error')}")
                    return False
        except Exception as e:
            logger.error(f"Error posting to Slack: {e}")
            return False
    
    async def monitoring_loop(self, interval_seconds: int = 300):
        """Main monitoring loop - runs continuously.
        
        Args:
            interval_seconds: How often to check logs (default: 5 minutes)
        """
        logger.info(f"🔄 Starting monitoring loop (checking every {interval_seconds}s)")
        
        while True:
            try:
                # Detect anomalies
                anomalies = await self.analyze_and_detect()
                
                # Process each new anomaly
                for anomaly in anomalies:
                    logger.info(f"🚨 Processing {anomaly.severity} anomaly: {anomaly.description}")
                    
                    # Only auto-generate fixes for MEDIUM+ severity
                    if anomaly.severity in ["MEDIUM", "HIGH", "CRITICAL"]:
                        # Analyze root cause
                        root_cause, severity, components = await self.analyze_root_cause(anomaly)
                        
                        # Generate fix
                        fix = await self.generate_fix(anomaly, root_cause, components)
                        
                        if fix:
                            # Post to Slack for approval
                            await self.post_to_slack(fix)
                    else:
                        logger.info(f"Skipping auto-fix for LOW severity anomaly")
                
                # Wait before next check
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error


# ===== Convenience Functions =====

_monitor_instance: Optional[ProactiveMonitor] = None

def get_proactive_monitor() -> ProactiveMonitor:
    """Get or create the global proactive monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = ProactiveMonitor()
    return _monitor_instance


async def start_monitoring(interval_seconds: int = 300):
    """Start the proactive monitoring system.
    
    Args:
        interval_seconds: Check interval (default: 5 minutes)
    """
    monitor = get_proactive_monitor()
    await monitor.monitoring_loop(interval_seconds)
