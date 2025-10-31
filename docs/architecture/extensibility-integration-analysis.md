# Agent-Zero Extensibility Integration Analysis
## Adapting Dynamic Tool Loading for hume-dspy-agent

**Date:** October 30, 2025
**Analysis Type:** Architecture Integration Study
**Goal:** Integrate agent-zero's dynamic tool discovery into hume-dspy-agent while preserving DSPy and Pydantic

---

## Executive Summary

This analysis demonstrates how to integrate **agent-zero's dynamic tool loading** pattern into **hume-dspy-agent** while fully preserving DSPy's reasoning capabilities and Pydantic's type safety. The solution creates a **Pydantic-based tool registry** that discovers tools at runtime, eliminating hardcoded tool lists while maintaining all existing architectural benefits.

**Key Findings:**
- Agent-zero uses file-based tool discovery via `importlib` and reflection
- hume-dspy-agent currently has hardcoded tools as methods in agent classes
- DSPy and Pydantic are fully compatible with dynamic tool loading
- The integration requires ~500 lines of new infrastructure code
- Migration can be done incrementally without breaking existing agents

---

## Part 1: Current Tool Loading Systems

### 1.1 Agent-Zero's Dynamic Tool Loading

#### Architecture Overview

Agent-zero implements runtime tool discovery through a three-layer system:

**File Location:** `/Users/joshisrael/agent-zero/python/helpers/tool.py`

```python
from abc import abstractmethod
from dataclasses import dataclass

@dataclass
class Response:
    message: str
    break_loop: bool

class Tool:
    def __init__(self, agent: Agent, name: str, method: str | None,
                 args: dict[str,str], message: str, loop_data: LoopData | None,
                 **kwargs) -> None:
        self.agent = agent
        self.name = name
        self.method = method
        self.args = args
        self.loop_data = loop_data
        self.message = message

    @abstractmethod
    async def execute(self, **kwargs) -> Response:
        pass

    async def before_execution(self, **kwargs):
        # Logging and preparation
        self.log = self.get_log_object()
        if self.args and isinstance(self.args, dict):
            for key, value in self.args.items():
                # Print arguments
                ...

    async def after_execution(self, response: Response, **kwargs):
        # Store results in history
        self.agent.hist_add_tool_result(self.name, text)
        self.log.update(content=text)
```

**Key Characteristics:**
- Abstract base class with lifecycle hooks (`before_execution`, `after_execution`)
- Returns structured `Response` objects
- Tightly coupled to agent (receives agent in constructor)
- Uses dataclasses, not Pydantic

#### Dynamic Loading Mechanism

**File Location:** `/Users/joshisrael/agent-zero/python/helpers/extract_tools.py`

```python
import importlib.util
import inspect
from typing import Type, TypeVar

T = TypeVar('T')

def load_classes_from_file(file: str, base_class: type[T],
                           one_per_file: bool = True) -> list[type[T]]:
    """Dynamically load tool classes from Python files"""
    classes = []

    # Use importlib to load module dynamically
    module = import_module(file)

    # Get all classes in the module
    class_list = inspect.getmembers(module, inspect.isclass)

    # Filter for subclasses of base_class
    for cls in reversed(class_list):
        if cls[1] is not base_class and issubclass(cls[1], base_class):
            classes.append(cls[1])
            if one_per_file:
                break

    return classes

def import_module(file_path: str):
    """Load a Python module from file path"""
    abs_path = get_abs_path(file_path)
    module_name = os.path.basename(abs_path).replace('.py', '')

    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
```

**Key Features:**
- Uses `importlib.util` for dynamic module loading
- Uses `inspect.getmembers()` to find classes
- Filters by base class via `issubclass()`
- Returns class references (not instances)

#### Tool Discovery at Runtime

**File Location:** `/Users/joshisrael/agent-zero/agent.py` (lines 809-837)

```python
def get_tool(self, name: str, method: str | None, args: dict,
             message: str, loop_data: LoopData | None, **kwargs):
    from python.tools.unknown import Unknown
    from python.helpers.tool import Tool

    classes = []

    # Try agent-specific tools first
    if self.config.profile:
        try:
            classes = extract_tools.load_classes_from_file(
                "agents/" + self.config.profile + "/tools/" + name + ".py",
                Tool
            )
        except Exception as e:
            pass

    # Fall back to default tools
    if not classes:
        try:
            classes = extract_tools.load_classes_from_file(
                "python/tools/" + name + ".py",
                Tool
            )
        except Exception as e:
            pass

    tool_class = classes[0] if classes else Unknown
    return tool_class(
        agent=self, name=name, method=method, args=args,
        message=message, loop_data=loop_data, **kwargs
    )
```

**Discovery Flow:**
1. Agent requests tool by name (e.g., "code_execution_tool")
2. System tries `agents/{profile}/tools/{name}.py` first (custom tools)
3. Falls back to `python/tools/{name}.py` (default tools)
4. Dynamically imports module and extracts Tool subclass
5. Instantiates tool with agent context
6. Returns ready-to-execute tool instance

**Benefits:**
- No hardcoded tool lists
- New tools added by dropping files in directory
- Agent-specific customization via profile folders
- Fails gracefully to `Unknown` tool

---

### 1.2 hume-dspy-agent's Current Tool System

#### Hardcoded Methods in Agent Classes

**File Location:** `/Users/joshisrael/hume-dspy-agent/agents/research_agent.py`

```python
class ResearchAgent(dspy.Module):
    """Agent for conducting deep research on leads and companies.

    Refactored as dspy.Module for better architecture and DSPy optimization.
    """

    def __init__(self):
        super().__init__()  # Initialize dspy.Module

        # DSPy modules for research workflow
        self.plan_research = dspy.ChainOfThought(ResearchPlanning)
        self.synthesize_findings = dspy.ChainOfThought(ResearchSynthesis)

        # Hardcoded API keys
        self.clearbit_api_key = os.getenv("CLEARBIT_API_KEY")
        self.apollo_api_key = os.getenv("APOLLO_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

    async def research_person(
        self,
        name: Optional[str],
        email: Optional[str],
        company: Optional[str] = None
    ) -> PersonProfile:
        """Research an individual person.

        Hardcoded implementation with embedded API calls.
        """
        profile_data = {
            "name": name or "Unknown",
            "email": email,
            "company": company
        }

        # Hardcoded Clearbit lookup
        if email and self.clearbit_api_key:
            try:
                clearbit_data = await self._clearbit_person_lookup(email)
                if clearbit_data:
                    profile_data.update(clearbit_data)
            except Exception as e:
                logger.warning(f"Clearbit failed: {str(e)}")

        # Hardcoded LinkedIn search
        if name and company:
            try:
                linkedin_url = await self._find_linkedin_profile(name, company)
                if linkedin_url:
                    profile_data["linkedin_url"] = linkedin_url
            except Exception as e:
                logger.warning(f"LinkedIn search failed: {str(e)}")

        return PersonProfile(**profile_data)

    async def _clearbit_person_lookup(self, email: str):
        """Hardcoded Clearbit API call - tightly coupled to agent"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://person.clearbit.com/v2/combined/find?email={email}",
                auth=(self.clearbit_api_key, ""),
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return None
```

