"""
MCP (Model Context Protocol) Client for Zapier Integration

This module provides a wrapper around FastMCP client to connect to the Zapier
MCP server, giving access to 200+ tools including:
- Close CRM (full integration)
- Perplexity (AI research)
- Apify (web scraping)
- Instantly (email campaigns)
- Google Sheets, Gmail, Slack, and more

Phase 0 / Phase 0.5 Integration
"""
import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for connecting to Zapier MCP server with 200+ tools."""
    
    def __init__(self):
        """Initialize MCP client with server URL from environment."""
        self.server_url = os.getenv("MCP_SERVER_URL")
        if not self.server_url:
            logger.warning("⚠️ MCP_SERVER_URL not set - MCP tools will be unavailable")
            self.transport = None
            self.client = None
        else:
            self.transport = StreamableHttpTransport(self.server_url)
            self.client = Client(transport=self.transport)
            logger.info("✅ MCP Client initialized")
            logger.info(f"   Server: {self.server_url[:50]}...")
    
    async def connect(self) -> bool:
        """Establish connection to MCP server.
        
        Returns:
            True if connected successfully, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Connection is established in context manager
            logger.info("🔌 Connecting to MCP server...")
            return True
        except Exception as e:
            logger.error(f"❌ MCP connection failed: {e}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from MCP server.
        
        Returns:
            List of tool definitions with name, description, params
        """
        if not self.client:
            return []
        
        try:
            async with self.client:
                tools = await self.client.list_tools()
                logger.info(f"📋 MCP Tools available: {len(tools)}")
                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "params": tool.inputSchema.get("properties", {})
                    }
                    for tool in tools
                ]
        except Exception as e:
            logger.error(f"❌ Failed to list MCP tools: {e}")
            return []
    
    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a specific MCP tool with parameters.
        
        Args:
            tool_name: Name of the tool to call
            params: Dictionary of parameters for the tool
        
        Returns:
            Tool result as dictionary
        """
        if not self.client:
            return {
                "success": False,
                "error": "MCP client not initialized (missing MCP_SERVER_URL)"
            }
        
        try:
            async with self.client:
                logger.info(f"🔧 MCP Tool: {tool_name}")
                logger.info(f"   Params: {json.dumps(params, indent=2)[:200]}...")
                
                result = await self.client.call_tool(tool_name, params)
                
                # Parse result from TextContent
                if result.content and len(result.content) > 0:
                    result_text = result.content[0].text
                    try:
                        parsed_result = json.loads(result_text)
                        logger.info(f"✅ MCP Tool {tool_name} succeeded")
                        return {
                            "success": True,
                            "data": parsed_result
                        }
                    except json.JSONDecodeError:
                        # Return as-is if not JSON
                        logger.info(f"✅ MCP Tool {tool_name} returned text")
                        return {
                            "success": True,
                            "data": result_text
                        }
                else:
                    return {
                        "success": True,
                        "data": None
                    }
                
        except Exception as e:
            logger.error(f"❌ MCP Tool {tool_name} failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close_create_lead(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
        note: Optional[str] = None,
        **custom_fields
    ) -> Dict[str, Any]:
        """Create a new lead in Close CRM via MCP.
        
        Args:
            name: Lead name (required)
            email: Email address
            phone: Phone number
            company: Company name
            note: Additional notes
            **custom_fields: Any custom fields to set
        
        Returns:
            Close CRM lead object
        """
        params = {
            "name": name,
        }
        
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone
        if company:
            params["company"] = company
        if note:
            params["note"] = note
        
        # Add custom fields
        params.update(custom_fields)
        
        return await self.call_tool("close_create_lead", params)
    
    async def perplexity_research(
        self,
        query: str,
        model: str = "llama-3.1-sonar-small-128k-online"
    ) -> Dict[str, Any]:
        """Use Perplexity AI to research a topic via MCP.
        
        Args:
            query: Research query
            model: Perplexity model to use
        
        Returns:
            Research results from Perplexity
        """
        params = {
            "content": query,
            "model": model
        }
        
        return await self.call_tool("perplexity_chat_completion", params)
    
    async def scrape_url(
        self,
        url: str,
        crawler_type: str = "playwright:firefox"
    ) -> Dict[str, Any]:
        """Scrape a website URL via Apify MCP tool.
        
        Args:
            url: URL to scrape
            crawler_type: Type of scraper to use
        
        Returns:
            Scraped content (text, markdown, HTML)
        """
        params = {
            "url": url,
            "crawlerType": crawler_type
        }
        
        return await self.call_tool("apify_scrape_single_url", params)
    
    async def instantly_add_lead(
        self,
        email: str,
        campaign_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        **custom_variables
    ) -> Dict[str, Any]:
        """Add a lead to an Instantly.ai campaign via MCP.
        
        Args:
            email: Lead email (required)
            campaign_id: Campaign ID to add lead to
            first_name: First name
            last_name: Last name
            **custom_variables: Custom merge variables
        
        Returns:
            Instantly.ai response
        """
        params = {
            "email": email,
            "campaign_id": campaign_id
        }
        
        if first_name:
            params["firstName"] = first_name
        if last_name:
            params["lastName"] = last_name
        
        params.update(custom_variables)
        
        return await self.call_tool("instantly_add_lead_to_campaign", params)


# Global MCP client singleton
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get global MCP client instance (singleton).
    
    Returns:
        MCPClient instance
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
