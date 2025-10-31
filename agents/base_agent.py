"""SelfOptimizingAgent Base Class

Universal base class for ALL agents with Continue.dev-inspired patterns.

Provides:
- Rule-based customization (department-specific rules)
- Model selection (cost vs performance)
- GEPA access (with permission)
- Sequential thought access (with permission)
- Performance tracking
- Autonomous optimization
- MCP tool exposure
- Extension system (Agent Zero pattern)
- Error recovery (RepairableException pattern)
"""

import dspy
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from uuid import uuid4

logger = logging.getLogger(__name__)

# ===== EXTENSION SYSTEM (Agent Zero Pattern) =====

class AgentExtension(ABC):
    """Base class for agent extensions.

    Extensions can hook into agent lifecycle:
    - before_execute: Before task execution
    - after_execute: After task execution
    - on_error: When error occurs
    - on_optimize: When optimization triggered
    """

    def __init__(self, name: str):
        self.name = name

    async def before_execute(self, task: str, **kwargs) -> Dict[str, Any]:
        """Called before task execution.

        Can modify task parameters or add context.
        Returns dict of modifications to apply.
        """
        return {}

    async def after_execute(self, task: str, result: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Called after task execution.

        Can modify result or trigger follow-up actions.
        Returns dict of modifications to apply.
        """
        return {}

    async def on_error(self, task: str, error: Exception, **kwargs) -> Optional[Dict[str, Any]]:
        """Called when error occurs.

        Can attempt error recovery or provide fallback.
        Returns recovery result or None if can't recover.
        """
        return None

    async def on_optimize(self, agent_name: str, performance_data: Dict[str, Any]) -> None:
        """Called when optimization triggered.

        Can customize optimization behavior.
        """
        pass

class RepairableException(Exception):
    """Exception that can potentially be repaired by LLM.

    Agent Zero pattern: Errors that DSPy can analyze and fix.
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}
        self.repair_attempts = 0
        self.max_repair_attempts = 3

    def can_repair(self) -> bool:
        """Check if repair should be attempted."""
        return self.repair_attempts < self.max_repair_attempts

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
        """Determine if optimization needed."""
        recent = self.history[-20:]

        if len(recent) < 10:
            return False

        success_rate = sum(r.success for r in recent) / len(recent)
        avg_satisfaction = sum(r.user_satisfaction for r in recent) / len(recent)

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
    """Intelligent model selection based on task and rules."""

    MODELS = {
        "strategic": "openrouter/anthropic/claude-sonnet-4.5",
        "fast": "openrouter/anthropic/claude-haiku-4.5",
        "free_strategic": "groq/llama-3.1-70b-versatile",
        "free_execution": "groq/mixtral-8x7b-32768",
        "free_alternative": "openrouter/qwen/qwen-2.5-72b-instruct"
    }

    def __init__(self, rules: AgentRules):
        self.rules = rules

    def select(
        self,
        complexity: str,
        customer_facing: bool,
        cost_limit: Optional[float] = None
    ) -> str:
        """Select optimal model based on context."""
        cost_limit = cost_limit or self.rules.max_cost_per_request

        if customer_facing and cost_limit >= 0.50:
            if complexity == "complex":
                return self.MODELS["strategic"]
            else:
                return self.MODELS["fast"]

        if complexity == "complex":
            return self.MODELS["free_strategic"]
        else:
            return self.MODELS["free_execution"]

# ===== PERMISSION MANAGEMENT =====

class PermissionManager:
    """Manage permission requests for expensive tools."""

    def __init__(self, agent_name: str, rules: AgentRules):
        self.agent_name = agent_name
        self.rules = rules
        self.pending_requests: Dict[str, Any] = {}

    async def request_permission(
        self,
        tool_name: str,
        task: str,
        estimated_cost: float
    ) -> bool:
        """Request permission to use expensive tool."""
        if not self.rules.requires_approval:
            logger.info(f"{self.agent_name}: Auto-approved {tool_name} (${estimated_cost})")
            return True

        if estimated_cost > self.rules.max_cost_per_request:
            logger.warning(f"{self.agent_name}: Cost ${estimated_cost} exceeds limit ${self.rules.max_cost_per_request}")
            return False

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

            timeout = 300 if tool_name != "gepa" else 3600

            try:
                approved = await asyncio.wait_for(
                    self._wait_for_approval(self.agent_name, tool_name),
                    timeout=timeout
                )
                return approved
            except asyncio.TimeoutError:
                logger.warning(f"{self.agent_name}: Permission timeout for {tool_name}")
                return False

        except Exception as e:
            logger.error(f"{self.agent_name}: Permission request failed: {e}")
            return False

    async def _wait_for_approval(self, agent_name: str, tool_name: str) -> bool:
        """Wait for user approval via Slack."""
        try:
            from integrations.slack_client import SlackClient
            slack = SlackClient()

            for _ in range(60):
                messages = await slack.get_recent_messages(
                    channel="#agent-permissions",
                    limit=10
                )

                for msg in messages:
                    text = msg.get('text', '').lower()

                    if f"approve {agent_name.lower()}" in text:
                        logger.info(f"✅ {agent_name}: Permission approved for {tool_name}")
                        return True

                    if "deny" in text and agent_name.lower() in text:
                        logger.info(f"❌ {agent_name}: Permission denied for {tool_name}")
                        return False

                await asyncio.sleep(5)

            logger.warning(f"⏱️ {agent_name}: Approval timeout for {tool_name}")
            return False

        except Exception as e:
            logger.error(f"❌ {agent_name}: Approval monitoring failed: {e}")
            return False

