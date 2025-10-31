"""
Base classes for dynamic tool loading system.

This module provides core Pydantic models and abstract base classes for
creating type-safe, discoverable tools for the hume-dspy-agent system.

Architecture:
- ToolParameter: Type-safe parameter definitions with validation
- ToolMetadata: Tool descriptive information and categorization
- ToolResult: Structured execution results with error handling
- BaseTool: Abstract base class for all tool implementations

Author: Claude (Sonnet 4.5)
Date: 2025-10-31
Version: 1.0
"""

from typing import Any, Optional, Dict, List, Type
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import time
import traceback
from datetime import datetime


class ToolParameterType(str, Enum):
    """Supported parameter types for tools."""
    STRING = "string"
    NUMBER = "number"
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
        ...     type=ToolParameterType.STRING,
        ...     description="Search query to execute",
        ...     required=True,
        ...     examples=["lead status", "pipeline metrics"]
        ... )
    """
    name: str = Field(..., description="Parameter name")
    type: ToolParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    validation_rules: Optional[Dict[str, Any]] = Field(
        None,
        description="Pydantic validation rules (min, max, pattern, etc.)"
    )
    examples: List[Any] = Field(default_factory=list, description="Example values")

    @field_validator('validation_rules')
    @classmethod
    def validate_rules(cls, v, info):
        """Ensure validation rules match parameter type."""
        if not v:
            return v

        param_type = info.data.get('type')
        if param_type == ToolParameterType.STRING:
            allowed_rules = {'min_length', 'max_length', 'pattern', 'regex'}
        elif param_type in [ToolParameterType.NUMBER]:
            allowed_rules = {'ge', 'gt', 'le', 'lt', 'multiple_of'}
        elif param_type == ToolParameterType.ARRAY:
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
        ...     name="supabase_lead_query",
        ...     description="Query leads from Supabase database",
        ...     category=ToolCategory.DATA,
        ...     version="1.0.0",
        ...     tags=["supabase", "leads", "database"]
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

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Ensure tool name is valid identifier."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f"Tool name must be alphanumeric with underscores/hyphens: {v}")
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
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When error occurred")


class ToolResult(BaseModel):
    """
    Result of tool execution with metadata.

    Examples:
        >>> result = ToolResult(
        ...     success=True,
        ...     data={"leads": [...]},
        ...     execution_time=1.23
        ... )
    """
    success: bool = Field(..., description="Whether execution succeeded")
    data: Optional[Any] = Field(None, description="Result data (if success)")
    error: Optional[ToolError] = Field(None, description="Error info (if failure)")
    execution_time: float = Field(..., description="Execution time in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When executed")

    @model_validator(mode='after')
    def validate_result(self):
        """Ensure either data or error is present, not both."""
        if self.success and self.error:
            raise ValueError("Cannot have error when success=True")
        if not self.success and not self.error:
            raise ValueError("Must have error when success=False")
        return self

    def to_json_string(self) -> str:
        """Convert result to JSON string for DSPy ReAct."""
        import json
        return json.dumps({
            "success": self.success,
            "data": self.data,
            "error": self.error.model_dump() if self.error else None,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }, indent=2, default=str)


class BaseTool(ABC):
    """
    Base class for tool implementations.

    Subclasses must define:
    - metadata: ToolMetadata class attribute
    - Parameters: Pydantic BaseModel for parameters
    - execute(): Async method that implements tool logic

    Examples:
        >>> class SupabaseLeadQuery(BaseTool):
        ...     metadata = ToolMetadata(
        ...         name="supabase_lead_query",
        ...         description="Query leads from Supabase",
        ...         category=ToolCategory.DATA
        ...     )
        ...
        ...     class Parameters(BaseModel):
        ...         tier: Optional[str] = None
        ...         limit: int = 10
        ...
        ...     async def execute(self, params: Parameters) -> ToolResult:
        ...         # Implementation
        ...         return ToolResult(success=True, data={...}, execution_time=0.5)
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
                    stack_trace=traceback.format_exc(),
                    recoverable=False
                ),
                execution_time=execution_time
            )

    def get_parameter_schema(self) -> Dict[str, Any]:
        """
        Generate JSON schema for parameters (for DSPy/OpenAI function calling).

        Returns:
            JSON schema dictionary
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # Extract from Pydantic model
        for field_name, field_info in self.Parameters.model_fields.items():
            field_schema = {
                "type": self._map_python_type_to_json_type(field_info.annotation),
                "description": field_info.description or f"Parameter: {field_name}"
            }

            # Add default if available
            if field_info.default is not None:
                field_schema["default"] = field_info.default

            schema["properties"][field_name] = field_schema

            # Mark as required if no default
            if field_info.is_required():
                schema["required"].append(field_name)

        return schema

    @staticmethod
    def _map_python_type_to_json_type(python_type) -> str:
        """Map Python type hints to JSON schema types."""
        # Handle Optional types
        if hasattr(python_type, '__origin__'):
            if python_type.__origin__ is type(None):
                return "null"
            # Get the first non-None type from Union
            args = getattr(python_type, '__args__', ())
            if args:
                python_type = next((arg for arg in args if arg is not type(None)), str)

        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        return type_mapping.get(python_type, "string")


__all__ = [
    'ToolParameterType',
    'ToolCategory',
    'ToolParameter',
    'ToolMetadata',
    'ToolError',
    'ToolResult',
    'BaseTool'
]
