"""
Tests for dynamic tool loading system.

Comprehensive test suite covering:
- Tool registration and discovery
- Parameter validation
- Tool execution
- Error handling
- Registry operations

Author: Claude (Sonnet 4.5)
Date: 2025-10-31
Version: 1.0
"""

import pytest
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult, ToolError,
    ToolCategory, ToolParameterType
)
from tools.registry import ToolRegistry, discover_tools, get_global_registry
from pydantic import BaseModel, Field


# ============================================================================
# Test Fixtures - Mock Tools
# ============================================================================

class MockSimpleTool(BaseTool):
    """Mock tool for testing basic functionality."""

    metadata = ToolMetadata(
        name="mock_simple_tool",
        description="A simple mock tool for testing",
        category=ToolCategory.CUSTOM,
        version="1.0.0",
        tags=["mock", "test"]
    )

    class Parameters(BaseModel):
        message: str = Field(..., description="Message to process")
        count: int = Field(default=1, ge=1, le=10, description="Number of times to repeat")

    async def execute(self, params: Parameters) -> ToolResult:
        """Execute mock operation."""
        result = params.message * params.count
        return ToolResult(
            success=True,
            data={"result": result, "length": len(result)},
            execution_time=0.01
        )


class MockFailingTool(BaseTool):
    """Mock tool that always fails - for error testing."""

    metadata = ToolMetadata(
        name="mock_failing_tool",
        description="A tool that always fails",
        category=ToolCategory.CUSTOM,
        version="1.0.0"
    )

    class Parameters(BaseModel):
        trigger_error: bool = Field(default=True, description="Whether to trigger error")

    async def execute(self, params: Parameters) -> ToolResult:
        """Always raises an exception."""
        if params.trigger_error:
            raise ValueError("Mock error for testing")
        return ToolResult(success=True, data={}, execution_time=0)


class MockDataTool(BaseTool):
    """Mock data tool for category testing."""

    metadata = ToolMetadata(
        name="mock_data_tool",
        description="Mock data processing tool",
        category=ToolCategory.DATA,
        version="1.0.0",
        tags=["data", "mock"]
    )

    class Parameters(BaseModel):
        query: str = Field(..., description="Data query")

    async def execute(self, params: Parameters) -> ToolResult:
        """Execute data query."""
        return ToolResult(
            success=True,
            data={"query": params.query, "results": []},
            execution_time=0.01
        )


# ============================================================================
# Test Cases
# ============================================================================

