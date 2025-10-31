"""
Example usage of the dynamic tool loading system.

This script demonstrates how to:
1. Discover tools automatically
2. Register tools manually
3. Query the registry
4. Execute tools with validation
5. Integrate with DSPy agents

Author: Claude (Sonnet 4.5)
Date: 2025-10-31
"""

import asyncio
import logging
from pathlib import Path

# Import the tool system
from tools import (
    discover_tools,
    get_global_registry,
    BaseTool,
    ToolMetadata,
    ToolCategory,
    ToolResult
)
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Create a custom tool
# ============================================================================

class ExampleCalculatorTool(BaseTool):
    """Example calculator tool demonstrating BaseTool inheritance."""

    metadata = ToolMetadata(
        name="example_calculator",
        description="Performs basic arithmetic operations",
        category=ToolCategory.CUSTOM,
        version="1.0.0",
        tags=["math", "calculator", "example"],
        examples=[
            "Add numbers: example_calculator(operation='add', a=5, b=3)",
            "Multiply: example_calculator(operation='multiply', a=4, b=7)"
        ]
    )

    class Parameters(BaseModel):
        """Calculator parameters with validation."""
        operation: str = Field(
            ...,
            description="Operation to perform: add, subtract, multiply, divide"
        )
        a: float = Field(..., description="First number")
        b: float = Field(..., description="Second number")

    async def execute(self, params: Parameters) -> ToolResult:
        """Execute the calculation."""
        operations = {
            'add': lambda a, b: a + b,
            'subtract': lambda a, b: a - b,
            'multiply': lambda a, b: a * b,
            'divide': lambda a, b: a / b if b != 0 else None
        }

        if params.operation not in operations:
            from tools.base import ToolError
            return ToolResult(
                success=False,
                error=ToolError(
                    error_type="ValueError",
                    message=f"Invalid operation: {params.operation}"
                ),
                execution_time=0
            )

        result = operations[params.operation](params.a, params.b)

        if result is None:
            from tools.base import ToolError
            return ToolResult(
                success=False,
                error=ToolError(
                    error_type="ZeroDivisionError",
                    message="Cannot divide by zero"
                ),
                execution_time=0
            )

        return ToolResult(
            success=True,
            data={
                "operation": params.operation,
                "a": params.a,
                "b": params.b,
                "result": result
            },
            execution_time=0
        )


# ============================================================================
# Example usage functions
# ============================================================================

async def example_1_manual_registration():
    """Example 1: Manually register a tool."""
    logger.info("\n=== Example 1: Manual Tool Registration ===")

    # Get the global registry
    registry = get_global_registry()

    # Create and register a tool
    tool = ExampleCalculatorTool()
    registry.register_tool(tool)

    logger.info(f"Registered tool: {tool.metadata.name}")
    logger.info(f"Total tools in registry: {registry.count_tools()}")


async def example_2_auto_discovery():
    """Example 2: Automatically discover tools from directory."""
    logger.info("\n=== Example 2: Automatic Tool Discovery ===")

    # Discover tools from the tools directory
    tools_dir = Path(__file__).parent
    count = discover_tools(str(tools_dir), recursive=False)

    logger.info(f"Discovered {count} tools from {tools_dir}")

    # List all registered tools
    registry = get_global_registry()
    for tool in registry.get_all_tools():
        logger.info(f"  - {tool.metadata.name}: {tool.metadata.description}")


async def example_3_query_registry():
    """Example 3: Query the registry."""
    logger.info("\n=== Example 3: Query Registry ===")

    registry = get_global_registry()

    # Get tool by name
    tool = registry.get_tool("example_calculator")
    if tool:
        logger.info(f"Found tool: {tool.metadata.name}")

    # List tools by category
    data_tools = registry.list_tools(category=ToolCategory.DATA)
    logger.info(f"Data tools: {len(data_tools)}")

    # Search tools
    results = registry.search_tools("supabase")
    logger.info(f"Search 'supabase': {len(results)} results")
    for tool in results:
        logger.info(f"  - {tool.metadata.name}")


