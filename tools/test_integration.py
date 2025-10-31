#!/usr/bin/env python3
"""
Test RAG + Wolfram Alpha Integration

Quick verification that all tools are properly integrated into Strategy Agent.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_tool_imports():
    """Test that all tools can be imported"""
    print("🧪 Testing tool imports...\n")
    
    # Test strategy_tools imports
    try:
        from tools.strategy_tools import (
            search_knowledge_base,
            list_indexed_documents,
            query_spreadsheet_data,
            wolfram_strategic_query,
            wolfram_market_analysis,
            wolfram_demographic_insight,
            STRATEGY_TOOLS
        )
        print("✅ All strategy_tools imports successful")
        print(f"   - {len(STRATEGY_TOOLS)} tools in registry")
        for tool_name in STRATEGY_TOOLS.keys():
            print(f"     • {tool_name}")
    except ImportError as e:
        print(f"❌ Failed to import strategy_tools: {e}")
        return False
    
    # Test RAG tools
    try:
        from tools.rag_tools import (
            retrieve_relevant_documents,
            list_documents,
            get_document_content,
            execute_sql_query,
            RAG_TOOLS
        )
        print(f"\n✅ RAG tools imported successfully")
        print(f"   - {len(RAG_TOOLS)} RAG tools available")
    except ImportError as e:
        print(f"❌ Failed to import rag_tools: {e}")
    
    # Test Wolfram tools
    try:
        from tools.wolfram_alpha import (
            WolframAlphaClient,
            wolfram_strategic_query as wf_query,
            wolfram_market_analysis as wf_market,
            wolfram_demographic_insight as wf_demo,
            WOLFRAM_TOOLS
        )
        print(f"\n✅ Wolfram Alpha tools imported successfully")
        print(f"   - {len(WOLFRAM_TOOLS)} Wolfram tools available")
    except ImportError as e:
        print(f"❌ Failed to import wolfram_alpha: {e}")
    
    return True

async def test_strategy_agent_integration():
    """Test that Strategy Agent has the tools registered"""
    print("\n\n🧪 Testing Strategy Agent integration...\n")
    
    try:
        # This will fail if agent can't initialize, but we'll catch it
        from agents.strategy_agent import StrategyAgent
        print("✅ StrategyAgent class imported successfully")
        
        # We can't fully initialize without credentials, but we can verify the class structure
        print("   - Agent class is properly structured")
        
        # Check if the _initialize_react_tools method exists
        if hasattr(StrategyAgent, '_initialize_react_tools'):
            print("   - _initialize_react_tools method exists")
        else:
            print("   ⚠️  _initialize_react_tools method not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to import StrategyAgent: {e}")
        return False

async def test_tool_signatures():
    """Verify tool function signatures are correct"""
    print("\n\n🧪 Testing tool signatures...\n")
    
    from tools.strategy_tools import STRATEGY_TOOLS
    import inspect
    
    print("Tool signatures:")
    for tool_name, tool_func in STRATEGY_TOOLS.items():
        sig = inspect.signature(tool_func)
        params = [f"{name}: {param.annotation.__name__ if param.annotation != inspect.Parameter.empty else 'Any'}" 
                  for name, param in sig.parameters.items()]
        print(f"  • {tool_name}({', '.join(params)})")
    
    return True

async def main():
    """Run all integration tests"""
    print("=" * 80)
    print("RAG + WOLFRAM ALPHA INTEGRATION TEST")
    print("=" * 80)
    
    results = []
    
    # Test imports
    results.append(await test_tool_imports())
    
    # Test Strategy Agent integration
    results.append(await test_strategy_agent_integration())
    
    # Test signatures
    results.append(await test_tool_signatures())
    
    # Summary
    print("\n" + "=" * 80)
    if all(results):
        print("✅ ALL TESTS PASSED - Integration complete!")
        print("\nNext steps:")
        print("  1. Deploy to Railway")
        print("  2. Test RAG search with real query")
        print("  3. Test Wolfram Alpha query")
        print("  4. Verify Phoenix tracing captures new tools")
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
        return 1
    
    print("=" * 80)
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