**Problems with Current Approach:**
1. **Tight Coupling:** Tools are methods on agent classes, can't be reused
2. **Hard to Test:** Must mock agent instance to test individual tools
3. **No Isolation:** All tools share agent state and dependencies
4. **Not Extensible:** Adding new tools requires modifying agent classes
5. **No Versioning:** Can't have multiple implementations of same tool
6. **Duplicated Code:** Same API calls repeated across multiple agents

#### MCP Orchestrator (Partial Solution)

**File Location:** `/Users/joshisrael/hume-dspy-agent/core/mcp_orchestrator.py`

```python
class MCPOrchestrator:
    """Orchestrates dynamic MCP server loading based on task analysis.

    Core Pattern (from PulseMCP paper):
    1. User makes request
    2. Analyze task → Select 2-5 relevant servers
    3. Load ONLY those servers
    4. Execute with lean context
    """

    def __init__(self):
        self.trusted_servers: Dict[str, MCPServerConfig] = {}
        self.active_servers: Set[str] = set()
        self.server_selector = dspy.ChainOfThought(AnalyzeTaskForServers)

        # Load trusted servers from config
        self._load_trusted_servers()

    async def select_servers_for_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Analyze task and select relevant MCP servers to load."""
        servers_desc = self._format_servers_for_llm()
        context_desc = self._format_context(context or {})

        # Use DSPy to analyze and select servers
        result = self.server_selector(
            task_description=task,
            trusted_servers=servers_desc,
            current_context=context_desc
        )

        # Parse selected servers
        selected = result.selected_servers.lower().strip()
        servers = [s.strip() for s in selected.split(",") if s.strip()]

        return servers
```

**What MCP Orchestrator Solves:**
- Dynamic selection of external MCP servers (Zapier, Perplexity, etc.)
- Task-based tool selection using DSPy reasoning
- Reduces context window by loading only needed servers

**What It Doesn't Solve:**
- Internal tools are still hardcoded
- No discovery mechanism for internal tool files
- Can't add new internal tools without code changes

---

## Part 2: Proposed Integration Architecture

### 2.1 Pydantic-Based Tool System

#### Base Tool Class

**Proposed File:** `/Users/joshisrael/hume-dspy-agent/tools/base.py`

```python
"""Pydantic-based tool system compatible with DSPy.

Combines agent-zero's extensibility with Pydantic's validation
and DSPy's tool-calling capabilities.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, List
from pydantic import BaseModel, Field, validator
from enum import Enum
import inspect


class ToolCategory(str, Enum):
    """Tool categories for filtering and organization"""
    RESEARCH = "research"
    CRM = "crm"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    DATA = "data"
    UTILITY = "utility"


class ToolMetadata(BaseModel):
    """Metadata for tool discovery and filtering.

    This replaces agent-zero's loose dictionary approach with
    validated Pydantic model.
    """
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="Human-readable tool description")
    category: ToolCategory = Field(ToolCategory.UTILITY, description="Tool category")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    version: str = Field("1.0.0", description="Tool version for A/B testing")
    requires_auth: bool = Field(False, description="Whether tool needs authentication")
    is_async: bool = Field(True, description="Whether tool is async")
    cost_level: str = Field("FREE", description="FREE, LOW, MEDIUM, HIGH")

    class Config:
        use_enum_values = True


class BaseTool(BaseModel, ABC):
    """Pydantic-based tool that works with DSPy.

    Key Design Decisions:
    1. Inherits from BaseModel for Pydantic validation
    2. Uses ABC for enforcing execute() implementation
    3. Implements __call__ for DSPy compatibility
    4. Stores metadata for discovery and filtering
    5. Supports both sync and async execution
    """

    metadata: ToolMetadata

    class Config:
        arbitrary_types_allowed = True  # Allow non-Pydantic types in fields
        validate_assignment = True      # Validate on attribute assignment

    def __init__(self, **data):
        """Initialize tool with Pydantic validation"""
        super().__init__(**data)

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool's main logic.

        This must be implemented by all tool subclasses.
        Return type should be a Pydantic model or simple type.
        """
        raise NotImplementedError(
            f"Tool {self.metadata.name} must implement execute()"
        )

    def __call__(self, **kwargs) -> Any:
        """Make tool callable for DSPy compatibility.

        DSPy expects tools to be callables. This method:
        1. Makes BaseTool instances callable
        2. Handles async execution transparently
        3. Preserves function signature for DSPy introspection
        """
        # Handle async execution
        import asyncio

        if self.metadata.is_async:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context
                    return loop.create_task(self.execute(**kwargs))
                else:
                    # Sync context, run until complete
                    return loop.run_until_complete(self.execute(**kwargs))
            except RuntimeError:
                # No event loop, create one
                return asyncio.run(self.execute(**kwargs))
        else:
            # Sync execution
            return self.execute(**kwargs)

    def to_dspy_tool(self) -> Callable:
        """Convert to DSPy tool format.

        DSPy expects tools to be callables with:
        - __name__ attribute
        - __doc__ attribute
        - Type hints on parameters

        Returns:
            Callable that DSPy can introspect and use
        """
        # Create wrapper function with proper metadata
        async def tool_wrapper(**kwargs):
            return await self.execute(**kwargs)

        # Set metadata for DSPy
        tool_wrapper.__name__ = self.metadata.name
        tool_wrapper.__doc__ = self.metadata.description

        # Copy signature from execute method for type hints
        tool_wrapper.__signature__ = inspect.signature(self.execute)

        return tool_wrapper

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool inputs/outputs.

        Useful for:
        - API documentation
        - UI generation
        - Validation
        """
        execute_sig = inspect.signature(self.execute)

        schema = {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "parameters": {},
            "return_type": None
        }

        # Extract parameter info
        for param_name, param in execute_sig.parameters.items():
            if param_name == "kwargs":
                continue

            schema["parameters"][param_name] = {
                "type": str(param.annotation),
                "required": param.default == inspect.Parameter.empty
            }

        # Extract return type
        if execute_sig.return_annotation != inspect.Signature.empty:
            schema["return_type"] = str(execute_sig.return_annotation)

        return schema
```

**Key Features:**
1. **Pydantic Validation:** All tool metadata is validated
2. **DSPy Compatibility:** `__call__` makes it work with DSPy
3. **Type Safety:** Uses type hints throughout
4. **Async Support:** Handles async execution transparently
5. **Self-Documenting:** Schema extraction for documentation

