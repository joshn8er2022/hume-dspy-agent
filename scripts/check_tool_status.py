#!/usr/bin/env python3
"""
Tool Status Checker - Verifies which tools are configured and working.

Run this script to see:
- Which environment variables are set
- Which tools are available
- Which APIs are accessible
- What needs configuration
"""

import os
import sys
import asyncio
import json
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_env_vars() -> Dict[str, Tuple[bool, str]]:
    """Check which environment variables are configured."""
    env_vars = {
        # Database
        'SUPABASE_URL': None,
        'SUPABASE_SERVICE_KEY': None,
        'SUPABASE_KEY': None,
        
        # LLMs
        'OPENROUTER_API_KEY': None,
        'OPENAI_API_KEY': None,
        'ANTHROPIC_API_KEY': None,
        
        # Communication
        'SLACK_BOT_TOKEN': None,
        'SLACK_MCP_XOXB_TOKEN': None,
        'SLACK_CHANNEL': None,
        'SLACK_CHANNEL_INBOUND': None,
        
        # Email
        'GMASS_API_KEY': None,
        'FROM_EMAIL': None,
        'SENDGRID_API_KEY': None,
        
        # CRM
        'CLOSE_API_KEY': None,
        
        # Research
        'CLEARBIT_API_KEY': None,
        'APOLLO_API_KEY': None,
        'PERPLEXITY_API_KEY': None,
        
        # Strategic Intelligence
        'WOLFRAM_APP_ID': None,
        
        # MCP
        'MCP_SERVER_URL': None,
        
        # Observability
        'PHOENIX_API_KEY': None,
        'PHOENIX_ENDPOINT': None,
        'PHOENIX_PROJECT_NAME': None,
    }
    
    results = {}
    for var in env_vars:
        value = os.getenv(var)
        is_set = value is not None and len(value) > 0
        masked = (value[:10] + '...' + value[-4:]) if value and len(value) > 14 else (value or 'Not Set')
        results[var] = (is_set, masked)
    
    return results


async def test_supabase() -> Tuple[bool, str]:
    """Test Supabase connection."""
    try:
        from supabase import create_client
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            return False, "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY"
        
        client = create_client(url, key)
        # Try a simple query
        result = client.table('leads').select('id').limit(1).execute()
        return True, f"✅ Connected (tested with leads table)"
    except Exception as e:
        return False, f"❌ Connection failed: {str(e)}"


async def test_openai() -> Tuple[bool, str]:
    """Test OpenAI API (for embeddings)."""
    try:
        from openai import AsyncOpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return False, "Missing OPENAI_API_KEY"
        
        client = AsyncOpenAI(api_key=api_key)
        # Try a simple embedding call
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input="test"
        )
        return True, f"✅ Working (tested embeddings)"
    except Exception as e:
        return False, f"❌ Failed: {str(e)}"


async def test_slack() -> Tuple[bool, str]:
    """Test Slack API."""
    try:
        from slack_sdk import WebClient
        
        token = os.getenv('SLACK_BOT_TOKEN') or os.getenv('SLACK_MCP_XOXB_TOKEN')
        if not token:
            return False, "Missing SLACK_BOT_TOKEN or SLACK_MCP_XOXB_TOKEN"
        
        client = WebClient(token=token)
        # Try auth test
        result = client.auth_test()
        if result['ok']:
            return True, f"✅ Connected (team: {result.get('team', 'Unknown')})"
        else:
            return False, f"❌ Auth failed: {result.get('error')}"
    except Exception as e:
        return False, f"❌ Failed: {str(e)}"


async def test_mcp() -> Tuple[bool, str]:
    """Test MCP client."""
    try:
        from core.mcp_client import MCPClient
        
        mcp = MCPClient()
        if not mcp.client:
            return False, "Missing MCP_SERVER_URL"
        
        # Try to list tools
        tools = await mcp.list_tools()
        if tools:
            return True, f"✅ Connected ({len(tools)} tools available)"
        else:
            return False, "Connected but no tools returned"
    except Exception as e:
        return False, f"❌ Failed: {str(e)}"


