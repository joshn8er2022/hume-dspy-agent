# Pydantic Tool System Design
## Dynamic, Type-Safe Tool Loading for Agent-Zero & DSPy

**Author**: Claude (Sonnet 4.5)
**Date**: 2025-10-30
**Version**: 1.0

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Pydantic Base Models](#pydantic-base-models)
3. [Discovery & Registration System](#discovery--registration-system)
4. [DSPy ReAct Integration](#dspy-react-integration)
5. [Example Implementations](#example-implementations)
6. [Migration Guide](#migration-guide)
7. [Advanced Features](#advanced-features)

---

## Architecture Overview

### Design Principles
1. **Type Safety First**: Pydantic validation at every layer
2. **Zero Configuration**: Tools discovered automatically via scanning
3. **Multiple Paradigms**: Support decorator, class-based, and functional patterns
4. **DSPy Native**: First-class integration with DSPy ReAct
5. **Backward Compatible**: Works alongside agent-zero's existing Tool class

### System Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: DSPy Integration                                   │
│ ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ DSPyBridge  │  │ ReActAdapter │  │ ToolFormatter│       │
│ └─────────────┘  └──────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Registration & Discovery                           │
│ ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ToolRegistry │  │ @tool decorator│ │ ToolDiscovery│       │
│ └─────────────┘  └──────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Execution & Validation                             │
│ ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ToolExecutor │  │ Validators   │  │ ErrorHandler │       │
│ └─────────────┘  └──────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Core Pydantic Models                               │
│ ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ToolParameter│  │ ToolDefinition│ │ ToolResult   │       │
│ │ToolMetadata │  │ BaseTool     │  │ ToolError    │       │
│ └─────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## Pydantic Base Models

### 1. Core Models (`models.py`)

```python
"""
Pydantic models for type-safe tool definitions.

This module provides the core data models for the dynamic tool system,
ensuring type safety and validation at every layer.
"""
from typing import Any, Optional, Dict, List, Callable, Literal, Union
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import time
from datetime import datetime


class ParameterType(str, Enum):
    """Supported parameter types for tools."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"


class ToolCategory(str, Enum):
    """Tool categories for organization and discovery."""
    DATA = "data"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    SYSTEM = "system"
    CUSTOM = "custom"


class ToolParameter(BaseModel):
    """
    Definition of a tool parameter with full type information.

    Examples:
        >>> param = ToolParameter(
        ...     name="query",
        ...     type=ParameterType.STRING,
        ...     description="Search query",
        ...     required=True
        ... )
    """
    name: str = Field(..., description="Parameter name")
    type: ParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    validation_rules: Optional[Dict[str, Any]] = Field(
        None,
        description="Pydantic validation rules (min, max, pattern, etc.)"
    )
    examples: List[Any] = Field(default_factory=list, description="Example values")

    @validator('validation_rules')
    def validate_rules(cls, v, values):
        """Ensure validation rules match parameter type."""
        if not v:
            return v

        param_type = values.get('type')
        if param_type == ParameterType.STRING:
            allowed_rules = {'min_length', 'max_length', 'pattern', 'regex'}
        elif param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            allowed_rules = {'ge', 'gt', 'le', 'lt', 'multiple_of'}
        elif param_type == ParameterType.ARRAY:
            allowed_rules = {'min_items', 'max_items', 'unique_items'}
        else:
            allowed_rules = set()

        invalid_rules = set(v.keys()) - allowed_rules
        if invalid_rules:
            raise ValueError(f"Invalid validation rules for {param_type}: {invalid_rules}")

        return v


class ToolMetadata(BaseModel):
    """
    Metadata describing a tool's purpose and characteristics.

    Examples:
        >>> metadata = ToolMetadata(
        ...     name="web_search",
        ...     description="Search the web using DuckDuckGo",
        ...     category=ToolCategory.RESEARCH,
        ...     version="1.0.0"
        ... )
    """
    name: str = Field(..., description="Tool name (unique identifier)")
    description: str = Field(..., description="Tool description")
    category: ToolCategory = Field(..., description="Tool category")
    version: str = Field(default="1.0.0", description="Tool version")
    author: Optional[str] = Field(None, description="Tool author")
    examples: List[str] = Field(default_factory=list, description="Usage examples")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    requires_auth: bool = Field(default=False, description="Requires authentication")
    rate_limit: Optional[int] = Field(None, description="Max calls per minute")
    timeout: int = Field(default=30, description="Execution timeout (seconds)")
    deprecated: bool = Field(default=False, description="Whether tool is deprecated")
    replacement: Optional[str] = Field(None, description="Replacement tool if deprecated")

    @validator('name')
    def validate_name(cls, v):
        """Ensure tool name is valid identifier."""
        if not v.replace('_', '').isalnum():
            raise ValueError(f"Tool name must be alphanumeric with underscores: {v}")
        return v


class ToolError(BaseModel):
    """
    Structured error information from tool execution.

    Examples:
        >>> error = ToolError(
        ...     error_type="ValidationError",
        ...     message="Invalid parameter: query cannot be empty",
        ...     recoverable=True
        ... )
    """
    error_type: str = Field(..., description="Error type/class name")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    recoverable: bool = Field(default=False, description="Whether error is recoverable")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")


class ToolResult(BaseModel):
    """
    Result of tool execution with metadata.

    Examples:
        >>> result = ToolResult(
        ...     success=True,
        ...     data={"results": [...]},
        ...     execution_time=1.23
        ... )
    """
    success: bool = Field(..., description="Whether execution succeeded")
    data: Optional[Any] = Field(None, description="Result data (if success)")
    error: Optional[ToolError] = Field(None, description="Error info (if failure)")
    execution_time: float = Field(..., description="Execution time in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @root_validator
    def validate_result(cls, values):
        """Ensure either data or error is present, not both."""
        success = values.get('success')
        data = values.get('data')
        error = values.get('error')

        if success and error:
            raise ValueError("Cannot have error when success=True")
        if not success and not error:
            raise ValueError("Must have error when success=False")

        return values

    def to_json_string(self) -> str:
        """Convert result to JSON string for DSPy ReAct."""
        import json
        return json.dumps({
            "success": self.success,
            "data": self.data,
            "error": self.error.dict() if self.error else None,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }, indent=2)


class ToolDefinition(BaseModel):
    """
    Complete tool definition including metadata, parameters, and executor.

    Examples:
        >>> tool_def = ToolDefinition(
        ...     metadata=ToolMetadata(name="search", ...),
        ...     parameters=[ToolParameter(name="query", ...)],
        ...     executor=search_function
        ... )
    """
    metadata: ToolMetadata = Field(..., description="Tool metadata")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    executor: Callable = Field(..., description="Execution function (async or sync)")
    before_execution: Optional[Callable] = Field(None, description="Pre-execution hook")
    after_execution: Optional[Callable] = Field(None, description="Post-execution hook")

    class Config:
        arbitrary_types_allowed = True  # Allow Callable type

    @validator('parameters')
    def validate_unique_params(cls, v):
        """Ensure parameter names are unique."""
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError("Parameter names must be unique")
        return v

    def get_parameter_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for parameters (for DSPy/OpenAI function calling)."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param in self.parameters:
            schema["properties"][param.name] = {
                "type": param.type.value,
                "description": param.description
            }

            # Add validation rules
            if param.validation_rules:
                schema["properties"][param.name].update(param.validation_rules)

            # Add examples
            if param.examples:
                schema["properties"][param.name]["examples"] = param.examples

            # Add default
            if param.default is not None:
                schema["properties"][param.name]["default"] = param.default

            # Mark as required
            if param.required:
                schema["required"].append(param.name)

        return schema
```

### 2. Base Tool Class (`base.py`)

```python
"""
Base class for tool implementations.

Provides a class-based alternative to decorator pattern,
compatible with agent-zero's Tool class structure.
"""
from typing import Any, Dict, Optional, Type
from abc import ABC, abstractmethod
from pydantic import BaseModel
import asyncio
import time

from .models import (
    ToolDefinition, ToolMetadata, ToolParameter,
    ToolResult, ToolError, ToolCategory
)


class BaseTool(ABC):
    """
    Base class for tool implementations.

    Subclasses must define:
    - metadata: ToolMetadata class attribute
    - Parameters: Pydantic BaseModel for parameters
    - execute(): Async method that implements tool logic

    Examples:
        >>> class SearchTool(BaseTool):
        ...     metadata = ToolMetadata(name="search", ...)
        ...
        ...     class Parameters(BaseModel):
        ...         query: str
        ...         limit: int = 10
        ...
        ...     async def execute(self, params: Parameters) -> ToolResult:
        ...         results = await do_search(params.query, params.limit)
        ...         return ToolResult(
        ...             success=True,
        ...             data=results,
        ...             execution_time=0.5
        ...         )
    """

    # Must be defined by subclass
    metadata: ToolMetadata
    Parameters: Type[BaseModel]

    def __init__(self):
        """Initialize tool and validate metadata."""
        if not hasattr(self, 'metadata'):
            raise NotImplementedError("Tool must define 'metadata' class attribute")
        if not hasattr(self, 'Parameters'):
            raise NotImplementedError("Tool must define 'Parameters' BaseModel")

    @abstractmethod
    async def execute(self, params: BaseModel) -> ToolResult:
        """
        Execute the tool with validated parameters.

        Args:
            params: Validated parameters (instance of self.Parameters)

        Returns:
            ToolResult with execution results
        """
        pass

    async def before_execution(self, params: BaseModel) -> None:
        """
        Hook called before execute(). Override for pre-execution logic.

        Args:
            params: Validated parameters
        """
        pass

    async def after_execution(self, result: ToolResult, params: BaseModel) -> None:
        """
        Hook called after execute(). Override for post-execution logic.

        Args:
            result: Execution result
            params: Parameters used
        """
        pass

    async def run(self, **kwargs) -> ToolResult:
        """
        Main entry point - validates parameters and executes tool.

        Args:
            **kwargs: Raw parameters to validate

        Returns:
            ToolResult with execution results
        """
        start_time = time.time()

        try:
            # Validate parameters using Pydantic
            params = self.Parameters(**kwargs)

            # Run before hook
            await self.before_execution(params)

            # Execute tool
            result = await self.execute(params)

            # Ensure execution_time is set
            if result.execution_time == 0:
                result.execution_time = time.time() - start_time

            # Run after hook
            await self.after_execution(result, params)

            return result

        except Exception as e:
            # Wrap exceptions in ToolError
            execution_time = time.time() - start_time
            return ToolResult(
                success=False,
                error=ToolError(
                    error_type=type(e).__name__,
                    message=str(e),
                    stack_trace=self._get_stack_trace(),
                    recoverable=False
                ),
                execution_time=execution_time
            )

    def _get_stack_trace(self) -> str:
        """Get current stack trace."""
        import traceback
        return traceback.format_exc()

    def to_tool_definition(self) -> ToolDefinition:
        """
        Convert BaseTool instance to ToolDefinition for registry.

        Returns:
            ToolDefinition with metadata and parameters
        """
        # Extract parameters from Pydantic model
        parameters = []
        for field_name, field in self.Parameters.__fields__.items():
            param = ToolParameter(
                name=field_name,
                type=self._map_python_type_to_param_type(field.type_),
                description=field.field_info.description or "",
                required=field.required,
                default=field.default if not field.required else None
            )
            parameters.append(param)

        return ToolDefinition(
            metadata=self.metadata,
            parameters=parameters,
            executor=self.run,
            before_execution=self.before_execution,
            after_execution=self.after_execution
        )

    @staticmethod
    def _map_python_type_to_param_type(python_type) -> str:
        """Map Python type hints to ParameterType."""
        from .models import ParameterType

        type_mapping = {
            str: ParameterType.STRING,
            int: ParameterType.INTEGER,
            float: ParameterType.FLOAT,
            bool: ParameterType.BOOLEAN,
            list: ParameterType.ARRAY,
            dict: ParameterType.OBJECT,
        }

        return type_mapping.get(python_type, ParameterType.ANY)
```

---

## Discovery & Registration System

### 3. Tool Registry (`registry.py`)

```python
"""
Central registry for tool discovery and management.

The ToolRegistry provides a singleton pattern for registering,
discovering, and retrieving tools throughout the application.
"""
from typing import Dict, List, Optional, Callable, Union
from pathlib import Path
import logging

from .models import ToolDefinition, ToolMetadata, ToolCategory
from .base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Singleton registry for all tools.

    Features:
    - Register tools via decorator, class, or manual
    - Auto-discovery via directory scanning
    - Query tools by name, category, or tag
    - Generate DSPy-compatible tool lists

    Examples:
        >>> registry = ToolRegistry()
        >>> registry.register_tool(tool_def)
        >>> tools = registry.get_all_tools()
        >>> dspy_tools = registry.get_dspy_tools()
    """

    _instance = None
    _tools: Dict[str, ToolDefinition] = {}

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register_tool(
        self,
        tool: Union[ToolDefinition, BaseTool],
        replace: bool = False
    ) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: ToolDefinition or BaseTool instance
            replace: Whether to replace existing tool with same name

        Raises:
            ValueError: If tool already exists and replace=False
        """
        # Convert BaseTool to ToolDefinition
        if isinstance(tool, BaseTool):
            tool = tool.to_tool_definition()

        tool_name = tool.metadata.name

        # Check for duplicates
        if tool_name in self._tools and not replace:
            raise ValueError(
                f"Tool '{tool_name}' already registered. "
                f"Use replace=True to override."
            )

        # Validate tool definition
        self._validate_tool(tool)

        # Register
        self._tools[tool_name] = tool
        logger.info(f"Registered tool: {tool_name} (v{tool.metadata.version})")

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool by name.

        Args:
            name: Tool name

        Returns:
            True if tool was unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            ToolDefinition if found, None otherwise
        """
        return self._tools.get(name)

    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """
        Get all tools in a category.

        Args:
            category: ToolCategory enum

        Returns:
            List of ToolDefinitions
        """
        return [
            tool for tool in self._tools.values()
            if tool.metadata.category == category
        ]

    def get_tools_by_tag(self, tag: str) -> List[ToolDefinition]:
        """
        Get all tools with a specific tag.

        Args:
            tag: Tag string

        Returns:
            List of ToolDefinitions
        """
        return [
            tool for tool in self._tools.values()
            if tag in tool.metadata.tags
        ]

    def search_tools(self, query: str) -> List[ToolDefinition]:
        """
        Search tools by name, description, or tags.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching ToolDefinitions
        """
        query_lower = query.lower()
        results = []

        for tool in self._tools.values():
            # Search in name
            if query_lower in tool.metadata.name.lower():
                results.append(tool)
                continue

            # Search in description
            if query_lower in tool.metadata.description.lower():
                results.append(tool)
                continue

            # Search in tags
            if any(query_lower in tag.lower() for tag in tool.metadata.tags):
                results.append(tool)
                continue

        return results

    def list_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return list(self._tools.keys())

    def count_tools(self) -> int:
        """Get total number of registered tools."""
        return len(self._tools)

    def clear(self) -> None:
        """Clear all registered tools (useful for testing)."""
        self._tools.clear()
        logger.info("Cleared all tools from registry")

    def _validate_tool(self, tool: ToolDefinition) -> None:
        """
        Validate tool definition.

        Args:
            tool: ToolDefinition to validate

        Raises:
            ValueError: If tool is invalid
        """
        # Check required fields
        if not tool.metadata.name:
            raise ValueError("Tool must have a name")

        if not tool.metadata.description:
            raise ValueError("Tool must have a description")

        if not tool.executor:
            raise ValueError("Tool must have an executor function")

        # Check executor is callable
        if not callable(tool.executor):
            raise ValueError("Tool executor must be callable")

        # Validate parameters
        param_names = [p.name for p in tool.parameters]
        if len(param_names) != len(set(param_names)):
            raise ValueError("Tool parameters must have unique names")


# Global registry instance
_global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _global_registry
```

### 4. Decorator Pattern (`decorators.py`)

```python
"""
Decorator for easy tool registration.

Provides @tool decorator that auto-registers functions as tools.
"""
from typing import Optional, List, Callable, Any
from functools import wraps
import inspect
import asyncio

from .models import (
    ToolDefinition, ToolMetadata, ToolParameter,
    ToolCategory, ParameterType, ToolResult, ToolError
)
from .registry import get_global_registry
import time


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: ToolCategory = ToolCategory.CUSTOM,
    version: str = "1.0.0",
    examples: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    timeout: int = 30,
    auto_register: bool = True
) -> Callable:
    """
    Decorator to register a function as a tool.

    The decorator:
    1. Extracts parameter info from function signature
    2. Creates ToolDefinition with metadata
    3. Auto-registers with global registry
    4. Wraps function with validation and error handling

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to docstring)
        category: Tool category
        version: Tool version
        examples: Usage examples
        tags: Searchable tags
        timeout: Execution timeout in seconds
        auto_register: Whether to auto-register with global registry

    Examples:
        >>> @tool(name="search", category=ToolCategory.RESEARCH)
        ... async def search_web(query: str, limit: int = 10) -> ToolResult:
        ...     '''Search the web using DuckDuckGo.'''
        ...     results = await search_api(query, limit)
        ...     return ToolResult(success=True, data=results, execution_time=0.5)
    """
    def decorator(func: Callable) -> Callable:
        # Extract metadata
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or "No description provided"
        tool_examples = examples or []
        tool_tags = tags or []

        # Extract parameters from function signature
        parameters = _extract_parameters(func)

        # Create metadata
        metadata = ToolMetadata(
            name=tool_name,
            description=tool_description.strip(),
            category=category,
            version=version,
            examples=tool_examples,
            tags=tool_tags,
            timeout=timeout
        )

        # Wrap function with validation and error handling
        @wraps(func)
        async def wrapper(**kwargs) -> ToolResult:
            start_time = time.time()

            try:
                # Validate parameters
                validated_params = _validate_parameters(parameters, kwargs)

                # Execute function (handle both async and sync)
                if asyncio.iscoroutinefunction(func):
                    result = await func(**validated_params)
                else:
                    result = func(**validated_params)

                # If function returns ToolResult, use it
                if isinstance(result, ToolResult):
                    if result.execution_time == 0:
                        result.execution_time = time.time() - start_time
                    return result

                # Otherwise, wrap result in ToolResult
                return ToolResult(
                    success=True,
                    data=result,
                    execution_time=time.time() - start_time
                )

            except Exception as e:
                # Wrap exceptions in ToolError
                execution_time = time.time() - start_time
                return ToolResult(
                    success=False,
                    error=ToolError(
                        error_type=type(e).__name__,
                        message=str(e),
                        stack_trace=_get_stack_trace(),
                        recoverable=False
                    ),
                    execution_time=execution_time
                )

        # Create ToolDefinition
        tool_def = ToolDefinition(
            metadata=metadata,
            parameters=parameters,
            executor=wrapper
        )

        # Auto-register if enabled
        if auto_register:
            registry = get_global_registry()
            registry.register_tool(tool_def, replace=True)

        # Attach ToolDefinition to function for introspection
        wrapper._tool_definition = tool_def

        return wrapper

    return decorator


def _extract_parameters(func: Callable) -> List[ToolParameter]:
    """
    Extract parameters from function signature.

    Args:
        func: Function to extract parameters from

    Returns:
        List of ToolParameter objects
    """
    sig = inspect.signature(func)
    parameters = []

    for param_name, param in sig.parameters.items():
        # Skip self/cls
        if param_name in ('self', 'cls'):
            continue

        # Extract type hint
        param_type = ParameterType.ANY
        if param.annotation != inspect.Parameter.empty:
            param_type = _map_type_hint(param.annotation)

        # Extract default value
        has_default = param.default != inspect.Parameter.empty
        default_value = param.default if has_default else None

        # Create ToolParameter
        tool_param = ToolParameter(
            name=param_name,
            type=param_type,
            description=f"Parameter: {param_name}",  # TODO: Extract from docstring
            required=not has_default,
            default=default_value
        )
        parameters.append(tool_param)

    return parameters


def _map_type_hint(type_hint: Any) -> ParameterType:
    """Map Python type hint to ParameterType."""
    # Handle Optional types
    if hasattr(type_hint, '__origin__'):
        if type_hint.__origin__ is Union:
            # Get non-None type from Union
            args = [arg for arg in type_hint.__args__ if arg is not type(None)]
            if args:
                type_hint = args[0]

    type_mapping = {
        str: ParameterType.STRING,
        int: ParameterType.INTEGER,
        float: ParameterType.FLOAT,
        bool: ParameterType.BOOLEAN,
        list: ParameterType.ARRAY,
        dict: ParameterType.OBJECT,
    }

    return type_mapping.get(type_hint, ParameterType.ANY)


def _validate_parameters(
    parameters: List[ToolParameter],
    kwargs: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate provided parameters against parameter definitions.

    Args:
        parameters: List of ToolParameter definitions
        kwargs: Provided keyword arguments

    Returns:
        Validated parameters dictionary

    Raises:
        ValueError: If validation fails
    """
    validated = {}

    for param in parameters:
        value = kwargs.get(param.name)

        # Check required parameters
        if param.required and value is None:
            raise ValueError(f"Missing required parameter: {param.name}")

        # Use default if not provided
        if value is None and param.default is not None:
            value = param.default

        # Type validation (basic)
        if value is not None:
            expected_type = _param_type_to_python_type(param.type)
            if expected_type and not isinstance(value, expected_type):
                try:
                    # Try to coerce type
                    value = expected_type(value)
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Parameter '{param.name}' must be {param.type}, "
                        f"got {type(value).__name__}"
                    )

        validated[param.name] = value

    return validated


def _param_type_to_python_type(param_type: ParameterType) -> Optional[type]:
    """Map ParameterType to Python type."""
    type_mapping = {
        ParameterType.STRING: str,
        ParameterType.INTEGER: int,
        ParameterType.FLOAT: float,
        ParameterType.BOOLEAN: bool,
        ParameterType.ARRAY: list,
        ParameterType.OBJECT: dict,
    }
    return type_mapping.get(param_type)


def _get_stack_trace() -> str:
    """Get current stack trace."""
    import traceback
    return traceback.format_exc()
```

### 5. Directory Discovery (`discovery.py`)

```python
"""
Automatic tool discovery via directory scanning.

Scans specified directories for tool modules and auto-registers them.
"""
from pathlib import Path
import importlib.util
import sys
from typing import List, Optional
import logging

from .registry import get_global_registry
from .base import BaseTool

logger = logging.getLogger(__name__)


class ToolDiscovery:
    """
    Discovers and loads tools from directories.

    Features:
    - Scans directories for Python modules
    - Auto-imports modules with tools
    - Registers discovered tools
    - Supports filtering by prefix/suffix

    Examples:
        >>> discovery = ToolDiscovery()
        >>> discovery.discover_tools("./tools")
        >>> # All tools in ./tools/*.py are now registered
    """

    def __init__(self, registry=None):
        """
        Initialize discovery system.

        Args:
            registry: ToolRegistry to use (defaults to global)
        """
        self.registry = registry or get_global_registry()

    def discover_tools(
        self,
        directory: str,
        pattern: str = "*.py",
        recursive: bool = True,
        prefix: Optional[str] = None,
        exclude: Optional[List[str]] = None
    ) -> int:
        """
        Discover and register tools from a directory.

        Args:
            directory: Directory to scan
            pattern: File pattern to match (default: "*.py")
            recursive: Whether to scan subdirectories
            prefix: Only load modules with this prefix
            exclude: List of filenames to exclude

        Returns:
            Number of tools registered

        Examples:
            >>> discovery = ToolDiscovery()
            >>> count = discovery.discover_tools(
            ...     "./python/tools",
            ...     prefix="tool_",
            ...     exclude=["__init__.py"]
            ... )
            >>> print(f"Registered {count} tools")
        """
        directory_path = Path(directory)
        if not directory_path.exists():
            logger.warning(f"Directory not found: {directory}")
            return 0

        exclude = exclude or []
        exclude.extend(['__init__.py', '__pycache__'])

        # Find matching files
        if recursive:
            files = list(directory_path.rglob(pattern))
        else:
            files = list(directory_path.glob(pattern))

        # Filter files
        files = [
            f for f in files
            if f.name not in exclude
            and (not prefix or f.stem.startswith(prefix))
        ]

        initial_count = self.registry.count_tools()

        # Import each module
        for file_path in files:
            try:
                self._import_tool_module(file_path)
            except Exception as e:
                logger.error(f"Error loading tool from {file_path}: {e}")

        final_count = self.registry.count_tools()
        registered = final_count - initial_count

        logger.info(f"Discovered {registered} tools from {directory}")
        return registered

    def _import_tool_module(self, file_path: Path) -> None:
        """
        Import a tool module and register any tools found.

        Args:
            file_path: Path to Python module
        """
        # Create module name from file path
        module_name = f"dynamic_tools.{file_path.stem}"

        # Load module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Look for BaseTool subclasses
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # Check if it's a BaseTool subclass (not BaseTool itself)
                if (isinstance(attr, type)
                    and issubclass(attr, BaseTool)
                    and attr is not BaseTool):

                    try:
                        # Instantiate and register
                        tool_instance = attr()
                        tool_def = tool_instance.to_tool_definition()
                        self.registry.register_tool(tool_def, replace=True)
                        logger.debug(f"Registered tool: {tool_def.metadata.name}")
                    except Exception as e:
                        logger.error(f"Error registering {attr_name}: {e}")

            logger.debug(f"Loaded module: {file_path.name}")
```

---

## DSPy ReAct Integration

### 6. DSPy Bridge (`dspy_bridge.py`)

```python
"""
Bridge between Pydantic tools and DSPy ReAct.

Converts ToolDefinitions to callables that DSPy ReAct can use.
"""
from typing import List, Callable, Any, Dict
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from .models import ToolDefinition, ToolResult
from .registry import ToolRegistry

logger = logging.getLogger(__name__)


class DSPyToolBridge:
    """
    Converts Pydantic tools to DSPy-compatible callables.

    DSPy ReAct expects:
    - List of callable functions
    - Functions return strings (usually JSON)
    - Functions have docstrings describing behavior

    This bridge handles:
    - Converting async tools to sync (for DSPy compatibility)
    - Parameter extraction and validation
    - Result formatting (ToolResult → JSON string)
    - Docstring generation from metadata

    Examples:
        >>> bridge = DSPyToolBridge(registry)
        >>> react_tools = bridge.get_dspy_tools()
        >>> agent = dspy.ReAct(signature, tools=react_tools)
    """

    def __init__(
        self,
        registry: ToolRegistry,
        max_workers: int = 3
    ):
        """
        Initialize DSPy bridge.

        Args:
            registry: ToolRegistry containing tools
            max_workers: Max threads for async execution
        """
        self.registry = registry
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def get_dspy_tools(
        self,
        include_categories: List[str] = None,
        exclude_tools: List[str] = None
    ) -> List[Callable]:
        """
        Get all tools as DSPy-compatible callables.

        Args:
            include_categories: Only include these categories (None = all)
            exclude_tools: Exclude these tool names

        Returns:
            List of callable functions for DSPy ReAct
        """
        tools = self.registry.get_all_tools()
        dspy_tools = []

        exclude_tools = exclude_tools or []

        for tool in tools:
            # Filter by category
            if include_categories and tool.metadata.category.value not in include_categories:
                continue

            # Filter by exclusion list
            if tool.metadata.name in exclude_tools:
                continue

            # Convert to DSPy-compatible callable
            dspy_tool = self._create_dspy_callable(tool)
            dspy_tools.append(dspy_tool)

        logger.info(f"Created {len(dspy_tools)} DSPy-compatible tools")
        return dspy_tools

    def _create_dspy_callable(self, tool: ToolDefinition) -> Callable:
        """
        Create a DSPy-compatible callable from ToolDefinition.

        Args:
            tool: ToolDefinition to convert

        Returns:
            Callable function for DSPy ReAct
        """
        # Extract metadata
        tool_name = tool.metadata.name
        description = tool.metadata.description

        # Build parameter documentation
        param_docs = []
        for param in tool.parameters:
            required_str = "required" if param.required else "optional"
            param_doc = f"    {param.name} ({param.type.value}, {required_str}): {param.description}"
            if param.default is not None:
                param_doc += f" (default: {param.default})"
            param_docs.append(param_doc)

        # Generate docstring
        docstring = f"""
{description}

Args:
{chr(10).join(param_docs)}

Returns:
    JSON string with execution results

Tool: {tool_name} (v{tool.metadata.version})
Category: {tool.metadata.category.value}
"""

        # Create wrapper function
        def dspy_callable(**kwargs) -> str:
            """Wrapper function for DSPy ReAct."""
            try:
                # Execute tool (handle async)
                result = self._execute_tool_sync(tool, kwargs)

                # Convert ToolResult to JSON string
                return result.to_json_string()

            except Exception as e:
                logger.error(f"Error in DSPy tool {tool_name}: {e}")
                # Return error as JSON
                import json
                return json.dumps({
                    "success": False,
                    "error": {
                        "error_type": type(e).__name__,
                        "message": str(e)
                    }
                })

        # Set function metadata
        dspy_callable.__name__ = tool_name
        dspy_callable.__doc__ = docstring

        # Attach tool definition for introspection
        dspy_callable._tool_definition = tool

        return dspy_callable

    def _execute_tool_sync(
        self,
        tool: ToolDefinition,
        kwargs: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute tool synchronously (wraps async if needed).

        Args:
            tool: ToolDefinition to execute
            kwargs: Parameters for tool

        Returns:
            ToolResult from execution
        """
        # Check if executor is async
        if asyncio.iscoroutinefunction(tool.executor):
            # Run async in separate thread with new event loop
            def run_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(tool.executor(**kwargs))
                finally:
                    loop.close()

            future = self.executor.submit(run_in_thread)
            return future.result(timeout=tool.metadata.timeout)
        else:
            # Execute sync
            return tool.executor(**kwargs)
```

---

## Example Implementations

### Example 1: Simple Decorator-Based Tool

```python
"""
Simple web search tool using decorator pattern.
"""
from tool_system import tool, ToolCategory, ToolResult
import httpx


@tool(
    name="web_search",
    description="Search the web using DuckDuckGo",
    category=ToolCategory.RESEARCH,
    examples=[
        "web_search(query='Python tutorial', limit=5)",
        "web_search(query='best practices for async Python')"
    ],
    tags=["search", "web", "research"]
)
async def web_search(query: str, limit: int = 10) -> ToolResult:
    """
    Search the web and return results.

    Args:
        query: Search query
        limit: Maximum number of results (default: 10)

    Returns:
        ToolResult with search results
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1}
            )
            data = response.json()

            # Extract results
            results = data.get("RelatedTopics", [])[:limit]

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "count": len(results)
                },
                execution_time=0  # Will be set by wrapper
            )
    except Exception as e:
        raise  # Will be caught and wrapped by decorator
```

### Example 2: Class-Based Tool (Agent-Zero Style)

```python
"""
Code execution tool using class-based pattern.
"""
from tool_system import BaseTool, ToolMetadata, ToolCategory, ToolResult
from pydantic import BaseModel, Field
from typing import Literal
import subprocess
import shlex


class CodeExecutionTool(BaseTool):
    """Execute code in various runtimes."""

    metadata = ToolMetadata(
        name="code_execution",
        description="Execute code in Python, Node.js, or terminal",
        category=ToolCategory.SYSTEM,
        version="2.0.0",
        examples=[
            "Execute Python: code_execution(code='print(2+2)', runtime='python')",
            "Execute Node: code_execution(code='console.log(2+2)', runtime='nodejs')"
        ],
        tags=["code", "execution", "python", "nodejs", "terminal"],
        timeout=60
    )

    class Parameters(BaseModel):
        """Validated parameters for code execution."""
        code: str = Field(..., description="Code to execute")
        runtime: Literal["python", "nodejs", "terminal"] = Field(
            ...,
            description="Runtime environment"
        )
        session: int = Field(
            default=0,
            ge=0,
            le=10,
            description="Session ID (0-10)"
        )
        timeout: int = Field(
            default=30,
            ge=1,
            le=300,
            description="Execution timeout in seconds"
        )

    async def execute(self, params: Parameters) -> ToolResult:
        """
        Execute code in specified runtime.

        Args:
            params: Validated parameters

        Returns:
            ToolResult with execution output
        """
        if params.runtime == "python":
            return await self._execute_python(params)
        elif params.runtime == "nodejs":
            return await self._execute_nodejs(params)
        elif params.runtime == "terminal":
            return await self._execute_terminal(params)
        else:
            raise ValueError(f"Unknown runtime: {params.runtime}")

    async def _execute_python(self, params: Parameters) -> ToolResult:
        """Execute Python code."""
        escaped_code = shlex.quote(params.code)
        command = f"python3 -c {escaped_code}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=params.timeout
            )

            output = result.stdout + result.stderr

            return ToolResult(
                success=result.returncode == 0,
                data={
                    "output": output,
                    "return_code": result.returncode,
                    "runtime": "python"
                },
                execution_time=0
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error={
                    "error_type": "TimeoutError",
                    "message": f"Execution exceeded {params.timeout}s timeout"
                },
                execution_time=params.timeout
            )

    async def _execute_nodejs(self, params: Parameters) -> ToolResult:
        """Execute Node.js code."""
        # Similar implementation
        pass

    async def _execute_terminal(self, params: Parameters) -> ToolResult:
        """Execute terminal command."""
        # Similar implementation
        pass

    async def before_execution(self, params: Parameters) -> None:
        """Log execution before running."""
        logger.info(f"Executing {params.runtime} code in session {params.session}")

    async def after_execution(self, result: ToolResult, params: Parameters) -> None:
        """Log execution results."""
        status = "✓" if result.success else "✗"
        logger.info(f"{status} Execution completed in {result.execution_time:.2f}s")
```

### Example 3: DSPy ReAct Integration

```python
"""
Example of using Pydantic tools with DSPy ReAct.
"""
import dspy
from tool_system import get_global_registry, DSPyToolBridge, ToolDiscovery

# Initialize DSPy
lm = dspy.LM(model="openrouter/anthropic/claude-sonnet-4.5", api_key="...")
dspy.configure(lm=lm)

# Discover tools from directory
discovery = ToolDiscovery()
discovery.discover_tools("./python/tools", recursive=True)

# Get registry
registry = get_global_registry()
print(f"Registered {registry.count_tools()} tools")

# Create DSPy-compatible tools
bridge = DSPyToolBridge(registry)
react_tools = bridge.get_dspy_tools()

# Define signature
class StrategyAgent(dspy.Signature):
    """Strategic decision-making agent."""
    context: str = dspy.InputField(desc="System context")
    user_message: str = dspy.InputField(desc="User's request")
    response: str = dspy.OutputField(desc="Agent response")

# Create ReAct agent with tools
agent = dspy.ReAct(StrategyAgent, tools=react_tools)

# Use the agent
result = agent(
    context="Pipeline data available via tools",
    user_message="Audit lead flow for last 24 hours"
)

print(result.response)
```

---

## Migration Guide

### Phase 1: Installation (No Breaking Changes)

**1. Install the new tool system alongside existing code:**

```python
# Add to python/helpers/tool_system/__init__.py
from .models import (
    ToolDefinition, ToolMetadata, ToolParameter,
    ToolResult, ToolError, ToolCategory
)
from .base import BaseTool
from .registry import ToolRegistry, get_global_registry
from .decorators import tool
from .discovery import ToolDiscovery
from .dspy_bridge import DSPyToolBridge

__all__ = [
    'ToolDefinition', 'ToolMetadata', 'ToolParameter',
    'ToolResult', 'ToolError', 'ToolCategory',
    'BaseTool', 'ToolRegistry', 'get_global_registry',
    'tool', 'ToolDiscovery', 'DSPyToolBridge'
]
```

**2. No changes to existing agent-zero tools required.**

### Phase 2: Register Existing Tools

**Create adapter for agent-zero tools:**

```python
"""
Adapter to register agent-zero Tools with Pydantic registry.
"""
from python.helpers.tool import Tool as AgentZeroTool
from tool_system import (
    ToolDefinition, ToolMetadata, ToolParameter,
    ToolCategory, ToolResult, get_global_registry
)


def register_agent_zero_tool(
    tool_class: type,
    category: ToolCategory = ToolCategory.CUSTOM
):
    """
    Register an agent-zero Tool with Pydantic registry.

    Args:
        tool_class: Agent-zero Tool class
        category: Tool category
    """
    # Create metadata from tool
    metadata = ToolMetadata(
        name=tool_class.__name__,
        description=tool_class.__doc__ or "No description",
        category=category,
        version="1.0.0"
    )

    # Create wrapper executor
    async def executor(**kwargs):
        # Instantiate tool (needs agent context - handle separately)
        # For now, return placeholder
        return ToolResult(
            success=True,
            data={"message": "Agent-zero tool - use original interface"},
            execution_time=0
        )

    # Create definition
    tool_def = ToolDefinition(
        metadata=metadata,
        parameters=[],  # Extract from __init__ signature
        executor=executor
    )

    # Register
    registry = get_global_registry()
    registry.register_tool(tool_def)
```

### Phase 3: Create New Tools with Pydantic

**Use decorator pattern for simple tools:**

```python
from tool_system import tool, ToolCategory, ToolResult

@tool(name="my_new_tool", category=ToolCategory.DATA)
async def my_new_tool(param1: str, param2: int = 10) -> ToolResult:
    """My new tool using Pydantic."""
    result = await do_something(param1, param2)
    return ToolResult(success=True, data=result, execution_time=0)
```

**Use class-based pattern for complex tools:**

```python
from tool_system import BaseTool, ToolMetadata, ToolCategory
from pydantic import BaseModel

class MyComplexTool(BaseTool):
    metadata = ToolMetadata(
        name="my_complex_tool",
        description="Complex tool with validation",
        category=ToolCategory.ANALYSIS
    )

    class Parameters(BaseModel):
        data: dict
        threshold: float = 0.5

    async def execute(self, params: Parameters) -> ToolResult:
        # Implementation
        pass
```

### Phase 4: Migrate Old Tools (Optional)

**Steps to migrate an agent-zero tool:**

1. **Extract the execute logic:**
```python
# Old (agent-zero)
class MemorySave(Tool):
    async def execute(self, text="", area="", **kwargs):
        metadata = {"area": area, **kwargs}
        db = await Memory.get(self.agent)
        id = await db.insert_text(text, metadata)
        result = self.agent.read_prompt("fw.memory_saved.md", memory_id=id)
        return Response(message=result, break_loop=False)
```

2. **Convert to Pydantic tool:**
```python
# New (Pydantic)
from tool_system import BaseTool, ToolMetadata, ToolCategory, ToolResult
from pydantic import BaseModel, Field

class MemorySaveTool(BaseTool):
    metadata = ToolMetadata(
        name="memory_save",
        description="Save information to agent memory",
        category=ToolCategory.DATA,
        version="2.0.0"
    )

    class Parameters(BaseModel):
        text: str = Field(..., description="Text to save")
        area: str = Field(default="main", description="Memory area")
        metadata: dict = Field(default_factory=dict, description="Additional metadata")

    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    async def execute(self, params: Parameters) -> ToolResult:
        metadata_dict = {"area": params.area, **params.metadata}
        db = await Memory.get(self.agent)
        memory_id = await db.insert_text(params.text, metadata_dict)

        result_message = self.agent.read_prompt(
            "fw.memory_saved.md",
            memory_id=memory_id
        )

        return ToolResult(
            success=True,
            data={
                "memory_id": memory_id,
                "message": result_message
            },
            execution_time=0
        )
```

### Integration Checklist

- [ ] Install Pydantic tool system in `python/helpers/tool_system/`
- [ ] Verify existing tools still work (no breaking changes)
- [ ] Create 1-2 new tools using decorator pattern
- [ ] Test DSPy ReAct integration with new tools
- [ ] Set up automatic discovery for new tools
- [ ] (Optional) Migrate high-value tools to Pydantic
- [ ] Update documentation with examples

---

## Advanced Features

### Tool Composition

```python
@tool(name="research_and_save", category=ToolCategory.RESEARCH)
async def research_and_save(query: str) -> ToolResult:
    """Research a topic and save results to memory."""
    # Get registry to access other tools
    registry = get_global_registry()

    # Use search tool
    search_tool = registry.get_tool("web_search")
    search_result = await search_tool.executor(query=query, limit=5)

    if not search_result.success:
        return search_result

    # Use memory save tool
    memory_tool = registry.get_tool("memory_save")
    memory_result = await memory_tool.executor(
        text=str(search_result.data),
        area="research"
    )

    return ToolResult(
        success=True,
        data={
            "search_results": search_result.data,
            "memory_id": memory_result.data
        },
        execution_time=search_result.execution_time + memory_result.execution_time
    )
```

### Caching

```python
from functools import lru_cache
import hashlib
import json

def cached_tool(**tool_kwargs):
    """Decorator to add caching to tools."""
    def decorator(func):
        cache = {}

        @tool(**tool_kwargs)
        async def wrapper(**kwargs):
            # Create cache key from parameters
            cache_key = hashlib.md5(
                json.dumps(kwargs, sort_keys=True).encode()
            ).hexdigest()

            # Check cache
            if cache_key in cache:
                return cache[cache_key]

            # Execute tool
            result = await func(**kwargs)

            # Cache successful results
            if result.success:
                cache[cache_key] = result

            return result

        return wrapper
    return decorator


@cached_tool(name="expensive_research", category=ToolCategory.RESEARCH)
async def expensive_research(topic: str) -> ToolResult:
    """Expensive research operation with caching."""
    # Implementation
    pass
```

### Metrics & Monitoring

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

@dataclass
class ToolMetrics:
    """Metrics for tool execution."""
    tool_name: str
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_called: datetime = None
    errors: List[str] = field(default_factory=list)


class MetricsCollector:
    """Collect and track tool metrics."""

    def __init__(self):
        self.metrics: Dict[str, ToolMetrics] = {}

    def record_execution(
        self,
        tool_name: str,
        result: ToolResult
    ):
        """Record tool execution metrics."""
        if tool_name not in self.metrics:
            self.metrics[tool_name] = ToolMetrics(tool_name=tool_name)

        m = self.metrics[tool_name]
        m.call_count += 1
        m.total_execution_time += result.execution_time
        m.average_execution_time = m.total_execution_time / m.call_count
        m.last_called = datetime.utcnow()

        if result.success:
            m.success_count += 1
        else:
            m.failure_count += 1
            if result.error:
                m.errors.append(result.error.message)

    def get_metrics(self, tool_name: str) -> ToolMetrics:
        """Get metrics for a tool."""
        return self.metrics.get(tool_name)

    def get_all_metrics(self) -> List[ToolMetrics]:
        """Get metrics for all tools."""
        return list(self.metrics.values())
```

---

## Summary

This Pydantic-based tool system provides:

✅ **Type Safety**: Pydantic validation at every layer
✅ **Dynamic Discovery**: Auto-discovery via directory scanning
✅ **Multiple Patterns**: Decorator, class-based, and functional
✅ **DSPy Integration**: First-class ReAct support
✅ **Backward Compatible**: Works with existing agent-zero tools
✅ **Extensible**: Easy to add new tools and features
✅ **Production Ready**: Error handling, validation, metrics

**Key Benefits:**
- Catch errors at tool definition time, not runtime
- Auto-generate documentation and schemas
- Easy testing with type-safe mocks
- Clear migration path from existing system
- Scales from simple scripts to complex agent systems

**Next Steps:**
1. Implement core models in `python/helpers/tool_system/models.py`
2. Create registry and discovery system
3. Build DSPy bridge for ReAct integration
4. Test with 2-3 example tools
5. Roll out gradually with Phase 1-4 migration plan