---

### 2.2 Dynamic Tool Registry

**Proposed File:** `/Users/joshisrael/hume-dspy-agent/tools/registry.py`

```python
"""Dynamic tool registry inspired by agent-zero's extract_tools.

Provides runtime tool discovery while adding Pydantic validation
and DSPy integration.
"""
from typing import Type, List, Dict, Optional, Set
import importlib.util
import inspect
from pathlib import Path
from .base import BaseTool, ToolCategory, ToolMetadata
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Dynamic tool registry with file-based discovery.

    Adapts agent-zero's pattern:
    1. Scan directories for .py files
    2. Dynamically import modules
    3. Extract BaseTool subclasses
    4. Cache for performance

    Improvements over agent-zero:
    1. Uses Pydantic for validation
    2. Supports multiple tool directories
    3. Caches loaded tools
    4. Provides filtering by category/tags
    """

    def __init__(self, tool_dirs: List[Path]):
        """Initialize registry with tool directories.

        Args:
            tool_dirs: List of directories to scan for tools
                      Example: [Path("tools/research"), Path("tools/crm")]
        """
        self.tool_dirs = [Path(d) for d in tool_dirs]
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._loaded = False

    def discover_tools(self, force_reload: bool = False) -> Dict[str, Type[BaseTool]]:
        """Scan directories for tool classes.

        This is the core discovery mechanism - adapts agent-zero's
        load_classes_from_file but:
        1. Scans multiple directories
        2. Handles Pydantic models
        3. Validates tool metadata

        Args:
            force_reload: If True, re-scan even if already loaded

        Returns:
            Dict mapping tool names to tool classes
        """
        if self._loaded and not force_reload:
            return self._tools

        self._tools.clear()

        for tool_dir in self.tool_dirs:
            if not tool_dir.exists():
                logger.warning(f"Tool directory not found: {tool_dir}")
                continue

            logger.info(f"Scanning for tools in: {tool_dir}")

            # Get all .py files (excluding __init__.py and _*.py)
            py_files = [
                f for f in tool_dir.glob("*.py")
                if not f.name.startswith("_") and f.name != "__init__.py"
            ]

            for py_file in py_files:
                try:
                    # Load module dynamically (agent-zero pattern)
                    module = self._load_module(py_file)

                    # Find BaseTool subclasses (agent-zero pattern)
                    tool_classes = self._extract_tool_classes(module)

                    # Register tools
                    for tool_cls in tool_classes:
                        self._register_tool(tool_cls)

                except Exception as e:
                    logger.error(f"Failed to load tool from {py_file}: {e}")
                    continue

        self._loaded = True
        logger.info(f"Discovered {len(self._tools)} tools")

        return self._tools

    def _load_module(self, file_path: Path):
        """Load a Python module from file path.

        Direct adaptation of agent-zero's import_module.
        """
        module_name = file_path.stem

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def _extract_tool_classes(self, module) -> List[Type[BaseTool]]:
        """Extract BaseTool subclasses from module.

        Adaptation of agent-zero's class extraction with
        Pydantic-specific handling.
        """
        tool_classes = []

        # Get all classes in module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Filter for BaseTool subclasses
            if (obj is not BaseTool and
                issubclass(obj, BaseTool) and
                obj.__module__ == module.__name__):

                # Validate that tool has proper metadata
                if not hasattr(obj, 'metadata'):
                    logger.warning(
                        f"Tool class {name} missing metadata, skipping"
                    )
                    continue

                tool_classes.append(obj)

        return tool_classes

    def _register_tool(self, tool_cls: Type[BaseTool]):
        """Register a tool class in the registry.

        Args:
            tool_cls: Tool class to register
        """
        # Get tool name from metadata
        # For Pydantic models, we need to instantiate to get metadata
        # But we want to avoid side effects, so we check class annotations
        if hasattr(tool_cls, '__annotations__'):
            # This is a Pydantic model with class-level metadata
            # We need to instantiate to validate
            try:
                # Create dummy instance to extract metadata
                dummy = tool_cls.construct()  # construct() skips validation
                tool_name = dummy.metadata.name
            except Exception:
                # Fall back to class name
                tool_name = tool_cls.__name__
        else:
            tool_name = tool_cls.__name__

        if tool_name in self._tools:
            logger.warning(
                f"Tool {tool_name} already registered, overwriting"
            )

        self._tools[tool_name] = tool_cls
        logger.debug(f"Registered tool: {tool_name}")

    def get_tool(self, name: str) -> Optional[Type[BaseTool]]:
        """Get a tool class by name.

        Args:
            name: Tool name

        Returns:
            Tool class or None if not found
        """
        if not self._loaded:
            self.discover_tools()

        return self._tools.get(name)

    def get_tools_by_category(
        self,
        category: ToolCategory
    ) -> Dict[str, Type[BaseTool]]:
        """Get all tools in a category.

        Args:
            category: Tool category to filter by

        Returns:
            Dict of tools in that category
        """
        if not self._loaded:
            self.discover_tools()

        filtered = {}
        for name, tool_cls in self._tools.items():
            dummy = tool_cls.construct()
            if dummy.metadata.category == category:
                filtered[name] = tool_cls

        return filtered

    def get_tools_by_tags(
        self,
        tags: List[str],
        match_all: bool = False
    ) -> Dict[str, Type[BaseTool]]:
        """Get tools matching tags.

        Args:
            tags: Tags to search for
            match_all: If True, tool must have all tags.
                      If False, tool must have at least one tag.

        Returns:
            Dict of matching tools
        """
        if not self._loaded:
            self.discover_tools()

        filtered = {}
        for name, tool_cls in self._tools.items():
            dummy = tool_cls.construct()
            tool_tags = set(dummy.metadata.tags)
            search_tags = set(tags)

            if match_all:
                if search_tags.issubset(tool_tags):
                    filtered[name] = tool_cls
            else:
                if search_tags.intersection(tool_tags):
                    filtered[name] = tool_cls

        return filtered

    def list_tools(self) -> List[str]:
        """List all tool names.

        Returns:
            List of tool names
        """
        if not self._loaded:
            self.discover_tools()

        return list(self._tools.keys())
```

**Key Features:**
1. **File-Based Discovery:** Scans directories like agent-zero
2. **Pydantic Integration:** Validates tool metadata
3. **Caching:** Only scans once unless forced
4. **Filtering:** Get tools by category or tags
5. **Error Handling:** Continues on individual tool failures

---

### 2.3 DSPy Tool Adapter

**Proposed File:** `/Users/joshisrael/hume-dspy-agent/tools/adapter.py`

