"""Sequential Thought Module - DSPy Implementation

Type-safe, production-ready implementation of Sequential Thought reasoning.
Integrates with DSPy for optimization and Agent Zero for MCP tool exposure.
"""

import dspy
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ===== PYDANTIC MODELS =====

class ThoughtType(BaseModel):
    """Type of thought in the reasoning chain."""
    type: Literal["analysis", "hypothesis", "verification", "revision", "synthesis"]
    description: str = Field(..., description="What this thought type represents")

class Thought(BaseModel):
    """Single thought in the reasoning chain."""
    number: int = Field(..., ge=1, description="Thought number in sequence")
    content: str = Field(..., min_length=10, description="The actual thought content")
    thought_type: Literal["analysis", "hypothesis", "verification", "revision", "synthesis"] = "analysis"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in this thought")
    is_revision: bool = Field(default=False, description="Is this revising previous thinking?")
    revises_thought: Optional[int] = Field(default=None, description="Which thought number is being revised")
    branch_id: Optional[str] = Field(default=None, description="Branch identifier if branching")
    branch_from: Optional[int] = Field(default=None, description="Thought number where branch started")

class ThoughtChain(BaseModel):
    """Complete chain of thoughts leading to a conclusion."""
    problem: str = Field(..., description="The problem being solved")
    context: Optional[str] = Field(default=None, description="Additional context")
    thoughts: List[Thought] = Field(default_factory=list, description="Chain of thoughts")
    conclusion: Optional[str] = Field(default=None, description="Final conclusion")
    total_thoughts: int = Field(default=10, ge=1, le=50, description="Estimated total thoughts needed")
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ===== DSPY SIGNATURES =====

class GenerateThought(dspy.Signature):
    """Generate next thought in reasoning chain."""
    problem: str = dspy.InputField(desc="Problem to solve")
    context: str = dspy.InputField(desc="Additional context")
    previous_thoughts: str = dspy.InputField(desc="Previous thoughts in chain")
    thought_number: int = dspy.InputField(desc="Current thought number")
    total_thoughts: int = dspy.InputField(desc="Estimated total thoughts")

    thought_content: str = dspy.OutputField(desc="The next thought")
    thought_type: str = dspy.OutputField(desc="Type: analysis, hypothesis, verification, revision, synthesis")
    confidence: float = dspy.OutputField(desc="Confidence 0.0-1.0")
    is_revision: bool = dspy.OutputField(desc="Is this revising previous thinking?")
    revises_thought: Optional[int] = dspy.OutputField(desc="Which thought number being revised (if any)")
    needs_more_thoughts: bool = dspy.OutputField(desc="Need more thoughts after this?")

class SynthesizeConclusion(dspy.Signature):
    """Synthesize final conclusion from thought chain."""
    problem: str = dspy.InputField(desc="Original problem")
    context: str = dspy.InputField(desc="Additional context")
    thought_chain: str = dspy.InputField(desc="Complete chain of thoughts")

    conclusion: str = dspy.OutputField(desc="Final synthesized conclusion")
    confidence: float = dspy.OutputField(desc="Overall confidence 0.0-1.0")

# ===== SEQUENTIAL THOUGHT MODULE =====

