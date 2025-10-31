"""DSPy modules and signatures."""
from .signatures import (
    QualifyLead,
    AnalyzeBusinessFit,
    AnalyzeEngagement,
    DetermineNextActions,
    GenerateEmailTemplate,
    GenerateSMSMessage,
)

__all__ = [
    "QualifyLead",
    "AnalyzeBusinessFit",
    "AnalyzeEngagement",
    "DetermineNextActions",
    "GenerateEmailTemplate",
    "GenerateSMSMessage",
]

# Sequential Thought Module (Week 1 Implementation)
from dspy_modules.sequential_thought import (
    SequentialThinkingModule,
    Thought,
    ThoughtChain,
    ThoughtType,
    sequential_think,
)