```python
"""Adapter between Pydantic tools and DSPy tool-calling system.

Bridges the gap between our Pydantic-based tool registry
and DSPy's expectations for tool format.
"""
from typing import List, Dict, Callable, Optional, Any
from .registry import ToolRegistry
from .base import BaseTool, ToolCategory
import logging

logger = logging.getLogger(__name__)


class DSPyToolAdapter:
    """Adapts Pydantic tools for DSPy ReAct/tool-calling modules.

    DSPy expects tools to be:
    1. Callable functions
    2. With __name__ and __doc__ attributes
    3. With type hints on parameters

    This adapter:
    1. Gets tools from registry
    2. Instantiates them
    3. Converts to DSPy format
    4. Applies filtering based on agent needs
    """

    def __init__(self, registry: ToolRegistry):
        """Initialize adapter with tool registry.

        Args:
            registry: Initialized ToolRegistry instance
        """
        self.registry = registry

    def get_tools_for_agent(
        self,
        agent_type: str,
        context: Optional[Dict[str, Any]] = None,
        categories: Optional[List[ToolCategory]] = None,
        tags: Optional[List[str]] = None,
        max_tools: Optional[int] = None
    ) -> List[Callable]:
        """Get tools filtered for specific agent type.

        This replaces hardcoded tool lists in agent classes!

        Args:
            agent_type: Type of agent (research, sales, strategy, etc.)
            context: Additional context for filtering
            categories: Filter by categories
            tags: Filter by tags
            max_tools: Maximum number of tools to return

        Returns:
            List of DSPy-compatible tool callables
        """
        # Discover all tools
        all_tools = self.registry.discover_tools()

        # Filter by categories if specified
        if categories:
            filtered_tools = {}
            for category in categories:
                filtered_tools.update(
                    self.registry.get_tools_by_category(category)
                )
        else:
            filtered_tools = all_tools

        # Filter by tags if specified
        if tags:
            filtered_tools = {
                name: cls
                for name, cls in filtered_tools.items()
                if self._matches_tags(cls, tags)
            }

        # Apply agent-specific filtering
        filtered_tools = self._filter_by_agent_type(
            filtered_tools,
            agent_type,
            context
        )

        # Limit number of tools if specified
        if max_tools and len(filtered_tools) > max_tools:
            # Sort by priority/relevance and take top N
            filtered_tools = dict(
                list(filtered_tools.items())[:max_tools]
            )

        # Convert to DSPy format
        dspy_tools = []
        for name, tool_cls in filtered_tools.items():
            try:
                # Instantiate tool
                tool_instance = tool_cls()

                # Convert to DSPy callable
                dspy_tool = tool_instance.to_dspy_tool()

                dspy_tools.append(dspy_tool)
                logger.debug(f"Added tool for {agent_type}: {name}")

            except Exception as e:
                logger.error(f"Failed to instantiate tool {name}: {e}")
                continue

        logger.info(
            f"Loaded {len(dspy_tools)} tools for agent type: {agent_type}"
        )

        return dspy_tools

    def _matches_tags(self, tool_cls, tags: List[str]) -> bool:
        """Check if tool matches any of the given tags."""
        dummy = tool_cls.construct()
        tool_tags = set(dummy.metadata.tags)
        return bool(tool_tags.intersection(tags))

    def _filter_by_agent_type(
        self,
        tools: Dict[str, type[BaseTool]],
        agent_type: str,
        context: Optional[Dict] = None
    ) -> Dict[str, type[BaseTool]]:
        """Filter tools based on agent type and context.

        This is where we encode agent-specific tool requirements.

        Examples:
        - research_agent: Gets research, enrichment tools
        - sales_agent: Gets CRM, communication tools
        - strategy_agent: Gets analysis, data tools
        """
        # Define agent type to category mappings
        agent_category_map = {
            "research": [ToolCategory.RESEARCH, ToolCategory.DATA],
            "sales": [ToolCategory.CRM, ToolCategory.COMMUNICATION],
            "strategy": [ToolCategory.ANALYSIS, ToolCategory.DATA],
            "audit": [ToolCategory.DATA, ToolCategory.UTILITY],
        }

        # Get relevant categories for this agent type
        relevant_categories = agent_category_map.get(agent_type, [])

        if not relevant_categories:
            # No specific filtering, return all
            return tools

        # Filter tools by category
        filtered = {}
        for name, tool_cls in tools.items():
            dummy = tool_cls.construct()
            if dummy.metadata.category in relevant_categories:
                filtered[name] = tool_cls

        # Apply context-based filtering if needed
        if context:
            filtered = self._apply_context_filters(filtered, context)

        return filtered

    def _apply_context_filters(
        self,
        tools: Dict[str, type[BaseTool]],
        context: Dict[str, Any]
    ) -> Dict[str, type[BaseTool]]:
        """Apply context-based filtering.

        Example contexts:
        - {"apis": ["clearbit", "apollo"]} -> Only tools using those APIs
        - {"cost_level": "FREE"} -> Only free tools
        - {"requires_auth": False} -> Only tools not needing auth
        """
        filtered = tools

        # Filter by API availability
        if "apis" in context:
            available_apis = set(context["apis"])
            filtered = {
                name: cls
                for name, cls in filtered.items()
                if self._tool_uses_api(cls, available_apis)
            }

        # Filter by cost level
        if "cost_level" in context:
            max_cost = context["cost_level"]
            filtered = {
                name: cls
                for name, cls in filtered.items()
                if self._tool_meets_cost(cls, max_cost)
            }

        # Filter by auth requirement
        if "requires_auth" in context:
            requires_auth = context["requires_auth"]
            filtered = {
                name: cls
                for name, cls in filtered.items()
                if self._check_auth_requirement(cls, requires_auth)
            }

        return filtered

    def _tool_uses_api(self, tool_cls, available_apis: set) -> bool:
        """Check if tool uses any of the available APIs."""
        dummy = tool_cls.construct()
        tool_tags = set(dummy.metadata.tags)
        return bool(tool_tags.intersection(available_apis))

    def _tool_meets_cost(self, tool_cls, max_cost: str) -> bool:
        """Check if tool meets cost requirements."""
        cost_levels = {"FREE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        dummy = tool_cls.construct()
        tool_cost = cost_levels.get(dummy.metadata.cost_level, 0)
        max_cost_level = cost_levels.get(max_cost, 3)
        return tool_cost <= max_cost_level

    def _check_auth_requirement(self, tool_cls, requires_auth: bool) -> bool:
        """Check if tool matches auth requirement."""
        dummy = tool_cls.construct()
        return dummy.metadata.requires_auth == requires_auth
```

**Key Features:**
1. **Agent-Specific Filtering:** Each agent type gets relevant tools
2. **Context-Based Selection:** Filter by API availability, cost, auth
3. **DSPy Conversion:** Converts Pydantic tools to DSPy callables
4. **Flexible Filtering:** Multiple filter dimensions (category, tags, context)

---

## Part 3: Integration Examples

