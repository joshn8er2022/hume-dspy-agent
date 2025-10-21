
"""Message Complexity Classifier for Model Selection.

Classifies incoming messages to determine appropriate model and context level.
"""

import re
from typing import Literal

ComplexityLevel = Literal["simple", "complex"]


class MessageClassifier:
    """Classify message complexity for optimal model selection."""

    # Simple message patterns (use Haiku + minimal context)
    SIMPLE_PATTERNS = [
        # Greetings
        r'^(hi|hey|hello|yo|sup)\b',
        # Acknowledgments
        r'^(yes|yeah|yep|ok|okay|sure|alright|got it|sounds good)\b',
        r'^(no|nope|nah)\b',
        # Thanks
        r'^(thanks|thank you|thx)\b',
        # Simple commands
        r'^(do it|go ahead|proceed|continue)\b',
        # Status checks (single word/phrase)
        r'^(status|update|progress)\??$',
    ]

    # Complex message indicators (use Sonnet + full context)
    COMPLEX_INDICATORS = [
        # Analysis requests
        r'\b(analyze|analysis|evaluate|assess|review)\b',
        # Strategic questions
        r'\b(strategy|strategic|plan|planning|roadmap)\b',
        # Research requests
        r'\b(research|investigate|find out|look into)\b',
        # Competitive intelligence
        r'\b(competitor|competitive|market|industry)\b',
        # Multi-step tasks
        r'\b(create|build|develop|implement|design)\b',
        # Questions requiring deep thought
        r'\b(why|how|what if|should we|would it)\b',
        # Data/metrics requests
        r'\b(pipeline|leads|conversion|metrics|stats|data)\b',
    ]

    def classify(self, message: str) -> ComplexityLevel:
        """Classify message complexity.

        Args:
            message: User message text

        Returns:
            "simple" or "complex"
        """
        message_lower = message.lower().strip()

        # Empty or very short messages are simple
        if len(message_lower) < 3:
            return "simple"

        # Check for simple patterns first (higher priority)
        for pattern in self.SIMPLE_PATTERNS:
            if re.search(pattern, message_lower):
                return "simple"

        # Check for complex indicators
        for pattern in self.COMPLEX_INDICATORS:
            if re.search(pattern, message_lower):
                return "complex"

        # Default heuristics
        # Long messages (>100 chars) are usually complex
        if len(message) > 100:
            return "complex"

        # Multiple sentences suggest complexity
        if message.count('.') > 1 or message.count('?') > 1:
            return "complex"

        # Default to simple (safer, cheaper)
        return "simple"

    def needs_full_context(self, message: str) -> bool:
        """Determine if message needs full infrastructure context.

        Args:
            message: User message text

        Returns:
            True if full context needed, False for minimal context
        """
        message_lower = message.lower()

        # Keywords that require full context
        full_context_keywords = [
            "infrastructure", "architecture", "system", "agents",
            "integrations", "deployment", "tech stack", "capabilities"
        ]

        return any(keyword in message_lower for keyword in full_context_keywords)

    def needs_pipeline_data(self, message: str) -> bool:
        """Determine if message needs pipeline/lead data.

        Args:
            message: User message text

        Returns:
            True if pipeline data needed
        """
        message_lower = message.lower()

        # Keywords that require pipeline data
        pipeline_keywords = [
            "pipeline", "leads", "lead", "tier", "hot", "warm", "cold",
            "qualified", "unqualified", "conversion", "stats", "metrics"
        ]

        return any(keyword in message_lower for keyword in pipeline_keywords)


# Global singleton
_classifier = None

def get_classifier() -> MessageClassifier:
    """Get or create global MessageClassifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = MessageClassifier()
    return _classifier


def classify_message(message: str) -> ComplexityLevel:
    """Convenience function to classify a message."""
    return get_classifier().classify(message)


def needs_full_context(message: str) -> bool:
    """Convenience function to check if full context needed."""
    return get_classifier().needs_full_context(message)


def needs_pipeline_data(message: str) -> bool:
    """Convenience function to check if pipeline data needed."""
    return get_classifier().needs_pipeline_data(message)
