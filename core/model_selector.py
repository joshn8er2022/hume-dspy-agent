"""
Model Selection Strategy for Cost Optimization

Two-Tier Paid Model System:
- Haiku 4.5: Fast, cheap for routine low-level agentic work
- Sonnet 4.5: Premium for complex high-level reasoning

Plus free models for background/overnight work.
"""

import random
import os
from typing import Literal
import dspy
import logging

logger = logging.getLogger(__name__)

TaskType = Literal[
    "email_to_lead", 
    "slack_response", 
    "qualification", 
    "follow_up",
    "strategy_analysis",
    "complex_research",
    "competitor_analysis",
    "research",
    "brainstorm",
    "analysis",
    "draft"
]

ComplexityLevel = Literal["low", "high"]


class ModelSelector:
    """
    Smart model selection based on task type and complexity.
    
    Strategy:
    - Overnight work: Free models (Llama, Mixtral, Qwen)
    - High-complexity: Sonnet 4.5 (premium reasoning)
    - Standard customer-facing: Haiku 4.5 (fast, cheap)
    - Background work: Free models
    """
    
    # Free models for overnight/background work
    FREE_MODELS = [
        "openrouter/meta-llama/llama-3.1-70b-instruct",
        "openrouter/mistralai/mixtral-8x7b-instruct",
        "openrouter/qwen/qwen-2.5-72b-instruct"
    ]
    
    # Low-tier paid: Fast, cheap for routine work
    PAID_MODEL_LOW = "openrouter/anthropic/claude-haiku-4.5"
    
    # High-tier paid: Premium for complex reasoning
    PAID_MODEL_HIGH = "openrouter/anthropic/claude-sonnet-4.5"
    
    # High-complexity task types (get Sonnet 4.5)
    HIGH_COMPLEXITY_TASKS = [
        "strategy_analysis",
        "complex_research", 
        "competitor_analysis",
        "multi_agent_synthesis",
        "strategic_planning"
    ]
    
    # Standard customer-facing tasks (get Haiku 4.5)
    CUSTOMER_FACING_TASKS = [
        "email_to_lead",
        "slack_response",
        "qualification",
        "follow_up",
        "simple_research"
    ]
    
    # Background tasks (get free models)
    BACKGROUND_TASKS = [
        "research",
        "brainstorm",
        "analysis",
        "draft",
        "data_processing"
    ]
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.error("❌ OPENROUTER_API_KEY not found!")
            raise ValueError("OPENROUTER_API_KEY required for model selection")
    
    def select_model(
        self, 
        task_type: TaskType,
        is_overnight: bool = False,
        complexity: ComplexityLevel = "low",
        force_paid: bool = False
    ) -> str:
        """
        Select appropriate model based on task and complexity.
        
        Args:
            task_type: Type of task being performed
            is_overnight: Whether this is overnight/background work
            complexity: Explicit complexity level override
            force_paid: Force use of paid model (for critical tasks)
            
        Returns:
            Model identifier string for OpenRouter
        """
        
        # Overnight work always uses free models
        if is_overnight and not force_paid:
            model = random.choice(self.FREE_MODELS)
            logger.info(f"🌙 Overnight task: Using free model {model}")
            return model
        
        # High-complexity tasks get Sonnet 4.5
        if complexity == "high" or task_type in self.HIGH_COMPLEXITY_TASKS:
            logger.info(f"🧠 High-complexity task: Using Sonnet 4.5")
            return self.PAID_MODEL_HIGH
        
        # Standard customer-facing tasks get Haiku 4.5
        if task_type in self.CUSTOMER_FACING_TASKS:
            logger.info(f"⚡ Standard task: Using Haiku 4.5")
            return self.PAID_MODEL_LOW
        
        # Background tasks get free models
        if task_type in self.BACKGROUND_TASKS and not force_paid:
            model = random.choice(self.FREE_MODELS)
            logger.info(f"🔧 Background task: Using free model {model}")
            return model
        
        # Default to low-tier paid for safety
        logger.info(f"🔒 Default: Using Haiku 4.5")
        return self.PAID_MODEL_LOW
    
    def get_dspy_lm(
        self,
        task_type: TaskType,
        is_overnight: bool = False,
        complexity: ComplexityLevel = "low",
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> dspy.LM:
        """
        Get configured DSPy LM for a specific task.
        
        Returns:
            Configured dspy.LM instance
        """
        model = self.select_model(
            task_type=task_type,
            is_overnight=is_overnight,
            complexity=complexity
        )
        
        lm = dspy.LM(
            model=model,
            api_key=self.api_key,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return lm
    
    def configure_dspy(
        self,
        task_type: TaskType,
        is_overnight: bool = False,
        complexity: ComplexityLevel = "low",
        max_tokens: int = 2000,
        temperature: float = 0.7
    ):
        """
        Configure DSPy globally for a specific task.
        
        This updates the global dspy.settings with the appropriate model.
        """
        lm = self.get_dspy_lm(
            task_type=task_type,
            is_overnight=is_overnight,
            complexity=complexity,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        dspy.configure(lm=lm)
        logger.info(f"✅ DSPy configured for {task_type} (complexity: {complexity})")


# Global singleton instance
_model_selector = None

def get_model_selector() -> ModelSelector:
    """Get or create the global ModelSelector instance."""
    global _model_selector
    if _model_selector is None:
        _model_selector = ModelSelector()
    return _model_selector


# Convenience functions
def select_model_for_task(task_type: TaskType, **kwargs) -> str:
    """Convenience function to select model for a task."""
    return get_model_selector().select_model(task_type, **kwargs)


def configure_dspy_for_task(task_type: TaskType, **kwargs):
    """Convenience function to configure DSPy for a task."""
    return get_model_selector().configure_dspy(task_type, **kwargs)