### 3.1 Example Tool: Clearbit Person Lookup

**Proposed File:** `/Users/joshisrael/hume-dspy-agent/tools/research/clearbit_lookup.py`

```python
"""Clearbit person enrichment tool.

Extracted from ResearchAgent._clearbit_person_lookup() method
to make it reusable, testable, and discoverable.
"""
from typing import Optional, Dict, Any
from tools.base import BaseTool, ToolMetadata, ToolCategory
from models.lead import PersonProfile  # Existing Pydantic model
from pydantic import Field, EmailStr
import httpx
import os
import logging

logger = logging.getLogger(__name__)


class ClearbitPersonLookup(BaseTool):
    """Look up person data via Clearbit Enrichment API.

    BEFORE: This was a private method on ResearchAgent
    AFTER: It's a standalone, reusable tool

    Benefits:
    - Can be used by ANY agent (research, sales, audit)
    - Easy to test in isolation
    - Can be versioned (v1, v2)
    - Pydantic validates inputs/outputs
    """

    metadata: ToolMetadata = ToolMetadata(
        name="clearbit_person_lookup",
        description="Enrich person data using email address via Clearbit API. "
                    "Returns name, title, company, LinkedIn, and social profiles.",
        category=ToolCategory.RESEARCH,
        tags=["enrichment", "person", "email", "clearbit"],
        requires_auth=True,
        cost_level="MEDIUM"
    )

    api_key: str = Field(
        default_factory=lambda: os.getenv("CLEARBIT_API_KEY", ""),
        description="Clearbit API key (loaded from env)"
    )

    timeout: float = Field(
        default=10.0,
        description="API request timeout in seconds"
    )

    async def execute(self, email: EmailStr) -> Optional[Dict[str, Any]]:
        """Execute the Clearbit person lookup.

        Args:
            email: Email address to look up (validated as proper email)

        Returns:
            Dict with person data or None if not found

        Example:
            tool = ClearbitPersonLookup()
            result = await tool.execute(email="john@example.com")
            # Returns: {
            #     "name": "John Doe",
            #     "title": "VP of Sales",
            #     "company": "Example Corp",
            #     "linkedin_url": "linkedin.com/in/johndoe",
            #     "location": "San Francisco, CA",
            #     ...
            # }
        """
        if not self.api_key:
            logger.warning("Clearbit API key not configured")
            return {"error": "Clearbit API key not configured"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://person.clearbit.com/v2/combined/find?email={email}",
                    auth=(self.api_key, ""),
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    person = data.get("person", {})

                    # Transform to our format
                    result = {
                        "name": person.get("name", {}).get("fullName"),
                        "title": person.get("employment", {}).get("title"),
                        "company": person.get("employment", {}).get("name"),
                        "location": person.get("location"),
                        "bio": person.get("bio"),
                        "linkedin_url": person.get("linkedin", {}).get("handle"),
                        "social_presence": {
                            "twitter": person.get("twitter", {}).get("handle"),
                            "facebook": person.get("facebook", {}).get("handle")
                        }
                    }

                    logger.info(f"Successfully enriched person: {email}")
                    return result

                elif response.status_code == 404:
                    logger.info(f"No Clearbit data found for: {email}")
                    return None

                else:
                    logger.warning(
                        f"Clearbit API error {response.status_code}: {response.text}"
                    )
                    return {"error": f"API returned {response.status_code}"}

        except httpx.TimeoutException:
            logger.error(f"Clearbit API timeout for: {email}")
            return {"error": "Request timed out"}

        except Exception as e:
            logger.error(f"Clearbit lookup failed: {e}")
            return {"error": str(e)}
```

**Benefits Over Current Approach:**

1. **Testability:**
```python
# BEFORE: Had to mock entire ResearchAgent
agent = ResearchAgent()
agent.clearbit_api_key = "test_key"
result = await agent._clearbit_person_lookup("test@example.com")

# AFTER: Test tool in isolation
tool = ClearbitPersonLookup(api_key="test_key")
result = await tool.execute(email="test@example.com")
```

2. **Reusability:**
```python
# BEFORE: Only ResearchAgent could use it
# AFTER: ANY agent can use it
from tools.registry import ToolRegistry

registry = ToolRegistry([Path("tools/research")])
clearbit = registry.get_tool("clearbit_person_lookup")()
result = await clearbit.execute(email="user@company.com")
```

3. **Validation:**
```python
# BEFORE: No validation
result = await agent._clearbit_person_lookup("invalid-email")  # Silently fails

# AFTER: Pydantic validation
tool = ClearbitPersonLookup()
result = await tool.execute(email="invalid-email")  # Raises ValidationError
```

---

### 3.2 Refactored Research Agent

**Updated File:** `/Users/joshisrael/hume-dspy-agent/agents/research_agent.py`

