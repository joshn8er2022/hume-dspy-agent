"""
GEPA Optimizer Implementation

Genetic Evolution for Prompt Adaptation (GEPA) optimizer for DSPy agents.

Based on research:
- 20-point improvement (38% → 69% on HotPotQA)
- Outperforms MIPRO, GRPO, reinforcement learning
- Sample efficient (tens vs thousands of rollouts)

Features:
- Genetic optimization for DSPy prompts
- Natural language feedback (not just 0/1 scores)
- Pareto-optimal selection
- Reflective prompt evolution
"""

import dspy
import logging
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OptimizationResult(BaseModel):
    """Result of GEPA optimization run."""
    agent_name: str
    optimizer: str = "gepa"
    
    # Performance
    baseline_score: float = Field(ge=0.0, le=1.0)
    optimized_score: float = Field(ge=0.0, le=1.0)
    improvement: float = Field(ge=0.0)
    
    # Cost
    optimization_cost: float
    metric_calls: int
    duration_seconds: float
    
    # Results
    optimized_prompts: Dict[str, str]
    saved_to: str
    
    # Metadata
    optimized_at: datetime = Field(default_factory=datetime.utcnow)


class GEPAOptimizer:
    """GEPA optimizer for DSPy agents.
    
    Implements genetic evolution for prompt adaptation.
    """
    
    def __init__(
        self,
        max_metric_calls: int = 500,
        reflection_model: str = "openrouter/anthropic/claude-sonnet-4.5",
        use_wandb: bool = False
    ):
        self.max_metric_calls = max_metric_calls
        self.reflection_model = reflection_model
        self.use_wandb = use_wandb
        
        logger.info(f"✅ GEPA optimizer initialized (max_calls={max_metric_calls})")
    
    async def optimize(
        self,
        agent: dspy.Module,
        trainset: List[dspy.Example],
        metric: Callable,
        agent_name: str
    ) -> OptimizationResult:
        """Run GEPA optimization on agent.
        
        Args:
            agent: DSPy agent to optimize
            trainset: Training examples
            metric: Metric function (returns score + feedback)
            agent_name: Name of agent being optimized
        
        Returns:
            OptimizationResult with performance improvements
        """
        logger.info(f"🔧 Starting GEPA optimization for {agent_name}")
        start_time = datetime.utcnow()
        
        try:
            # Import GEPA from DSPy
            from dspy.teleprompt import GEPA
            
            # Configure GEPA optimizer
            optimizer = GEPA(
                metric=metric,
                max_metric_calls=self.max_metric_calls,
                reflection_lm=dspy.LM(self.reflection_model, max_tokens=32000, temperature=1.0),
                use_merge=True,  # System-aware merging
                num_threads=4
            )
            
            # Evaluate baseline
            logger.info(f"📊 Evaluating baseline performance...")
            evaluator = dspy.Evaluate(
                devset=trainset[:20],  # Use subset for baseline
                metric=metric,
                num_threads=4
            )
            baseline_score = evaluator(agent)
            logger.info(f"📊 Baseline score: {baseline_score:.2%}")
            
            # Run GEPA optimization
            logger.info(f"🔧 Running GEPA optimization ({self.max_metric_calls} metric calls)...")
            optimized_agent = optimizer.compile(
                student=agent,
                trainset=trainset
            )
            
            # Evaluate optimized
            logger.info(f"📊 Evaluating optimized performance...")
            optimized_score = evaluator(optimized_agent)
            logger.info(f"📊 Optimized score: {optimized_score:.2%}")
            
            # Calculate improvement
            improvement = optimized_score - baseline_score
            logger.info(f"📈 Improvement: +{improvement:.2%}")
            
            # Save optimized agent
            save_path = f"optimized_{agent_name.lower()}_gepa.json"
            optimized_agent.save(save_path)
            logger.info(f"💾 Saved optimized agent to {save_path}")
            
            # Calculate duration and cost
            duration = (datetime.utcnow() - start_time).total_seconds()
            cost = self._estimate_cost(self.max_metric_calls)
            
            # Extract optimized prompts
            optimized_prompts = self._extract_prompts(optimized_agent)
            
            return OptimizationResult(
                agent_name=agent_name,
                baseline_score=baseline_score,
                optimized_score=optimized_score,
                improvement=improvement,
                optimization_cost=cost,
                metric_calls=self.max_metric_calls,
                duration_seconds=duration,
                optimized_prompts=optimized_prompts,
                saved_to=save_path
            )
            
        except Exception as e:
            logger.error(f"❌ GEPA optimization failed: {e}")
            raise
    
    def _estimate_cost(self, metric_calls: int) -> float:
        """Estimate optimization cost.
        
        Based on GEPA research:
        - 500 metric calls ≈ $25-30
        - Reflection LM (Claude Sonnet) ≈ $15-20
        """
        base_cost = (metric_calls / 500) * 25
        reflection_cost = (metric_calls / 500) * 15
        return base_cost + reflection_cost
    
    def _extract_prompts(self, agent: dspy.Module) -> Dict[str, str]:
        """Extract optimized prompts from agent."""
        prompts = {}
        
        # Extract from DSPy modules
        for name, module in agent.__dict__.items():
            if isinstance(module, dspy.Predict):
                if hasattr(module, 'signature'):
                    prompts[name] = str(module.signature.instructions)
        
        return prompts
