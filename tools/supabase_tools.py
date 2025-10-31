"""
Supabase database tools for lead querying.

Example tools demonstrating the dynamic tool loading system.
These tools query the Supabase database for lead information and analytics.

Author: Claude (Sonnet 4.5)
Date: 2025-10-31
Version: 1.0
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging

from .base import BaseTool, ToolMetadata, ToolCategory, ToolResult, ToolError

logger = logging.getLogger(__name__)


class SupabaseLeadQuery(BaseTool):
    """
    Query leads from Supabase database.

    This tool provides flexible querying of leads with filtering by tier,
    time period, and pagination. Integrates with the existing Supabase
    connection used by the strategy agent.

    Examples:
        >>> tool = SupabaseLeadQuery()
        >>> result = await tool.run(tier="HOT", limit=10)
        >>> print(result.data)  # List of HOT leads
    """

    metadata = ToolMetadata(
        name="supabase_lead_query",
        description="Query leads from Supabase database with filtering by tier, time period, and pagination",
        category=ToolCategory.DATA,
        version="1.0.0",
        author="Claude (Sonnet 4.5)",
        examples=[
            "Query HOT leads: supabase_lead_query(tier='HOT', limit=10)",
            "Recent leads: supabase_lead_query(days_back=7, limit=50)",
            "All leads: supabase_lead_query(limit=100)"
        ],
        tags=["supabase", "leads", "database", "query"],
        requires_auth=True,
        timeout=30
    )

    class Parameters(BaseModel):
        """Query parameters with validation."""
        tier: Optional[str] = Field(
            None,
            description="Filter by tier (HOT, WARM, COOL, COLD, SCORCHING)"
        )
        days_back: Optional[int] = Field(
            None,
            ge=1,
            le=365,
            description="Filter leads from last N days"
        )
        limit: int = Field(
            10,
            ge=1,
            le=1000,
            description="Maximum number of results"
        )
        offset: int = Field(
            0,
            ge=0,
            description="Offset for pagination"
        )

    def __init__(self):
        """Initialize with Supabase connection."""
        super().__init__()
        self.supabase = self._get_supabase_client()

    def _get_supabase_client(self):
        """Get or create Supabase client."""
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

            if not url or not key:
                logger.warning("Supabase credentials not configured")
                return None

            return create_client(url, key)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            return None

    async def execute(self, params: Parameters) -> ToolResult:
        """
        Execute the lead query.

        Args:
            params: Validated query parameters

        Returns:
            ToolResult with lead data or error
        """
        if not self.supabase:
            return ToolResult(
                success=False,
                error=ToolError(
                    error_type="ConfigurationError",
                    message="Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.",
                    recoverable=True
                ),
                execution_time=0
            )

        try:
            # Build query
            query = self.supabase.table('leads').select('*')

            # Apply tier filter
            if params.tier:
                query = query.eq('qualification_tier', params.tier.upper())

            # Apply time filter
            if params.days_back:
                start_date = (datetime.utcnow() - timedelta(days=params.days_back)).isoformat()
                query = query.gte('created_at', start_date)

            # Apply pagination
            query = query.range(params.offset, params.offset + params.limit - 1)

            # Execute query
            result = query.execute()

            return ToolResult(
                success=True,
                data={
                    "leads": result.data,
                    "count": len(result.data),
                    "filters": {
                        "tier": params.tier,
                        "days_back": params.days_back,
                        "limit": params.limit,
                        "offset": params.offset
                    }
                },
                execution_time=0,  # Will be set by run()
                metadata={
                    "table": "leads",
                    "query_timestamp": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=ToolError(
                    error_type=type(e).__name__,
                    message=f"Database query failed: {str(e)}",
                    recoverable=True,
                    retry_after=5
                ),
                execution_time=0
            )


class SupabasePipelineAnalytics(BaseTool):
    """
    Analyze pipeline metrics from Supabase.

    Provides aggregated analytics including tier distribution,
    source breakdown, and trend analysis.

    Examples:
        >>> tool = SupabasePipelineAnalytics()
        >>> result = await tool.run(days=7, group_by="tier")
        >>> print(result.data)  # Pipeline analytics
    """

    metadata = ToolMetadata(
        name="supabase_pipeline_analytics",
        description="Analyze pipeline metrics including tier distribution, source breakdown, and trends",
        category=ToolCategory.ANALYSIS,
        version="1.0.0",
        author="Claude (Sonnet 4.5)",
        examples=[
            "Weekly analytics: supabase_pipeline_analytics(days=7, group_by='tier')",
            "Source breakdown: supabase_pipeline_analytics(days=30, group_by='source')",
            "Monthly trends: supabase_pipeline_analytics(days=30)"
        ],
        tags=["supabase", "analytics", "pipeline", "metrics"],
        requires_auth=True,
        timeout=30
    )

    class Parameters(BaseModel):
        """Analytics parameters."""
        days: int = Field(
            7,
            ge=1,
            le=365,
            description="Time period in days"
        )
        group_by: str = Field(
            "tier",
            description="Group results by: tier, source, or date"
        )

    def __init__(self):
        """Initialize with Supabase connection."""
        super().__init__()
        self.supabase = self._get_supabase_client()

    def _get_supabase_client(self):
        """Get or create Supabase client."""
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

            if not url or not key:
                return None

            return create_client(url, key)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            return None

    async def execute(self, params: Parameters) -> ToolResult:
        """
        Execute pipeline analytics.

        Args:
            params: Validated analytics parameters

        Returns:
            ToolResult with analytics data
        """
        if not self.supabase:
            return ToolResult(
                success=False,
                error=ToolError(
                    error_type="ConfigurationError",
                    message="Supabase not configured",
                    recoverable=True
                ),
                execution_time=0
            )

        try:
            # Query leads for time period
            start_date = (datetime.utcnow() - timedelta(days=params.days)).isoformat()
            result = self.supabase.table('leads') \
                .select('*') \
                .gte('created_at', start_date) \
                .execute()

            leads = result.data

            # Calculate analytics based on group_by
            if params.group_by == "tier":
                analytics = self._analyze_by_tier(leads)
            elif params.group_by == "source":
                analytics = self._analyze_by_source(leads)
            elif params.group_by == "date":
                analytics = self._analyze_by_date(leads)
            else:
                analytics = {"error": f"Invalid group_by: {params.group_by}"}

            return ToolResult(
                success=True,
                data={
                    "period_days": params.days,
                    "total_leads": len(leads),
                    "group_by": params.group_by,
                    "analytics": analytics,
                    "timestamp": datetime.utcnow().isoformat()
                },
                execution_time=0,
                metadata={
                    "start_date": start_date,
                    "end_date": datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=ToolError(
                    error_type=type(e).__name__,
                    message=f"Analytics failed: {str(e)}",
                    recoverable=True
                ),
                execution_time=0
            )

    def _analyze_by_tier(self, leads: List[Dict]) -> Dict[str, Any]:
        """Analyze leads by tier."""
        tier_counts = {}
        for lead in leads:
            tier = lead.get('qualification_tier', 'UNKNOWN')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            "by_tier": tier_counts,
            "total": len(leads),
            "hot_percentage": (tier_counts.get('HOT', 0) + tier_counts.get('SCORCHING', 0)) / len(leads) * 100 if leads else 0
        }

    def _analyze_by_source(self, leads: List[Dict]) -> Dict[str, Any]:
        """Analyze leads by source."""
        source_counts = {}
        for lead in leads:
            source = lead.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1

        return {
            "by_source": source_counts,
            "total": len(leads)
        }

    def _analyze_by_date(self, leads: List[Dict]) -> Dict[str, Any]:
        """Analyze leads by date."""
        date_counts = {}
        for lead in leads:
            created_at = lead.get('created_at', '')
            date = created_at.split('T')[0] if 'T' in created_at else 'unknown'
            date_counts[date] = date_counts.get(date, 0) + 1

        return {
            "by_date": date_counts,
            "total": len(leads)
        }


__all__ = [
    'SupabaseLeadQuery',
    'SupabasePipelineAnalytics'
]