async def example_4_execute_tool():
    """Example 4: Execute a tool with validation."""
    logger.info("\n=== Example 4: Tool Execution ===")

    registry = get_global_registry()
    tool = registry.get_tool("example_calculator")

    if not tool:
        logger.warning("Calculator tool not found. Registering it now...")
        tool = ExampleCalculatorTool()
        registry.register_tool(tool)

    # Execute with valid parameters
    logger.info("Executing: add 10 + 5")
    result = await tool.run(operation="add", a=10, b=5)

    if result.success:
        logger.info(f"Result: {result.data['result']}")
        logger.info(f"Execution time: {result.execution_time:.3f}s")
    else:
        logger.error(f"Error: {result.error.message}")

    # Execute with invalid parameters
    logger.info("Executing: invalid operation")
    result = await tool.run(operation="invalid", a=1, b=2)

    if not result.success:
        logger.info(f"Expected error: {result.error.message}")


async def example_5_parameter_schema():
    """Example 5: Generate parameter schema for DSPy."""
    logger.info("\n=== Example 5: Parameter Schema Generation ===")

    registry = get_global_registry()
    tool = registry.get_tool("example_calculator")

    if tool:
        schema = tool.get_parameter_schema()
        logger.info("Parameter schema (for DSPy integration):")
        import json
        logger.info(json.dumps(schema, indent=2))


async def example_6_error_handling():
    """Example 6: Error handling and recovery."""
    logger.info("\n=== Example 6: Error Handling ===")

    registry = get_global_registry()
    tool = registry.get_tool("example_calculator")

    if tool:
        # Trigger division by zero
        logger.info("Executing: divide by zero")
        result = await tool.run(operation="divide", a=10, b=0)

        if not result.success:
            logger.info(f"Error type: {result.error.error_type}")
            logger.info(f"Error message: {result.error.message}")
            logger.info(f"Recoverable: {result.error.recoverable}")


async def example_7_batch_execution():
    """Example 7: Batch execute multiple operations."""
    logger.info("\n=== Example 7: Batch Execution ===")

    registry = get_global_registry()
    tool = registry.get_tool("example_calculator")

    if tool:
        operations = [
            ("add", 5, 3),
            ("multiply", 4, 7),
            ("subtract", 10, 4),
            ("divide", 20, 5)
        ]

        results = []
        for op, a, b in operations:
            result = await tool.run(operation=op, a=a, b=b)
            results.append(result)

        # Summary
        successful = sum(1 for r in results if r.success)
        logger.info(f"Executed {len(results)} operations: {successful} successful")

        for i, (result, (op, a, b)) in enumerate(zip(results, operations), 1):
            if result.success:
                logger.info(f"  {i}. {op}({a}, {b}) = {result.data['result']}")


# ============================================================================
# Integration Example: DSPy ReAct
# ============================================================================

def create_dspy_tools():
    """Example: Create DSPy-compatible tools from registry.

    This demonstrates how to integrate the tool registry with DSPy ReAct.
    """
    logger.info("\n=== DSPy Integration Example ===")

    registry = get_global_registry()

    def create_dspy_wrapper(tool: BaseTool):
        """Wrap a BaseTool for DSPy ReAct."""
        import json

        def dspy_callable(**kwargs) -> str:
            """DSPy-compatible callable."""
            # Run the tool (sync wrapper around async)
            import asyncio
            result = asyncio.run(tool.run(**kwargs))
            return result.to_json_string()

        # Set function metadata
        dspy_callable.__name__ = tool.metadata.name
        dspy_callable.__doc__ = tool.metadata.description

        return dspy_callable

    # Create DSPy tools from all registered tools
    dspy_tools = []
    for tool in registry.get_all_tools():
        dspy_tool = create_dspy_wrapper(tool)
        dspy_tools.append(dspy_tool)

    logger.info(f"Created {len(dspy_tools)} DSPy-compatible tools")
    logger.info("These can be passed to dspy.ReAct(signature, tools=dspy_tools)")

    return dspy_tools


# ============================================================================
# Main execution
# ============================================================================

async def main():
    """Run all examples."""
    logger.info("=" * 70)
    logger.info("Dynamic Tool Loading System - Example Usage")
    logger.info("=" * 70)

    # Run examples in sequence
    await example_1_manual_registration()
    await example_2_auto_discovery()
    await example_3_query_registry()
    await example_4_execute_tool()
    await example_5_parameter_schema()
    await example_6_error_handling()
    await example_7_batch_execution()

    # DSPy integration example (non-async)
    create_dspy_tools()

    logger.info("\n" + "=" * 70)
    logger.info("All examples completed successfully!")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
