"""
Wolfram Alpha Integration for Strategic Intelligence

Provides computational knowledge and cross-domain data synthesis
for strategic planning and market analysis.
"""
import os
import urllib.parse
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class WolframAlphaClient:
    """Client for Wolfram Alpha LLM API"""
    
    def __init__(self, app_id: Optional[str] = None):
        """
        Initialize Wolfram Alpha client.
        
        Args:
            app_id: Wolfram Alpha App ID. If None, reads from environment.
        """
        self.app_id = app_id or os.getenv('WOLFRAM_APP_ID')
        if not self.app_id:
            raise ValueError("Wolfram Alpha App ID is required. Set WOLFRAM_APP_ID environment variable.")
        
        self.base_url = "https://www.wolframalpha.com/api/v1/llm-api"
    
    def query(self, input_query: str, assumptions: Optional[Dict[str, str]] = None) -> str:
        """
        Query Wolfram Alpha for computational knowledge.
        
        Args:
            input_query: Natural language query
            assumptions: Optional dictionary of assumption parameters
            
        Returns:
            Formatted response from Wolfram Alpha
            
        Example:
            result = client.query("healthcare spending per capita US vs Europe")
        """
        try:
            # Build query parameters
            params = {
                'appid': self.app_id,
                'input': input_query
            }
            
            # Add assumptions if provided
            if assumptions:
                for key, value in assumptions.items():
                    params[f'assumption'] = f"{key}={value}"
            
            # Make request
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            return f"Error querying Wolfram Alpha: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"


async def wolfram_strategic_query(
    query: str,
    category: Optional[str] = None
) -> str:
    """
    Execute a strategic intelligence query using Wolfram Alpha.
    
    This tool provides computational knowledge and cross-domain data synthesis
    for strategic planning, market analysis, and competitive intelligence.
    
    Use this for:
    - Market size and demographic analysis
    - Economic indicators and trends
    - Healthcare spending patterns
    - Competitive benchmarking
    - Statistical comparisons across regions/markets
    - Scientific/medical data for product development
    
    Args:
        query: Natural language query
        category: Optional category hint (healthcare, economics, demographics, etc.)
        
    Returns:
        Formatted strategic insights from Wolfram Alpha
        
    Example Queries:
        - "healthcare spending per capita United States vs Europe"
        - "aging population demographics over 65 in California"
        - "median household income by state United States"
        - "supplement market size United States"
        - "telemedicine adoption rate 2020 to 2024"
    """
    try:
        client = WolframAlphaClient()
        
        # Add category context if provided
        if category:
            enhanced_query = f"{category}: {query}"
        else:
            enhanced_query = query
        
        # Execute query
        result = client.query(enhanced_query)
        
        # Format response
        if "Wolfram|Alpha could not understand" in result:
            return f"❌ Wolfram Alpha could not process this query. Try rephrasing or simplifying.\n\nQuery: {query}\n\n{result}"
        
        if "(data not available)" in result:
            return f"⚠️ Wolfram Alpha found the query but data is not available.\n\nQuery: {query}\n\nTry: More specific query or different data source"
        
        # Success - return formatted result
        output = f"🔬 **Wolfram Alpha Strategic Insight**\n\n"
        output += f"**Query**: {query}\n\n"
        output += "**Results**:\n"
        output += "```\n"
        output += result
        output += "\n```\n"
        
        return output
        
    except Exception as e:
        return f"❌ Error executing Wolfram Alpha query: {str(e)}"


async def wolfram_market_analysis(
    market: str,
    metric: str,
    comparison_regions: Optional[list] = None
) -> str:
    """
    Analyze market metrics using Wolfram Alpha computational data.
    
    Specialized tool for market analysis queries with structured inputs.
    
    Args:
        market: Market or industry (e.g., "healthcare", "supplements", "telemedicine")
        metric: What to analyze (e.g., "spending per capita", "market size", "growth rate")
        comparison_regions: Optional list of regions to compare
        
    Returns:
        Comparative market analysis
        
    Example:
        result = await wolfram_market_analysis(
            market="healthcare",
            metric="spending per capita",
            comparison_regions=["United States", "Europe", "Asia"]
        )
    """
    try:
        # Build query
        if comparison_regions:
            regions_str = " vs ".join(comparison_regions)
            query = f"{market} {metric} {regions_str}"
        else:
            query = f"{market} {metric}"
        
        # Execute using main query function
        return await wolfram_strategic_query(query, category="market analysis")
        
    except Exception as e:
        return f"❌ Error in market analysis: {str(e)}"


async def wolfram_demographic_insight(
    region: str,
    demographic_query: str
) -> str:
    """
    Get demographic insights for strategic planning.
    
    Args:
        region: Geographic region (country, state, city)
        demographic_query: What demographic data to retrieve
        
    Returns:
        Demographic analysis from Wolfram Alpha
        
    Example:
        result = await wolfram_demographic_insight(
            region="California",
            demographic_query="population over 65 aging trends"
        )
    """
    try:
        query = f"{demographic_query} {region}"
        return await wolfram_strategic_query(query, category="demographics")
        
    except Exception as e:
        return f"❌ Error in demographic analysis: {str(e)}"


# Tool metadata for agent registration
WOLFRAM_TOOLS = {
    "wolfram_strategic_query": {
        "function": wolfram_strategic_query,
        "description": "Query Wolfram Alpha for strategic intelligence, market data, and computational analysis",
        "parameters": ["query", "category"]
    },
    "wolfram_market_analysis": {
        "function": wolfram_market_analysis,
        "description": "Analyze market metrics with cross-regional comparisons using Wolfram Alpha data",
        "parameters": ["market", "metric", "comparison_regions"]
    },
    "wolfram_demographic_insight": {
        "function": wolfram_demographic_insight,
        "description": "Get demographic data and trends for strategic planning",
        "parameters": ["region", "demographic_query"]
    }
}
