"""
Test Wolfram Alpha Integration for Strategic Intelligence

Demonstrates the kinds of strategic insights Wolfram Alpha provides
for billion-dollar business decisions.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.wolfram_alpha import (
    wolfram_strategic_query,
    wolfram_market_analysis,
    wolfram_demographic_insight
)


async def test_strategic_queries():
    """Test strategic intelligence queries"""
    print("=" * 80)
    print("🔬 WOLFRAM ALPHA STRATEGIC INTELLIGENCE TEST")
    print("=" * 80)
    print()
    
    # Test 1: Market Comparison
    print("TEST 1: Healthcare Market Comparison")
    print("-" * 80)
    result1 = await wolfram_strategic_query(
        "healthcare spending per capita United States vs Europe"
    )
    print(result1)
    print()
    
    # Test 2: Demographic Analysis
    print("TEST 2: Aging Population Demographics")
    print("-" * 80)
    result2 = await wolfram_demographic_insight(
        region="United States",
        demographic_query="population over 65 trends"
    )
    print(result2)
    print()
    
    # Test 3: Economic Indicators
    print("TEST 3: Economic Analysis")
    print("-" * 80)
    result3 = await wolfram_strategic_query(
        "median household income California vs New York vs Texas"
    )
    print(result3)
    print()
    
    # Test 4: Market Size Query
    print("TEST 4: Market Analysis")
    print("-" * 80)
    result4 = await wolfram_market_analysis(
        market="telemedicine",
        metric="adoption rate",
        comparison_regions=["United States"]
    )
    print(result4)
    print()
    
    # Test 5: Global Comparison
    print("TEST 5: Global Healthcare Comparison")
    print("-" * 80)
    result5 = await wolfram_strategic_query(
        "healthcare expenditure as percentage of GDP United States vs China vs Germany"
    )
    print(result5)
    print()
    
    print("=" * 80)
    print("✅ WOLFRAM ALPHA STRATEGIC TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_strategic_queries())