class SequentialThinkingModule(dspy.Module):
    """DSPy module for sequential thought reasoning.

    Features:
    - Type-safe Pydantic models
    - Branching and revision support
    - Confidence tracking
    - Auto-synthesis when max thoughts reached
    - Comprehensive error handling
    """

    def __init__(self, max_thoughts: int = 20):
        super().__init__()
        self.max_thoughts = max_thoughts
        self.generate_thought = dspy.ChainOfThought(GenerateThought)
        self.synthesize = dspy.ChainOfThought(SynthesizeConclusion)

    def forward(
        self,
        problem: str,
        context: Optional[str] = None,
        initial_thoughts: int = 10
    ) -> ThoughtChain:
        """Execute sequential thought reasoning.

        Args:
            problem: The problem to solve
            context: Additional context (optional)
            initial_thoughts: Initial estimate of thoughts needed

        Returns:
            ThoughtChain with complete reasoning process
        """
        try:
            # Initialize thought chain
            chain = ThoughtChain(
                problem=problem,
                context=context or "",
                total_thoughts=min(initial_thoughts, self.max_thoughts)
            )

            # Generate thoughts iteratively
            thought_number = 1
            needs_more = True

            while needs_more and thought_number <= self.max_thoughts:
                # Format previous thoughts
                prev_thoughts = self._format_previous_thoughts(chain.thoughts)

                # Generate next thought
                result = self.generate_thought(
                    problem=problem,
                    context=context or "",
                    previous_thoughts=prev_thoughts,
                    thought_number=thought_number,
                    total_thoughts=chain.total_thoughts
                )

                # Create thought object
                thought = Thought(
                    number=thought_number,
                    content=result.thought_content,
                    thought_type=result.thought_type,
                    confidence=float(result.confidence),
                    is_revision=result.is_revision,
                    revises_thought=result.revises_thought
                )

                chain.thoughts.append(thought)

                # Check if more thoughts needed
                needs_more = result.needs_more_thoughts
                thought_number += 1

                # Auto-adjust total if needed
                if thought_number > chain.total_thoughts and needs_more:
                    chain.total_thoughts = min(thought_number + 5, self.max_thoughts)

            # Synthesize conclusion
            chain.conclusion = self._synthesize_conclusion(chain)

            return chain

        except Exception as e:
            logger.error(f"Sequential thought failed: {e}")
            # Return partial chain with error
            chain.conclusion = f"Error during reasoning: {str(e)}"
            return chain

    def _format_previous_thoughts(self, thoughts: List[Thought]) -> str:
        """Format previous thoughts for context."""
        if not thoughts:
            return "No previous thoughts yet."

        formatted = []
        for t in thoughts:
            prefix = "🔄" if t.is_revision else "💭"
            formatted.append(
                f"{prefix} Thought {t.number} ({t.thought_type}, confidence: {t.confidence:.2f}): {t.content}"
            )

        return "\n".join(formatted)

    def _synthesize_conclusion(self, chain: ThoughtChain) -> str:
        """Synthesize final conclusion from thought chain."""
        try:
            thought_summary = self._format_previous_thoughts(chain.thoughts)

            result = self.synthesize(
                problem=chain.problem,
                context=chain.context or "",
                thought_chain=thought_summary
            )

            return result.conclusion

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return f"Unable to synthesize conclusion: {str(e)}"

    def to_markdown(self, chain: ThoughtChain) -> str:
        """Convert thought chain to markdown format."""
        md = f"""# Sequential Thought Process

## Problem:
{chain.problem}

"""

        if chain.context:
            md += f"""## Context:
{chain.context}

"""

        md += """## Reasoning Chain:

"""

        for thought in chain.thoughts:
            prefix = "🔄" if thought.is_revision else "💭"
            md += f"""### {prefix} Thought {thought.number} ({thought.thought_type})
"""
            md += f"""**Confidence**: {thought.confidence:.0%}

"""
            md += f"""{thought.content}

"""

            if thought.is_revision and thought.revises_thought:
                md += f"""*Revises thought #{thought.revises_thought}*

"""

        md += f"""## Conclusion:
{chain.conclusion}
"""

        return md

# ===== CONVENIENCE FUNCTIONS =====

def sequential_think(
    problem: str,
    context: Optional[str] = None,
    max_thoughts: int = 20
) -> ThoughtChain:
    """Convenience function for sequential thinking.

    Args:
        problem: Problem to solve
        context: Additional context
        max_thoughts: Maximum thoughts to generate

    Returns:
        Complete thought chain with conclusion
    """
    module = SequentialThinkingModule(max_thoughts=max_thoughts)
    return module.forward(problem=problem, context=context)

# ===== EXPORTS =====

__all__ = [
    "ThoughtType",
    "Thought",
    "ThoughtChain",
    "SequentialThinkingModule",
    "sequential_think"
]
