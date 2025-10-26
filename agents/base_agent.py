"""
SelfOptimizingAgent Base Class

Universal base class for ALL agents with Continue.dev-inspired patterns.

Provides:
- Rule-based customization (department-specific rules)
- Model selection (cost vs performance)
- GEPA access (with permission)
- Sequential thought access (with permission)
- Performance tracking
- Autonomous optimization
- MCP tool exposure
"""

import dspy
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===== AGENT RULES (Continue.dev-inspired) =====

class AgentRules(BaseModel):
    """Rule-based configuration for agent behavior.
    
    Inspired by Continue.dev rules system.
    """
    # Model selection
    allowed_models: List[str] = Field(..., description="Models agent can use")
    default_model: str = Field(..., description="Default model")
    
    # Tool access
    allowed_tools: List[str] = Field(default_factory=list, description="Tools agent can use")
    requires_approval: bool = Field(default=True, description="Require approval for expensive tools?")
    max_cost_per_request: float = Field(default=0.10, description="Max cost per request ($)")
    
    # Optimization
    optimizer: str = Field(default="bootstrap", description="gepa or bootstrap")
    auto_optimize_threshold: float = Field(default=0.70, description="Optimize if success <70%")
    
    # Department
    department: Optional[str] = Field(default=None, description="CS, Marketing, Legal, etc.")


# ===== PERFORMANCE TRACKING =====