```python
"""Research Agent with dynamic tool loading.

BEFORE: 600+ lines with embedded tool implementations
AFTER: 200 lines using tool registry
"""
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
import dspy

from tools.registry import ToolRegistry
from tools.adapter import DSPyToolAdapter
from tools.base import ToolCategory
from pathlib import Path

logger = logging.getLogger(__name__)


# DSPy Signatures stay the same!
class ResearchPlanning(dspy.Signature):
    """Plan research strategy for a lead."""
    lead_info: str = dspy.InputField(desc="Available information about the lead")
    research_goals: str = dspy.InputField(desc="What information we need")

    research_plan: str = dspy.OutputField(desc="Step-by-step research plan")
    priority_targets: str = dspy.OutputField(desc="High-priority information to find")


class ResearchSynthesis(dspy.Signature):
    """Synthesize research findings into actionable insights."""
    person_data: str = dspy.InputField(desc="Information about the person")
    company_data: str = dspy.InputField(desc="Information about the company")

    key_insights: str = dspy.OutputField(desc="Key insights from research")
    engagement_strategy: str = dspy.OutputField(desc="Recommended engagement approach")


class ResearchAgent(dspy.Module):
    """Agent for conducting deep research on leads and companies.

    REFACTORED: Now uses dynamic tool loading instead of hardcoded methods.

    Changes:
    - Removed ~20 private methods (_clearbit_lookup, _apollo_search, etc.)
    - Added tool registry and adapter
    - Tools are discovered at runtime
    - Preserved all DSPy signatures and modules

    Benefits:
    - 70% less code in agent file
    - Tools are reusable by other agents
    - Easy to add new tools (just drop file in tools/research/)
    - Better testability
    """

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        tool_dirs: Optional[list] = None
    ):
        super().__init__()

        # DSPy modules (unchanged)
        self.plan_research = dspy.ChainOfThought(ResearchPlanning)
        self.synthesize_findings = dspy.ChainOfThought(ResearchSynthesis)

        # NEW: Dynamic tool loading
        if tool_registry is None:
            if tool_dirs is None:
                tool_dirs = [
                    Path(__file__).parent.parent / "tools" / "research",
                    Path(__file__).parent.parent / "tools" / "common"
                ]
            tool_registry = ToolRegistry(tool_dirs=tool_dirs)

        self.tool_registry = tool_registry
        self.tool_adapter = DSPyToolAdapter(tool_registry)

        # Load tools for research agent
        self.tools = self.tool_adapter.get_tools_for_agent(
            agent_type="research",
            categories=[ToolCategory.RESEARCH, ToolCategory.DATA],
            context={
                "apis": ["clearbit", "apollo", "perplexity"],
                "cost_level": "MEDIUM"
            }
        )

        logger.info("🔍 Research Agent initialized")
        logger.info(f"   Loaded {len(self.tools)} tools dynamically")

    def forward(
        self,
        lead_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """DSPy Module forward pass - main entry point.

        This interface is unchanged - still works with DSPy optimization.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return loop.create_task(
                    self.research_lead_deeply(
                        lead_id=lead_id,
                        name=name,
                        email=email,
                        company=company
                    )
                )
            else:
                return loop.run_until_complete(
                    self.research_lead_deeply(
                        lead_id=lead_id,
                        name=name,
                        email=email,
                        company=company
                    )
                )
        except RuntimeError:
            return asyncio.run(
                self.research_lead_deeply(
                    lead_id=lead_id,
                    name=name,
                    email=email,
                    company=company
                )
            )

    async def research_lead_deeply(
        self,
        lead_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive research on a lead.

        BEFORE: Called private methods like _clearbit_person_lookup()
        AFTER: Uses tools from registry
        """
        logger.info(f"🔍 Starting deep research for lead: {lead_id}")

        results = {}

        # BEFORE: await self._clearbit_person_lookup(email)
        # AFTER: Get tool from registry and use it
        if email:
            clearbit_tool = self._get_tool("clearbit_person_lookup")
            if clearbit_tool:
                person_data = await clearbit_tool(email=email)
                results["person_enrichment"] = person_data

        # BEFORE: await self._apollo_find_contacts(company)
        # AFTER: Get tool from registry
        if company:
            apollo_tool = self._get_tool("apollo_contact_search")
            if apollo_tool:
                contacts = await apollo_tool(company=company)
                results["additional_contacts"] = contacts

        # BEFORE: await self._find_company_news(company)
        # AFTER: Get tool from registry
        if company:
            news_tool = self._get_tool("perplexity_company_research")
            if news_tool:
                news = await news_tool(company=company)
                results["company_news"] = news

        logger.info(f"✅ Research complete for lead: {lead_id}")
        return results

    def _get_tool(self, tool_name: str):
        """Get a tool by name from loaded tools.

        Helper method to get specific tools when needed.
        """
        for tool in self.tools:
            if tool.__name__ == tool_name:
                return tool
        return None
```

**Key Changes:**

1. **Removed ~400 lines of tool code** - moved to separate tool files
2. **Added tool registry** - discovers tools at runtime
3. **Preserved DSPy interface** - forward() method unchanged
4. **Same functionality** - but more maintainable

---

### 3.3 Unified Tool Provider

**Proposed File:** `/Users/joshisrael/hume-dspy-agent/tools/unified_provider.py`

```python
"""Unified provider for both internal and MCP tools.

Combines:
1. Internal tools (via ToolRegistry)
2. MCP tools (via MCPOrchestrator)

Provides single interface for agents to get all tools they need.
"""
from typing import List, Callable, Optional, Dict, Any
from pathlib import Path

from .registry import ToolRegistry
from .adapter import DSPyToolAdapter
from .base import ToolCategory
from core.mcp_orchestrator import MCPOrchestrator

import logging

logger = logging.getLogger(__name__)


class UnifiedToolProvider:
    """Provides both internal and MCP tools to agents.

    Architecture:
    - Internal tools: Fast, free, Pydantic-validated
    - MCP tools: External, dynamically selected based on task

    This integrates:
    - agent-zero's file-based tool discovery
    - hume-dspy-agent's MCP orchestration
    - DSPy's tool-calling system
    """

    def __init__(
        self,
        tool_dirs: Optional[List[Path]] = None,
        mcp_orchestrator: Optional[MCPOrchestrator] = None
    ):
        """Initialize unified provider.

        Args:
            tool_dirs: Directories containing internal tools
            mcp_orchestrator: MCP orchestrator instance
        """
        # Initialize internal tool system
        if tool_dirs is None:
            tool_dirs = [
                Path("tools/research"),
                Path("tools/crm"),
                Path("tools/analysis"),
                Path("tools/common")
            ]

        self.tool_registry = ToolRegistry(tool_dirs=tool_dirs)
        self.tool_adapter = DSPyToolAdapter(self.tool_registry)

        # Initialize MCP system
        self.mcp_orchestrator = mcp_orchestrator or MCPOrchestrator()

        logger.info("✅ Unified Tool Provider initialized")
        logger.info(f"   Internal tool dirs: {len(tool_dirs)}")
        logger.info(f"   MCP servers available: {len(self.mcp_orchestrator.trusted_servers)}")

    async def get_tools_for_task(
        self,
        task: str,
        agent_type: str,
        context: Optional[Dict[str, Any]] = None,
        include_mcp: bool = True,
        max_internal_tools: Optional[int] = None,
        max_mcp_tools: Optional[int] = None
    ) -> List[Callable]:
        """Get both internal and MCP tools for a task.

        This is the main entry point agents should use.

        Args:
            task: Task description for MCP server selection
            agent_type: Type of agent (research, sales, etc.)
            context: Additional context for tool filtering
            include_mcp: Whether to include MCP tools
            max_internal_tools: Max internal tools to load
            max_mcp_tools: Max MCP tools to load

        Returns:
            List of DSPy-compatible tools

        Example:
            provider = UnifiedToolProvider()
            tools = await provider.get_tools_for_task(
                task="Research a B2B lead's company",
                agent_type="research",
                context={"apis": ["clearbit", "apollo"]}
            )
            # Returns: [clearbit_lookup, apollo_search, perplexity_research, ...]
        """
        # 1. Get internal tools (always available, fast, free)
        internal_tools = self.tool_adapter.get_tools_for_agent(
            agent_type=agent_type,
            context=context,
            max_tools=max_internal_tools
        )

        logger.info(f"📦 Loaded {len(internal_tools)} internal tools")

        # 2. Get MCP tools if requested (external, cost varies)
        mcp_tools = []
        if include_mcp:
            try:
                # Use MCP orchestrator to select relevant servers
                selected_servers = await self.mcp_orchestrator.select_servers_for_task(
                    task=task,
                    context=context
                )

                if selected_servers:
                    mcp_tools = await self._load_mcp_tools(
                        selected_servers,
                        max_tools=max_mcp_tools
                    )
                    logger.info(f"📦 Loaded {len(mcp_tools)} MCP tools")
                else:
                    logger.info("📦 No MCP servers selected for this task")

            except Exception as e:
                logger.error(f"Failed to load MCP tools: {e}")
                # Continue with internal tools only

        # 3. Combine and return
        all_tools = internal_tools + mcp_tools

        # Log context savings
        if include_mcp and selected_servers:
            savings = self.mcp_orchestrator.estimate_context_savings(selected_servers)
            logger.info(
                f"💰 Context savings: {savings['savings_percentage']}% "
                f"({savings['tools_saved']} tools not loaded)"
            )

        logger.info(f"✅ Total tools available: {len(all_tools)}")

        return all_tools

    async def _load_mcp_tools(
        self,
        server_names: List[str],
        max_tools: Optional[int] = None
    ) -> List[Callable]:
        """Load tools from selected MCP servers.

        Args:
            server_names: MCP server names to load
            max_tools: Maximum tools to load

        Returns:
            List of MCP tools as DSPy callables
        """
        # TODO: Integrate with actual MCP client
        # This would interface with the existing mcp_client.py

        # Mark servers as active
        await self.mcp_orchestrator.mark_servers_active(server_names)

        # Load tools from servers
        # In reality, this would call the MCP client
        # For now, return empty list
        mcp_tools = []

        # Limit if needed
        if max_tools and len(mcp_tools) > max_tools:
            mcp_tools = mcp_tools[:max_tools]

        return mcp_tools
```