async def test_clearbit() -> Tuple[bool, str]:
    """Test Clearbit API."""
    try:
        api_key = os.getenv('CLEARBIT_API_KEY')
        if not api_key:
            return False, "Missing CLEARBIT_API_KEY"
        
        import httpx
        async with httpx.AsyncClient() as client:
            # Test person enrichment endpoint
            response = await client.get(
                "https://person.clearbit.com/v2/combined/find",
                params={"email": "test@example.com"},
                auth=(api_key, ""),
                timeout=5.0
            )
            # 404 is OK (test email doesn't exist), 401 is auth failure
            if response.status_code == 401:
                return False, "❌ Invalid API key"
            elif response.status_code in [200, 404]:
                return True, "✅ API key valid"
            else:
                return False, f"❌ Unexpected status: {response.status_code}"
    except Exception as e:
        return False, f"❌ Failed: {str(e)}"


async def test_wolfram() -> Tuple[bool, str]:
    """Test Wolfram Alpha API."""
    try:
        app_id = os.getenv('WOLFRAM_APP_ID')
        if not app_id:
            return False, "Missing WOLFRAM_APP_ID"
        
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.wolframalpha.com/api/v1/llm-api",
                params={"appid": app_id, "input": "test"},
                timeout=10.0
            )
            if response.status_code == 200:
                return True, "✅ API working"
            elif response.status_code == 401:
                return False, "❌ Invalid App ID"
            else:
                return False, f"❌ Status: {response.status_code}"
    except Exception as e:
        return False, f"❌ Failed: {str(e)}"


def print_results():
    """Print comprehensive tool status report."""
    print("=" * 80)
    print("TOOL INVENTORY & STATUS CHECK")
    print("=" * 80)
    print()
    
    # Check environment variables
    print("📋 ENVIRONMENT VARIABLES")
    print("-" * 80)
    env_status = check_env_vars()
    
    categories = {
        "Database": ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'SUPABASE_KEY'],
        "LLMs": ['OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'],
        "Communication": ['SLACK_BOT_TOKEN', 'SLACK_MCP_XOXB_TOKEN', 'SLACK_CHANNEL', 'SLACK_CHANNEL_INBOUND'],
        "Email": ['GMASS_API_KEY', 'FROM_EMAIL', 'SENDGRID_API_KEY'],
        "CRM": ['CLOSE_API_KEY'],
        "Research": ['CLEARBIT_API_KEY', 'APOLLO_API_KEY', 'PERPLEXITY_API_KEY'],
        "Strategic": ['WOLFRAM_APP_ID'],
        "MCP": ['MCP_SERVER_URL'],
        "Observability": ['PHOENIX_API_KEY', 'PHOENIX_ENDPOINT', 'PHOENIX_PROJECT_NAME'],
    }
    
    for category, vars_list in categories.items():
        print(f"\n{category}:")
        for var in vars_list:
            if var in env_status:
                is_set, masked = env_status[var]
                status = "✅" if is_set else "❌"
                print(f"  {status} {var}: {masked}")
    
    print("\n" + "=" * 80)
    print("🔧 API CONNECTION TESTS")
    print("-" * 80)
    
    # Run async tests
    async def run_tests():
        tests = [
            ("Supabase", test_supabase()),
            ("OpenAI", test_openai()),
            ("Slack", test_slack()),
            ("MCP Client", test_mcp()),
            ("Clearbit", test_clearbit()),
            ("Wolfram Alpha", test_wolfram()),
        ]
        
        for name, test_coro in tests:
            try:
                success, message = await test_coro
                status = "✅" if success else "❌"
                print(f"{status} {name}: {message}")
            except Exception as e:
                print(f"❌ {name}: Error - {str(e)}")
    
    asyncio.run(run_tests())
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("-" * 80)
    
    # Count configured
    configured = sum(1 for _, (is_set, _) in env_status.items() if is_set)
    total = len(env_status)
    
    print(f"Environment Variables: {configured}/{total} configured ({configured*100//total}%)")
    print()
    print("✅ = Configured/Working")
    print("❌ = Not Configured/Failed")
    print()
    print("📖 See docs/COMPLETE_TOOL_INVENTORY.md for full details")


if __name__ == "__main__":
    print_results()