# ===== SELF-OPTIMIZING AGENT BASE CLASS =====

class SelfOptimizingAgent(dspy.Module):
    """Base class for ALL agents with extension system and error recovery."""

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

        # Extension system (Agent Zero pattern)
        self.extensions: Dict[str, List[AgentExtension]] = {
            'before_execute': [],
            'after_execute': [],
            'on_error': [],
            'on_optimize': []
        }

        # Agent ID for state persistence
        self.agent_id = str(uuid4())

        logger.info(f"✅ {agent_name} initialized with {rules.optimizer} optimizer")

    def register_extension(self, hook_name: str, extension: AgentExtension) -> None:
        """Register an extension for a specific hook."""
        if hook_name not in self.extensions:
            raise ValueError(f"Invalid hook name: {hook_name}")

        self.extensions[hook_name].append(extension)
        logger.info(f"✅ {self.agent_name}: Registered extension '{extension.name}' for hook '{hook_name}'")

    async def call_extensions(self, hook_name: str, **kwargs) -> Dict[str, Any]:
        """Call all registered extensions for a hook."""
        results = {}

        for extension in self.extensions.get(hook_name, []):
            try:
                if hook_name == 'before_execute':
                    ext_result = await extension.before_execute(**kwargs)
                elif hook_name == 'after_execute':
                    ext_result = await extension.after_execute(**kwargs)
                elif hook_name == 'on_error':
                    ext_result = await extension.on_error(**kwargs)
                elif hook_name == 'on_optimize':
                    ext_result = await extension.on_optimize(**kwargs)
                else:
                    continue

                if ext_result:
                    results.update(ext_result)

            except Exception as e:
                logger.error(f"❌ {self.agent_name}: Extension '{extension.name}' failed: {e}")

        return results

    async def execute_with_monitoring(
        self,
        task: str,
        complexity: str = "medium",
        customer_facing: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute task with performance monitoring and extension hooks."""
        try:
            # Call before_execute extensions
            before_mods = await self.call_extensions(
                'before_execute',
                task=task,
                complexity=complexity,
                customer_facing=customer_facing,
                **kwargs
            )

            kwargs.update(before_mods)

            # Select model
            model = self.model_selector.select(complexity, customer_facing)
            dspy.configure(lm=dspy.LM(model))

            # Execute task with error recovery
            result = await self._execute_with_recovery(task, **kwargs)

            # Call after_execute extensions
            after_mods = await self.call_extensions(
                'after_execute',
                task=task,
                result=result,
                **kwargs
            )

            result.update(after_mods)

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

        except Exception as e:
            logger.error(f"❌ {self.agent_name}: Task execution failed: {e}")

            # Call on_error extensions
            recovery_result = await self.call_extensions(
                'on_error',
                task=task,
                error=e,
                **kwargs
            )

            if recovery_result:
                logger.info(f"✅ {self.agent_name}: Error recovered by extension")
                return recovery_result

            raise

    async def _execute_with_recovery(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute task with automatic error recovery."""
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                result = await self.forward_async(task, **kwargs)
                return result

            except RepairableException as e:
                if not e.can_repair():
                    logger.error(f"❌ {self.agent_name}: Max repair attempts reached")
                    raise

                logger.warning(f"⚠️ {self.agent_name}: Repairable error (attempt {attempt + 1}/{max_attempts}): {e}")

                try:
                    repair_result = await self._attempt_repair(task, e, **kwargs)
                    if repair_result:
                        logger.info(f"✅ {self.agent_name}: Error repaired successfully")
                        return repair_result
                except Exception as repair_error:
                    logger.error(f"❌ {self.agent_name}: Repair failed: {repair_error}")

                e.repair_attempts += 1

            except Exception as e:
                logger.error(f"❌ {self.agent_name}: Non-repairable error: {e}")
                raise

        raise Exception(f"Task failed after {max_attempts} attempts")

    async def _attempt_repair(self, task: str, error: RepairableException, **kwargs) -> Optional[Dict[str, Any]]:
        """Attempt to repair error using LLM analysis."""
        try:
            repair_prompt = f"""Task failed with error: {str(error)}

Original task: {task}
Error context: {error.context}

Analyze the error and suggest a fix. Then retry the task with the fix applied."""

            dspy.configure(lm=dspy.LM(self.model_selector.select("complex", False)))

            logger.warning(f"⚠️ {self.agent_name}: Repair logic not implemented in subclass")
            return None

        except Exception as e:
            logger.error(f"❌ {self.agent_name}: Repair attempt failed: {e}")
            return None

    async def request_tool_access(
        self,
        tool_name: str,
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
        """Run optimization (GEPA or BootstrapFewShot)."""
        logger.info(f"🔧 Running {self.rules.optimizer} optimization for {self.agent_name}")

        try:
            if self.rules.optimizer == "gepa":
                from optimization.gepa_optimizer import GEPAOptimizer

                optimizer = GEPAOptimizer(
                    max_metric_calls=500,
                    reflection_model="openrouter/anthropic/claude-sonnet-4.5"
                )

                trainset = self._create_trainset_from_history()

                if len(trainset) < 10:
                    logger.warning(f"⚠️ Not enough training data ({len(trainset)} examples)")
                    return

                def metric(example, prediction, trace=None):
                    if hasattr(prediction, 'success'):
                        return 1.0 if prediction.success else 0.0
                    return 0.5

                result = await optimizer.optimize(
                    agent=self,
                    trainset=trainset,
                    metric=metric,
                    agent_name=self.agent_name
                )

                logger.info(f"✅ GEPA optimization complete!")
                logger.info(f"  - Baseline: {result.baseline_score:.2%}")
                logger.info(f"  - Optimized: {result.optimized_score:.2%}")

            elif self.rules.optimizer == "bootstrap":
                from dspy.teleprompt import BootstrapFewShot

                trainset = self._create_trainset_from_history()

                if len(trainset) < 5:
                    logger.warning(f"⚠️ Not enough training data ({len(trainset)} examples)")
                    return

                def metric(example, prediction, trace=None):
                    if hasattr(prediction, 'success'):
                        return 1.0 if prediction.success else 0.0
                    return 0.5

                optimizer = BootstrapFewShot(metric=metric, max_bootstrapped_demos=4)
                optimized = optimizer.compile(student=self, trainset=trainset)

                save_path = f"optimized_{self.agent_name.lower()}_bootstrap.json"
                optimized.save(save_path)

                logger.info(f"✅ BootstrapFewShot optimization complete!")

        except Exception as e:
            logger.error(f"❌ Optimization failed for {self.agent_name}: {e}")

    def _create_trainset_from_history(self) -> List:
        """Create training dataset from performance history."""
        trainset = []

        for record in self.performance_tracker.history:
            if record.success and record.user_satisfaction >= 3.5:
                example = dspy.Example(
                    task=record.task,
                    success=True
                ).with_inputs("task")

                trainset.append(example)

        return trainset

    async def save_state(self, state: Dict[str, Any]) -> None:
        """Save agent state to Supabase."""
        try:
            from config.settings import settings
            from supabase import create_client

            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

            await supabase.table('agent_state').upsert({
                'agent_id': self.agent_id,
                'agent_type': self.__class__.__name__,
                'state': state,
                'last_updated': datetime.now().isoformat()
            }).execute()

            logger.info(f"✅ State saved for agent {self.agent_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save state: {e}")

    async def load_state(self) -> Optional[Dict[str, Any]]:
        """Load agent state from Supabase."""
        try:
            from config.settings import settings
            from supabase import create_client

            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

            result = await supabase.table('agent_state').select('state').eq('agent_id', self.agent_id).execute()

            if result.data:
                logger.info(f"✅ State loaded for agent {self.agent_id}")
                return result.data[0]['state']
            else:
                logger.info(f"ℹ️ No saved state for agent {self.agent_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to load state: {e}")
            return None

    async def forward_async(self, task: str, **kwargs) -> Dict[str, Any]:
        """Override in subclass."""
        raise NotImplementedError("Subclass must implement forward_async()")