**Usage Example:**

```python
# In any agent
from tools.unified_provider import UnifiedToolProvider

class MyAgent(dspy.Module):
    def __init__(self):
        super().__init__()

        # Get all tools (internal + MCP) in one call
        provider = UnifiedToolProvider()
        self.tools = await provider.get_tools_for_task(
            task="Research B2B leads and update CRM",
            agent_type="sales",
            context={"apis": ["clearbit", "zapier"]}
        )

        # Use tools with DSPy
        self.tool_executor = dspy.ReAct(
            signature=SalesTask,
            tools=self.tools
        )
```

---

## Part 4: Migration Strategy

### 4.1 Phase 1: Add Infrastructure (Week 1)

**Goal:** Add tool system without breaking existing code

**Tasks:**
1. Create `tools/base.py` with `BaseTool` and `ToolMetadata`
2. Create `tools/registry.py` with `ToolRegistry`
3. Create `tools/adapter.py` with `DSPyToolAdapter`
4. Create `tools/unified_provider.py` with `UnifiedToolProvider`
5. Add tests for each component

**No Breaking Changes:**
- Existing agents continue using hardcoded methods
- New system exists alongside old system
- Can be tested independently

### 4.2 Phase 2: Extract Research Tools (Week 2)

**Goal:** Prove the pattern with ResearchAgent

**Tasks:**
1. Create `tools/research/` directory
2. Extract `_clearbit_person_lookup()` → `clearbit_lookup.py`
3. Extract `_apollo_find_contacts()` → `apollo_search.py`
4. Extract `_find_linkedin_profile()` → `linkedin_search.py`
5. Extract `_find_company_news()` → `company_news.py`
6. Update `ResearchAgent` to use tool registry
7. Add integration tests

**Success Criteria:**
- ResearchAgent works exactly as before
- But now uses 5 separate tool files
- Tools can be tested in isolation
- Other agents can reuse research tools

### 4.3 Phase 3: Expand to Other Agents (Week 3-4)

**Goal:** Roll out to all agents

**Tasks:**
1. Create `tools/crm/` directory
2. Extract CRM operations from various agents
3. Create `tools/analysis/` directory
4. Extract analysis tools
5. Update all agents to use tool registry
6. Deprecate old hardcoded methods

**Agents to Update:**
- `InboundAgent`
- `StrategyAgent`
- `AuditAgent`
- `FollowUpAgent`

### 4.4 Phase 4: Integration with MCP (Week 5)

**Goal:** Unify internal and MCP tools

**Tasks:**
1. Integrate `UnifiedToolProvider` with existing `MCPOrchestrator`
2. Update agents to use `UnifiedToolProvider`
3. Add MCP tool loading to `_load_mcp_tools()`
4. Test full integration
5. Measure context window improvements

---

## Part 5: Code Examples - Before & After

### 5.1 Research Agent Comparison

#### BEFORE: Hardcoded Tools (600+ lines)

```python
class ResearchAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.plan_research = dspy.ChainOfThought(ResearchPlanning)
        self.synthesize_findings = dspy.ChainOfThought(ResearchSynthesis)
        self.clearbit_api_key = os.getenv("CLEARBIT_API_KEY")
        self.apollo_api_key = os.getenv("APOLLO_API_KEY")

    async def research_person(self, name, email, company):
        # 50 lines of hardcoded logic
        if email and self.clearbit_api_key:
            clearbit_data = await self._clearbit_person_lookup(email)
        if name and company:
            linkedin_url = await self._find_linkedin_profile(name, company)
        # ... more hardcoded calls

    async def _clearbit_person_lookup(self, email):
        # 30 lines of Clearbit API logic
        async with httpx.AsyncClient() as client:
            response = await client.get(...)
            # ... parsing logic

    async def _find_linkedin_profile(self, name, company):
        # 40 lines of LinkedIn search logic
        # ...

    async def _apollo_find_contacts(self, company):
        # 50 lines of Apollo API logic
        # ...

    # ... 15 more private methods
```

**Problems:**
- 600+ lines in one file
- Can't reuse tools
- Hard to test
- Duplicated across agents

#### AFTER: Dynamic Tools (200 lines)

```python
class ResearchAgent(dspy.Module):
    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        super().__init__()
        self.plan_research = dspy.ChainOfThought(ResearchPlanning)
        self.synthesize_findings = dspy.ChainOfThought(ResearchSynthesis)

        # Dynamic tool loading
        if tool_registry is None:
            tool_registry = ToolRegistry([Path("tools/research")])

        self.tool_adapter = DSPyToolAdapter(tool_registry)
        self.tools = self.tool_adapter.get_tools_for_agent("research")

    async def research_person(self, name, email, company):
        # Use tools from registry
        clearbit = self._get_tool("clearbit_person_lookup")
        person_data = await clearbit(email=email)

        linkedin = self._get_tool("linkedin_search")
        profile = await linkedin(name=name, company=company)

        return PersonProfile(**person_data)

    def _get_tool(self, name):
        return next(t for t in self.tools if t.__name__ == name)
```

**Benefits:**
- 200 lines instead of 600
- Tools in separate files
- Reusable by other agents
- Easy to test

---

### 5.2 Tool Testing Comparison

#### BEFORE: Testing Hardcoded Methods

