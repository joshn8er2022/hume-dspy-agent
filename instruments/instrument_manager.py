"""Instrument Manager - Dynamic tool discovery via semantic search.

Instead of putting all tools in the system prompt, store them in a vector DB
and discover relevant tools based on the query. This allows unlimited tools
without prompt bloat.
"""

import logging
import inspect
from typing import List, Dict, Callable, Optional, Any
from dataclasses import dataclass
import os

from memory.vector_memory import AgentMemory, MemoryType

logger = logging.getLogger(__name__)


@dataclass
class Instrument:
    """A tool/function that agents can invoke."""
    
    name: str
    description: str
    function: Callable
    category: str = "general"
    signature: Optional[str] = None
    examples: List[str] = None
    
    def __post_init__(self):
        if self.signature is None:
            try:
                self.signature = str(inspect.signature(self.function))
            except:
                self.signature = "(...)"
        
        if self.examples is None:
            self.examples = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "signature": self.signature,
            "examples": self.examples
        }
    
    def to_search_text(self) -> str:
        """Generate text for semantic search indexing."""
        parts = [
            f"Tool: {self.name}",
            f"Category: {self.category}",
            f"Description: {self.description}",
            f"Signature: {self.signature}"
        ]
        
        if self.examples:
            parts.append(f"Examples: {' | '.join(self.examples)}")
        
        return "\n".join(parts)


class InstrumentManager:
    """Manage tools using vector search instead of system prompt.
    
    Benefits:
    - Add unlimited tools without bloating prompts
    - Semantic discovery of relevant tools
    - Dynamic loading based on query
    - Easy categorization and organization
    """
    
    def __init__(self, memory: Optional[AgentMemory] = None):
        """Initialize instrument manager.
        
        Args:
            memory: Optional AgentMemory instance. If None, creates new one.
        """
        # Use shared memory for instruments
        if memory is None:
            try:
                from memory.vector_memory import get_agent_memory
                memory = get_agent_memory("instruments")
            except Exception as e:
                logger.error(f"Failed to initialize instrument memory: {e}")
                self.memory = None
        
        self.memory = memory
        self.instruments: Dict[str, Instrument] = {}
        self.enabled = memory is not None
        
        if self.enabled:
            logger.info("✅ Instrument Manager initialized with vector search")
        else:
            logger.warning("⚠️ Instrument Manager disabled (FAISS not available)")
    
    def register_instrument(
        self,
        name: str,
        description: str,
        function: Callable,
        category: str = "general",
        examples: Optional[List[str]] = None
    ) -> bool:
        """Register a new instrument.
        
        Args:
            name: Unique name for the instrument
            description: Clear description of what it does
            function: The callable function
            category: Category for organization
            examples: Example use cases
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning(f"Instrument Manager disabled, cannot register: {name}")
            return False
        
        try:
            # Create instrument
            instrument = Instrument(
                name=name,
                description=description,
                function=function,
                category=category,
                examples=examples or []
            )
            
            # Store locally
            self.instruments[name] = instrument
            
            # Store in vector DB for semantic search
            if self.memory:
                self.memory.remember_sync(
                    content=instrument.to_search_text(),
                    memory_type=MemoryType.TOOL_RESULT,  # Reusing tool_result type
                    metadata={
                        "instrument_name": name,
                        "category": category,
                        "signature": instrument.signature
                    }
                )
            
            logger.info(f"✅ Registered instrument: {name} ({category})")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register instrument {name}: {e}")
            return False
    
    def discover_instruments(
        self,
        query: str,
        k: int = 5,
        category: Optional[str] = None,
        min_score: float = 0.3
    ) -> List[Instrument]:
        """Find relevant instruments via semantic search.
        
        Args:
            query: The user's query or task description
            k: Number of instruments to return
            category: Optional category filter
            min_score: Minimum relevance score (0.0 to 1.0)
        
        Returns:
            List of relevant Instrument objects
        """
        if not self.enabled or not self.memory:
            # Return all instruments if discovery disabled
            return list(self.instruments.values())[:k]
        
        try:
            # Search for relevant instruments
            results = self.memory.recall_sync(
                query=query,
                k=k * 2,  # Get more, then filter
                memory_type=MemoryType.TOOL_RESULT,
                min_score=min_score
            )
            
            # Extract instruments
            instruments = []
            seen = set()
            
            for result in results:
                inst_name = result["metadata"].get("instrument_name")
                if inst_name and inst_name in self.instruments and inst_name not in seen:
                    instrument = self.instruments[inst_name]
                    
                    # Apply category filter if specified
                    if category and instrument.category != category:
                        continue
                    
                    instruments.append(instrument)
                    seen.add(inst_name)
                    
                    if len(instruments) >= k:
                        break
            
            logger.debug(
                f"🔍 Discovered {len(instruments)} instruments for: {query[:50]}..."
            )
            
            return instruments
        
        except Exception as e:
            logger.error(f"Failed to discover instruments: {e}")
            # Fallback to returning all instruments
            return list(self.instruments.values())[:k]
    
    def get_instrument(self, name: str) -> Optional[Instrument]:
        """Get a specific instrument by name."""
        return self.instruments.get(name)
    
    def list_instruments(
        self,
        category: Optional[str] = None
    ) -> List[Instrument]:
        """List all registered instruments, optionally filtered by category."""
        if category:
            return [
                inst for inst in self.instruments.values()
                if inst.category == category
            ]
        return list(self.instruments.values())
    
    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return list(set(inst.category for inst in self.instruments.values()))
    
    def save(self):
        """Persist instruments to disk."""
        if self.memory:
            self.memory.save()
            logger.info("💾 Saved instruments to disk")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get instrument manager statistics."""
        return {
            "enabled": self.enabled,
            "total_instruments": len(self.instruments),
            "categories": self.get_categories(),
            "memory_stats": self.memory.get_stats() if self.memory else None
        }


# Decorator for easy instrument creation
def instrument(
    description: str,
    category: str = "general",
    examples: Optional[List[str]] = None
):
    """Decorator to mark a function as an instrument.
    
    Usage:
        @instrument("Calculate ROI for marketing campaigns", category="analytics")
        def calculate_roi(revenue: float, cost: float) -> float:
            return (revenue - cost) / cost * 100
    
    Args:
        description: Clear description of what the function does
        category: Category for organization
        examples: Example use cases
    """
    def decorator(func: Callable):
        func._instrument_description = description
        func._instrument_category = category
        func._instrument_examples = examples or []
        func._is_instrument = True
        return func
    return decorator


# Global instrument manager instance
_instrument_manager: Optional[InstrumentManager] = None


def get_instrument_manager() -> InstrumentManager:
    """Get or create global instrument manager instance."""
    global _instrument_manager
    
    if _instrument_manager is None:
        _instrument_manager = InstrumentManager()
    
    return _instrument_manager
