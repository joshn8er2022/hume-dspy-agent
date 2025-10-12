"""DSPy initialization and configuration."""
import dspy
from typing import Optional
from .config import settings


class DSPyManager:
    """Manager for DSPy LLM configuration with switchable backends."""

    def __init__(self):
        self._lm: Optional[dspy.LM] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize DSPy with configured LLM backend."""
        if self._initialized:
            return

        api_key = settings.get_llm_api_key()

        if settings.llm_provider == "openai":
            self._lm = dspy.LM(
                model=f"openai/{settings.dspy_model}",
                api_key=api_key,
                max_tokens=settings.dspy_max_tokens,
                temperature=settings.dspy_temperature,
            )
        elif settings.llm_provider == "anthropic":
            self._lm = dspy.LM(
                model=f"anthropic/{settings.dspy_model}",
                api_key=api_key,
                max_tokens=settings.dspy_max_tokens,
                temperature=settings.dspy_temperature,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

        # Configure DSPy to use this LM
        dspy.configure(lm=self._lm)
        self._initialized = True

        print(f"✅ DSPy initialized with {settings.llm_provider}/{settings.dspy_model}")

    def get_lm(self) -> dspy.LM:
        """Get the configured language model."""
        if not self._initialized:
            self.initialize()
        return self._lm

    def switch_provider(self, provider: str, model: str) -> None:
        """Switch LLM provider at runtime."""
        settings.llm_provider = provider
        settings.dspy_model = model
        self._initialized = False
        self.initialize()
        print(f"✅ Switched to {provider}/{model}")


# Global DSPy manager instance
dspy_manager = DSPyManager()