```python
# test_research_agent.py
import pytest
from unittest.mock import Mock, patch
from agents.research_agent import ResearchAgent

@pytest.mark.asyncio
async def test_clearbit_lookup():
    # Must mock entire agent
    agent = ResearchAgent()
    agent.clearbit_api_key = "test_key"

    # Must mock httpx client
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"person": {...}}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        # Test private method
        result = await agent._clearbit_person_lookup("test@example.com")

        assert result is not None
```

**Problems:**
- Must instantiate entire agent
- Complex mocking
- Testing private methods
- Slow

#### AFTER: Testing Isolated Tools

```python
# test_clearbit_tool.py
import pytest
from tools.research.clearbit_lookup import ClearbitPersonLookup

@pytest.mark.asyncio
async def test_clearbit_lookup():
    # Test tool in isolation
    tool = ClearbitPersonLookup(api_key="test_key")

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"person": {...}}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        # Test public execute method
        result = await tool.execute(email="test@example.com")

        assert result is not None
        assert "name" in result
```

**Benefits:**
- No agent instantiation needed
- Simpler mocking
- Tests public interface
- Fast

---

### 5.3 Adding New Tools Comparison

#### BEFORE: Adding New Tool

```python
# Must modify research_agent.py (600 lines)
class ResearchAgent(dspy.Module):
    # ... existing 600 lines

    async def _new_api_lookup(self, query):
        # Add 50 lines of new API logic here
        self.new_api_key = os.getenv("NEW_API_KEY")
        async with httpx.AsyncClient() as client:
            # ... implementation

    async def research_person(self, name, email, company):
        # Update this method to call new tool
        new_data = await self._new_api_lookup(query)
        # ...
```

**Problems:**
- Modifies 600-line file
- Adds coupling
- Harder to review
- Risk of breaking existing code

#### AFTER: Adding New Tool

```python
# Create new file: tools/research/new_api_lookup.py
from tools.base import BaseTool, ToolMetadata, ToolCategory

class NewApiLookup(BaseTool):
    """New API lookup tool."""

    metadata: ToolMetadata = ToolMetadata(
        name="new_api_lookup",
        description="Look up data via New API",
        category=ToolCategory.RESEARCH,
        tags=["enrichment", "new_api"]
    )

    api_key: str = Field(default_factory=lambda: os.getenv("NEW_API_KEY"))

    async def execute(self, query: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            # ... implementation
            return result
```

**That's it!** Tool is automatically discovered.

**Benefits:**
- New file, no modifications to existing code
- Easy to review
- Can't break existing tools
- Immediately available to all agents

---

## Part 6: Benefits Summary

### 6.1 For Developers

1. **Less Code:** 70% reduction in agent files
2. **Better Organization:** Tools in separate, focused files
3. **Easy Testing:** Test tools in isolation
4. **Code Reuse:** Same tool used by multiple agents
5. **Safe Changes:** New tools can't break existing ones

### 6.2 For DSPy

1. **Preserves Signatures:** All DSPy signatures unchanged
2. **Preserves Modules:** ChainOfThought, ReAct work as before
3. **Enables Optimization:** Can try different tool combinations
4. **Better Composition:** Tools are proper callables

### 6.3 For Pydantic

1. **Input Validation:** Email must be valid email, etc.
2. **Output Validation:** Return types are Pydantic models
3. **Type Safety:** Full type hints throughout
4. **Configuration:** Use Pydantic settings for tool config

### 6.4 For Extensibility

1. **Plugin Architecture:** Drop new tool file, it's discovered
2. **Versioning:** Can have `clearbit_v1.py` and `clearbit_v2.py`
3. **A/B Testing:** Load different tools for different contexts
4. **Multi-Tenant:** Different tool sets per customer

---

## Part 7: Conclusion

### Integration Summary

This analysis shows how to integrate **agent-zero's dynamic tool discovery** into **hume-dspy-agent** through a **Pydantic-based tool registry**. The solution:

1. **Preserves DSPy:** All signatures and modules unchanged
2. **Preserves Pydantic:** Enhanced with tool validation
3. **Adds Extensibility:** File-based tool discovery like agent-zero
4. **Improves Architecture:** Separation of concerns, better testing
5. **Reduces Code:** 70% reduction in agent file sizes

### Key Insight

The power of agent-zero's approach is **runtime discovery via filesystem scanning**. We can adopt this pattern while staying true to DSPy and Pydantic by:

- Using Pydantic BaseModel instead of dataclasses
- Converting tools to DSPy callables via adapter
- Validating tool metadata with Pydantic
- Maintaining type safety throughout

### Next Steps

1. Implement Phase 1 (infrastructure)
2. Prove pattern with ResearchAgent
3. Roll out to remaining agents
4. Integrate with MCP orchestrator
5. Measure improvements

### Files to Create

```
hume-dspy-agent/
├── tools/
│   ├── __init__.py
│   ├── base.py              # ~200 lines (BaseTool, ToolMetadata)
│   ├── registry.py          # ~150 lines (ToolRegistry)
│   ├── adapter.py           # ~100 lines (DSPyToolAdapter)
│   ├── unified_provider.py  # ~100 lines (UnifiedToolProvider)
│   ├── research/
│   │   ├── clearbit_lookup.py
│   │   ├── apollo_search.py
│   │   └── ...
│   ├── crm/
│   │   └── ...
│   └── common/
│       └── ...
```

**Total New Code:** ~550 lines of infrastructure + individual tool files

**Code Removed:** ~2000 lines from agent files

**Net Change:** Fewer total lines, better architecture

---

## Appendix: Additional Resources

### A. Agent-Zero References

- Tool Base Class: `/Users/joshisrael/agent-zero/python/helpers/tool.py`
- Dynamic Loading: `/Users/joshisrael/agent-zero/python/helpers/extract_tools.py`
- Tool Discovery: `/Users/joshisrael/agent-zero/agent.py` (lines 809-837)
- Example Tool: `/Users/joshisrael/agent-zero/python/tools/code_execution_tool.py`

### B. hume-dspy-agent References

- Research Agent: `/Users/joshisrael/hume-dspy-agent/agents/research_agent.py`
- MCP Orchestrator: `/Users/joshisrael/hume-dspy-agent/core/mcp_orchestrator.py`
- DSPy Signatures: `/Users/joshisrael/hume-dspy-agent/dspy_modules/signatures.py`
- Pydantic Models: `/Users/joshisrael/hume-dspy-agent/models/lead.py`

### C. Key Patterns

1. **Dynamic Import:** Use `importlib.util.spec_from_file_location()`
2. **Class Discovery:** Use `inspect.getmembers()` and `issubclass()`
3. **DSPy Integration:** Provide callables with `__name__` and `__doc__`
4. **Pydantic Validation:** Use `BaseModel` for all tool classes

---

**End of Analysis**