class PerformanceRecord(BaseModel):
    """Single performance record."""
    task: str
    success: bool
    user_satisfaction: float = Field(ge=0.0, le=5.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PerformanceTracker:
    """Track agent performance over time."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.history: List[PerformanceRecord] = []
        self.max_history = 100
    
    def record(self, task: str, success: bool, user_satisfaction: float = 3.5):
        """Record task performance."""
        self.history.append(PerformanceRecord(
            task=task,
            success=success,
            user_satisfaction=user_satisfaction
        ))
        
        # Trim history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def should_optimize(self, threshold: float = 0.70) -> bool:
        """Determine if optimization needed.
        
        Triggers when:
        - Success rate <threshold over last 20 tasks
        - User satisfaction <3.5/5 average
        - 3+ consecutive failures
        """
        recent = self.history[-20:]  # Last 20 tasks
        
        if len(recent) < 10:
            return False  # Need more data
        
        success_rate = sum(r.success for r in recent) / len(recent)
        avg_satisfaction = sum(r.user_satisfaction for r in recent) / len(recent)
        
        # Check triggers
        if success_rate < threshold:
            return True
        if avg_satisfaction < 3.5:
            return True
        if self._consecutive_failures() >= 3:
            return True
        
        return False
    
    def _consecutive_failures(self) -> int:
        """Count consecutive failures."""
        count = 0
        for record in reversed(self.history):
            if not record.success:
                count += 1
            else:
                break
        return count


# ===== MODEL SELECTION =====

class SmartModelSelector:
    """Intelligent model selection based on task and rules.
    
    Continue.dev pattern: Context-aware model selection.
    """
    
    MODELS = {
        # Paid models (customer-facing)
        "strategic": "openrouter/anthropic/claude-sonnet-4.5",
        "fast": "openrouter/anthropic/claude-haiku-4.5",
        
        # Free models (autonomous, GEPA-optimized)
        "free_strategic": "groq/llama-3.1-70b-versatile",
        "free_execution": "groq/mixtral-8x7b-32768",
        "free_alternative": "openrouter/qwen/qwen-2.5-72b-instruct"
    }
    
    def __init__(self, rules: AgentRules):
        self.rules = rules
    
    def select(
        self,
        complexity: str,  # "simple", "medium", "complex"
        customer_facing: bool,
        cost_limit: Optional[float] = None
    ) -> str:
        """Select optimal model based on context."""
        cost_limit = cost_limit or self.rules.max_cost_per_request
        
        # Customer-facing = Always use paid model (if allowed)
        if customer_facing and cost_limit >= 0.50:
            if complexity == "complex":
                return self.MODELS["strategic"]  # Claude Sonnet
            else:
                return self.MODELS["fast"]  # Claude Haiku
        
        # Autonomous = Free models (GEPA-optimized)
        if complexity == "complex":
            return self.MODELS["free_strategic"]  # Llama 3.1 70B
        else:
            return self.MODELS["free_execution"]  # Mixtral 8x7B


# ===== PERMISSION MANAGEMENT =====

class PermissionManager:
    """Manage permission requests for expensive tools.

    Continue.dev pattern: Rule-based tool access with approval.
    Includes Slack integration and timeout fallback.
    """

    def __init__(self, agent_name: str, rules: AgentRules):
        self.agent_name = agent_name
        self.rules = rules
        self.pending_requests: Dict[str, Any] = {}

    async def request_permission(
        self,
        tool_name: str,  # "gepa", "sequential_thought"
        task: str,
        estimated_cost: float
    ) -> bool:
        """Request permission to use expensive tool.

        Sends Slack notification and waits for approval with timeout.
        Returns False if timeout or denied.
        """
        # Check if approval required
        if not self.rules.requires_approval:
            logger.info(f"{self.agent_name}: Auto-approved {tool_name} (${estimated_cost})")
            return True  # Auto-approve

        # Check cost limit
        if estimated_cost > self.rules.max_cost_per_request:
            logger.warning(f"{self.agent_name}: Cost ${estimated_cost} exceeds limit ${self.rules.max_cost_per_request}")
            return False

        # Send Slack notification
        try:
            from integrations.slack_client import SlackClient
            slack = SlackClient()

            message = f"""🤖 **{self.agent_name} Permission Request**

**Tool**: {tool_name.upper()}
**Task**: {task}
**Cost**: ${estimated_cost:.2f}

**Approve?**
✅ Reply "approve {self.agent_name.lower()}" to approve
❌ Reply "deny" to deny
⏱️ Auto-deny in 5 minutes if no response
"""

            await slack.send_message(
                channel="#agent-permissions",
                text=message
            )

            # Wait for approval with timeout
            timeout = 300  # 5 minutes for sequential thought, 3600 for GEPA
            if tool_name == "gepa":
                timeout = 3600  # 1 hour for GEPA

            try:
                approved = await asyncio.wait_for(
                    self._wait_for_approval(self.agent_name, tool_name),
                    timeout=timeout
                )
                return approved
            except asyncio.TimeoutError:
                logger.warning(f"{self.agent_name}: Permission timeout for {tool_name}, using free model fallback")
                return False  # Timeout = deny, use free model

        except Exception as e:
            logger.error(f"{self.agent_name}: Permission request failed: {e}")
            return False  # Error = deny, use free model

    async def _wait_for_approval(self, agent_name: str, tool_name: str) -> bool:
        """Wait for user approval via Slack.

        Monitors Slack for approval message.
        Returns True if approved, False if denied.
        """
        try:
            from integrations.slack_client import SlackClient
            slack = SlackClient()

            # Poll for approval message
            # Check every 5 seconds for approval
            for _ in range(60):  # 5 minutes max (60 * 5 seconds)
                # Check for approval message in #agent-permissions channel
                messages = await slack.get_recent_messages(
                    channel="#agent-permissions",
                    limit=10
                )

                for msg in messages:
                    text = msg.get('text', '').lower()

                    # Check for approval
                    if f"approve {agent_name.lower()}" in text:
                        logger.info(f"✅ {agent_name}: Permission approved for {tool_name}")
                        return True

                    # Check for denial
                    if "deny" in text and agent_name.lower() in text:
                        logger.info(f"❌ {agent_name}: Permission denied for {tool_name}")
                        return False

                # Wait 5 seconds before checking again
                await asyncio.sleep(5)

            # Timeout after 5 minutes
            logger.warning(f"⏱️ {agent_name}: Approval timeout for {tool_name}")
            return False

        except Exception as e:
            logger.error(f"❌ {agent_name}: Approval monitoring failed: {e}")
            return False  # Error = deny

# ===== SELF-OPTIMIZING AGENT BASE CLASS =====

class SelfOptimizingAgent(dspy.Module):
    """Base class for ALL agents with Continue.dev-inspired patterns.
    
    Provides:
    - Rule-based customization
    - Model selection (cost vs performance)
    - GEPA access (with permission)
    - Sequential thought access (with permission)
    - Performance tracking
    - Autonomous optimization
    - MCP tool exposure
    """
    
    def __init__(self, agent_name: str, rules: AgentRules):
        super().__init__()
        self.agent_name = agent_name
        self.rules = rules
        
        # Model selection
        self.model_selector = SmartModelSelector(rules)
        
        # Performance tracking
        self.performance_tracker = PerformanceTracker(agent_name)
        
        # Permission system
        self.permission_manager = PermissionManager(agent_name, rules)
        
        logger.info(f"✅ {agent_name} initialized with {rules.optimizer} optimizer")
    
    async def execute_with_monitoring(
        self,
        task: str,
        complexity: str = "medium",
        customer_facing: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute task with performance monitoring."""
        # Select model
        model = self.model_selector.select(complexity, customer_facing)
        dspy.configure(lm=dspy.LM(model))
        
        # Execute task
        result = await self.forward_async(task, **kwargs)
        
        # Track performance
        self.performance_tracker.record(
            task=task,
            success=result.get('success', False),
            user_satisfaction=result.get('satisfaction', 3.5)
        )
        
        # Check if optimization needed
        if self.performance_tracker.should_optimize(self.rules.auto_optimize_threshold):
            await self._request_optimization()
        
        return result
    
    async def request_tool_access(
        self,
        tool_name: str,  # "gepa", "sequential_thought"
        task: str,
        estimated_cost: float
    ) -> bool:
        """Request permission to use expensive tool."""
        return await self.permission_manager.request_permission(
            tool_name=tool_name,
            task=task,
            estimated_cost=estimated_cost
        )
    
    async def _request_optimization(self):
        """Request permission to run optimization."""
        optimizer_cost = 30.0 if self.rules.optimizer == "gepa" else 5.0
        
        approved = await self.request_tool_access(
            tool_name=self.rules.optimizer,
            task=f"Optimize {self.agent_name} (performance degraded)",
            estimated_cost=optimizer_cost
        )
        
        if approved:
            await self._run_optimization()
    
    async def _run_optimization(self):
        """Run optimization (GEPA or BootstrapFewShot).

        Actually executes optimization, not placeholder.
        """
        logger.info(f"🔧 Running {self.rules.optimizer} optimization for {self.agent_name}")

        try:
            if self.rules.optimizer == "gepa":
                # Import GEPA optimizer
                from optimization.gepa_optimizer import GEPAOptimizer
                import dspy

                optimizer = GEPAOptimizer(
                    max_metric_calls=500,
                    reflection_model="openrouter/anthropic/claude-sonnet-4.5"
                )

                # Create simple trainset from recent performance history
                trainset = self._create_trainset_from_history()

                if len(trainset) < 10:
                    logger.warning(f"⚠️ Not enough training data ({len(trainset)} examples), need 10+")
                    logger.info("Skipping optimization until more data available")
                    return

                # Define metric function
                def metric(example, prediction, trace=None):
                    # Simple success metric
                    if hasattr(prediction, 'success'):
                        return 1.0 if prediction.success else 0.0
                    return 0.5  # Unknown

                # Run GEPA optimization
                logger.info(f"🔧 Running GEPA optimization with {len(trainset)} examples...")
                result = await optimizer.optimize(
                    agent=self,
                    trainset=trainset,
                    metric=metric,
                    agent_name=self.agent_name
                )

                logger.info(f"✅ GEPA optimization complete!")
                logger.info(f"  - Baseline: {result.baseline_score:.2%}")
                logger.info(f"  - Optimized: {result.optimized_score:.2%}")
                logger.info(f"  - Improvement: +{result.improvement:.2%}")
                logger.info(f"  - Cost: ${result.optimization_cost:.2f}")
                logger.info(f"  - Saved to: {result.saved_to}")

            elif self.rules.optimizer == "bootstrap":
                # Import BootstrapFewShot
                import dspy
                from dspy.teleprompt import BootstrapFewShot

                # Create trainset
                trainset = self._create_trainset_from_history()

                if len(trainset) < 5:
                    logger.warning(f"⚠️ Not enough training data ({len(trainset)} examples), need 5+")
                    logger.info("Skipping optimization until more data available")
                    return

                # Define metric
                def metric(example, prediction, trace=None):
                    if hasattr(prediction, 'success'):
                        return 1.0 if prediction.success else 0.0
                    return 0.5

                # Run BootstrapFewShot
                logger.info(f"🔧 Running BootstrapFewShot with {len(trainset)} examples...")
                optimizer = BootstrapFewShot(metric=metric, max_bootstrapped_demos=4)
                optimized = optimizer.compile(student=self, trainset=trainset)

                # Save optimized agent
                save_path = f"optimized_{self.agent_name.lower()}_bootstrap.json"
                optimized.save(save_path)

                logger.info(f"✅ BootstrapFewShot optimization complete!")
                logger.info(f"  - Saved to: {save_path}")

            else:
                logger.warning(f"⚠️ Unknown optimizer: {self.rules.optimizer}")

        except Exception as e:
            logger.error(f"❌ Optimization failed for {self.agent_name}: {e}")
            import traceback
            traceback.print_exc()

    def _create_trainset_from_history(self) -> List:
        """Create training dataset from performance history.

        Converts recent performance records into DSPy examples.
        """
        import dspy

        trainset = []

        # Use recent successful tasks as training examples
        for record in self.performance_tracker.history:
            if record.success and record.user_satisfaction >= 3.5:
                # Create DSPy example from successful task
                example = dspy.Example(
                    task=record.task,
                    success=True
                ).with_inputs("task")

                trainset.append(example)

        return trainset
    async def forward_async(self, task: str, **kwargs) -> Dict[str, Any]:
        """Override in subclass."""
        raise NotImplementedError("Subclass must implement forward_async()")