class TestToolMetadata:
    """Test ToolMetadata validation."""

    def test_valid_metadata(self):
        """Test creating valid metadata."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test description",
            category=ToolCategory.DATA,
            version="1.0.0"
        )
        assert metadata.name == "test_tool"
        assert metadata.category == ToolCategory.DATA

    def test_invalid_tool_name(self):
        """Test that invalid tool names are rejected."""
        with pytest.raises(ValueError):
            ToolMetadata(
                name="invalid name!",  # Spaces and special chars
                description="Test",
                category=ToolCategory.DATA
            )

    def test_metadata_with_tags(self):
        """Test metadata with tags."""
        metadata = ToolMetadata(
            name="test_tool",
            description="Test",
            category=ToolCategory.DATA,
            tags=["tag1", "tag2", "tag3"]
        )
        assert len(metadata.tags) == 3
        assert "tag1" in metadata.tags


class TestToolParameter:
    """Test ToolParameter validation."""

    def test_valid_parameter(self):
        """Test creating valid parameter."""
        param = ToolParameter(
            name="test_param",
            type=ToolParameterType.STRING,
            description="Test parameter",
            required=True
        )
        assert param.name == "test_param"
        assert param.required is True

    def test_parameter_with_validation_rules(self):
        """Test parameter with validation rules."""
        param = ToolParameter(
            name="age",
            type=ToolParameterType.NUMBER,
            description="Age parameter",
            validation_rules={"ge": 0, "le": 150}
        )
        assert param.validation_rules["ge"] == 0

    def test_invalid_validation_rules(self):
        """Test that invalid validation rules are rejected."""
        with pytest.raises(ValueError):
            ToolParameter(
                name="text",
                type=ToolParameterType.STRING,
                description="Text",
                validation_rules={"ge": 0}  # ge is for numbers, not strings
            )


class TestToolResult:
    """Test ToolResult validation."""

    def test_successful_result(self):
        """Test creating successful result."""
        result = ToolResult(
            success=True,
            data={"key": "value"},
            execution_time=1.5
        )
        assert result.success is True
        assert result.data["key"] == "value"

    def test_failed_result(self):
        """Test creating failed result."""
        result = ToolResult(
            success=False,
            error=ToolError(
                error_type="ValueError",
                message="Test error"
            ),
            execution_time=0.5
        )
        assert result.success is False
        assert result.error.message == "Test error"

    def test_result_validation(self):
        """Test that result validation catches inconsistencies."""
        # Success with error should fail
        with pytest.raises(ValueError):
            ToolResult(
                success=True,
                error=ToolError(error_type="Error", message="test"),
                execution_time=1.0
            )

        # Failure without error should fail
        with pytest.raises(ValueError):
            ToolResult(
                success=False,
                execution_time=1.0
            )

    def test_result_to_json(self):
        """Test converting result to JSON."""
        result = ToolResult(
            success=True,
            data={"test": "value"},
            execution_time=1.0
        )
        json_str = result.to_json_string()
        assert "success" in json_str
        assert "test" in json_str


class TestBaseTool:
    """Test BaseTool functionality."""

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Test basic tool execution."""
        tool = MockSimpleTool()
        result = await tool.run(message="test", count=3)

        assert result.success is True
        assert result.data["result"] == "testtesttest"
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test tool error handling."""
        tool = MockFailingTool()
        result = await tool.run(trigger_error=True)

        assert result.success is False
        assert result.error is not None
        assert "Mock error" in result.error.message

    @pytest.mark.asyncio
    async def test_parameter_validation(self):
        """Test parameter validation."""
        tool = MockSimpleTool()

        # Valid parameters
        result = await tool.run(message="hello", count=2)
        assert result.success is True

        # Invalid count (out of range)
        result = await tool.run(message="hello", count=100)
        assert result.success is False
        assert result.error is not None

    def test_get_parameter_schema(self):
        """Test parameter schema generation."""
        tool = MockSimpleTool()
        schema = tool.get_parameter_schema()

        assert schema["type"] == "object"
        assert "message" in schema["properties"]
        assert "count" in schema["properties"]
        assert "message" in schema["required"]


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def setup_method(self):
        """Clear registry before each test."""
        registry = get_global_registry()
        registry.clear()

    def test_register_tool(self):
        """Test registering a tool."""
        registry = get_global_registry()
        tool = MockSimpleTool()

        registry.register_tool(tool)
        assert registry.count_tools() == 1
        assert registry.get_tool("mock_simple_tool") is not None

    def test_register_duplicate_tool(self):
        """Test that duplicate registration fails without replace flag."""
        registry = get_global_registry()
        tool1 = MockSimpleTool()
        tool2 = MockSimpleTool()

        registry.register_tool(tool1)

        # Should raise error
        with pytest.raises(ValueError):
            registry.register_tool(tool2, replace=False)

        # Should succeed with replace=True
        registry.register_tool(tool2, replace=True)
        assert registry.count_tools() == 1

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = get_global_registry()
        tool = MockSimpleTool()

        registry.register_tool(tool)
        assert registry.count_tools() == 1

        result = registry.unregister_tool("mock_simple_tool")
        assert result is True
        assert registry.count_tools() == 0

    def test_get_tool(self):
        """Test getting a tool by name."""
        registry = get_global_registry()
        tool = MockSimpleTool()
        registry.register_tool(tool)

        retrieved = registry.get_tool("mock_simple_tool")
        assert retrieved is not None
        assert retrieved.metadata.name == "mock_simple_tool"

    def test_list_tools_by_category(self):
        """Test listing tools by category."""
        registry = get_global_registry()
        registry.register_tool(MockSimpleTool())
        registry.register_tool(MockDataTool())

        data_tools = registry.list_tools(category=ToolCategory.DATA)
        assert len(data_tools) == 1
        assert data_tools[0].metadata.category == ToolCategory.DATA

    def test_list_tools_by_tag(self):
        """Test listing tools by tag."""
        registry = get_global_registry()
        registry.register_tool(MockSimpleTool())
        registry.register_tool(MockDataTool())

        mock_tools = registry.list_tools(tag="mock")
        assert len(mock_tools) == 2

    def test_search_tools(self):
        """Test searching tools."""
        registry = get_global_registry()
        registry.register_tool(MockSimpleTool())
        registry.register_tool(MockDataTool())

        # Search by name
        results = registry.search_tools("simple")
        assert len(results) == 1

        # Search by description
        results = registry.search_tools("data")
        assert len(results) >= 1

    def test_get_all_tools(self):
        """Test getting all tools."""
        registry = get_global_registry()
        registry.register_tool(MockSimpleTool())
        registry.register_tool(MockDataTool())

        all_tools = registry.get_all_tools()
        assert len(all_tools) == 2


class TestToolDiscovery:
    """Test tool discovery functionality."""

    def setup_method(self):
        """Clear registry before each test."""
        registry = get_global_registry()
        registry.clear()

    def test_discover_tools_from_directory(self):
        """Test discovering tools from directory."""
        # Discover tools from the tools directory
        tools_dir = Path(__file__).parent.parent / "tools"
        count = discover_tools(str(tools_dir), recursive=False)

        # Should find at least the supabase_tools
        assert count >= 2  # SupabaseLeadQuery, SupabasePipelineAnalytics

    def test_discover_nonexistent_directory(self):
        """Test discovering from non-existent directory."""
        count = discover_tools("/nonexistent/path")
        assert count == 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the complete system."""

    def setup_method(self):
        """Clear registry before each test."""
        registry = get_global_registry()
        registry.clear()

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow: register, discover, execute."""
        # 1. Register a tool manually
        registry = get_global_registry()
        tool = MockSimpleTool()
        registry.register_tool(tool)

        # 2. Discover tools from directory
        tools_dir = Path(__file__).parent.parent / "tools"
        count = discover_tools(str(tools_dir), recursive=False)

        # 3. List all tools
        all_tools = registry.get_all_tools()
        assert len(all_tools) > 0

        # 4. Execute a tool
        result = await tool.run(message="integration", count=2)
        assert result.success is True


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
