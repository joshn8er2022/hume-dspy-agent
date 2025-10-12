"""Core configuration and setup."""
from .config import settings, Settings
from .dspy_setup import dspy_manager, DSPyManager

__all__ = [
    "settings",
    "Settings",
    "dspy_manager",
    "DSPyManager",
]
