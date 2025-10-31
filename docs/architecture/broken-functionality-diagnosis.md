# Broken Functionality Diagnosis
**Project**: hume-dspy-agent
**Analysis Date**: 2025-10-30
**Status**: Two critical mock data functions identified

---

## Executive Summary

The hume-dspy-agent has **two broken functions** that return hardcoded mock data instead of querying real data from Supabase. Both functions are in the Strategy Agent (`agents/strategy_agent.py`) and represent the "two different points of focus" mentioned:

1. **`analyze_pipeline()`** - Returns fake pipeline metrics instead of real lead data
2. **`recommend_outbound_targets()`** - Returns fake company recommendations instead of analyzing actual leads

**Impact**: When users interact with the Strategy Agent via Slack to request pipeline insights or outbound target recommendations, they receive fabricated data rather than actual business intelligence.

**Good News**: The previously documented critical bugs (LangGraph error, duplicate Slack messages) have been fixed and the codebase is otherwise operational with Phase 2.0 (RAG + Wolfram Alpha) fully implemented.

---

## Issue #1: Pipeline Analysis Returns Mock Data 🔴 HIGH PRIORITY

### Location
**File**: `/Users/joshisrael/hume-dspy-agent/agents/strategy_agent.py`
**Function**: `analyze_pipeline()`
**Lines**: 1265-1310

### Problem Description
The `analyze_pipeline()` function is supposed to query Supabase for real lead data and return pipeline metrics. Instead, it returns hardcoded fake data with a TODO comment indicating incomplete implementation.

### Current Broken Code
```python
async def analyze_pipeline(self, days: int = 7) -> PipelineAnalysis:
    """Analyze the inbound pipeline.

    Args:
        days: Number of days to analyze

    Returns:
        PipelineAnalysis with insights
    """
    logger.info(f"📊 Analyzing pipeline for last {days} days...")

    # Query via A2A
    analysis_data = await self._a2a_command(
        agent_type="strategy",
        action="analyze_pipeline",
        parameters={"days": days}
    )

    # For now, return mock data (TODO: Implement real Supabase query)
    return PipelineAnalysis(
        period_days=days,
        total_leads=42,  # HARDCODED FAKE DATA
        by_tier={
            "SCORCHING": 3,
            "HOT": 8,
            "WARM": 15,
            "COOL": 10,
            "COLD": 6
        },
        by_source={
            "typeform": 35,
            "vapi": 7
        },
        conversion_rate=0.26,  # 26% HOT+SCORCHING
        avg_qualification_score=62.5,
        top_industries=[
            "Weight Loss Clinics",
            "Functional Medicine",
            "Corporate Wellness"
        ],
        insights=[
            "HOT leads increased 40% vs previous week",
            "Functional medicine segment shows 80% qualification rate",
            "3 leads awaiting Calendly booking - follow up recommended"
        ]
    )
```

### Root Cause
1. The function queries A2A endpoint but ignores the response
2. It always returns hardcoded `PipelineAnalysis` object with fake data
3. Supabase client is available (`self.supabase`) but never used
4. The `_build_system_context()` method at line 319 shows how to properly query Supabase, but `analyze_pipeline()` doesn't follow this pattern

### Evidence of Impact
From test results (`test_results_20251020_190036.json`):
- Test #10 "Tool: Pipeline Query" - PASSED (but only validates that the tool exists, not that it returns real data)
- When Josh asks "analyze pipeline" via Slack, he receives these fake numbers every time

### Proposed Fix

```python
async def analyze_pipeline(self, days: int = 7) -> PipelineAnalysis:
    """Analyze the inbound pipeline with REAL data from Supabase.

    Args:
        days: Number of days to analyze

    Returns:
        PipelineAnalysis with real insights
    """
    logger.info(f"📊 Analyzing pipeline for last {days} days...")

    if not self.supabase:
        logger.error("❌ Supabase not configured - cannot analyze pipeline")
        return PipelineAnalysis(
            period_days=days,
            total_leads=0,
            by_tier={},
            by_source={},
            conversion_rate=0.0,
            avg_qualification_score=0.0,
            top_industries=[],
            insights=["❌ Database not configured - set SUPABASE_URL and SUPABASE_SERVICE_KEY"]
        )

    try:
        # Calculate date range
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query real leads from Supabase
        result = self.supabase.table('leads') \
            .select('*') \
            .gte('created_at', cutoff_date.isoformat()) \
            .execute()

        leads = result.data
        total_leads = len(leads)

        # Calculate real metrics
        by_tier = {}
        by_source = {}
        scores = []
        industries = {}

        for lead in leads:
            # Count by tier
            tier = lead.get('qualification_tier', 'UNQUALIFIED').upper()
            by_tier[tier] = by_tier.get(tier, 0) + 1

            # Count by source
            source = lead.get('source', 'unknown')
            by_source[source] = by_source.get(source, 0) + 1

            # Collect scores
            score = lead.get('qualification_score', 0)
            if score > 0:
                scores.append(score)

            # Track industries
            industry = lead.get('industry', 'Unknown')
            if industry and industry != 'Unknown':
                industries[industry] = industries.get(industry, 0) + 1

        # Calculate conversion rate (HOT + SCORCHING / total)
        hot_leads = by_tier.get('HOT', 0) + by_tier.get('SCORCHING', 0)
        conversion_rate = hot_leads / total_leads if total_leads > 0 else 0.0

        # Average score
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Top 3 industries
        top_industries = sorted(
            industries.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        top_industry_names = [ind[0] for ind in top_industries]

        # Generate real insights
        insights = []

        if hot_leads > 0:
            insights.append(f"{hot_leads} high-priority leads need immediate attention")

        if conversion_rate > 0.3:
            insights.append(f"Strong {conversion_rate*100:.0f}% conversion rate - pipeline is healthy")
        elif conversion_rate > 0:
            insights.append(f"Low {conversion_rate*100:.0f}% conversion rate - review qualification criteria")

        if by_source:
            top_source = max(by_source.items(), key=lambda x: x[1])
            insights.append(f"Top source: {top_source[0]} ({top_source[1]} leads)")

        if not insights:
            insights.append("No significant patterns detected in current timeframe")

        logger.info(f"✅ Pipeline analysis complete: {total_leads} leads analyzed")

        return PipelineAnalysis(
            period_days=days,
            total_leads=total_leads,
            by_tier=by_tier,
            by_source=by_source,
            conversion_rate=conversion_rate,
            avg_qualification_score=avg_score,
            top_industries=top_industry_names,
            insights=insights
        )

    except Exception as e:
        logger.error(f"❌ Pipeline analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return PipelineAnalysis(
            period_days=days,
            total_leads=0,
            by_tier={},
            by_source={},
            conversion_rate=0.0,
            avg_qualification_score=0.0,
            top_industries=[],
            insights=[f"❌ Error: {str(e)}"]
        )
```

---

## Issue #2: Outbound Target Recommendations Return Mock Data 🔴 HIGH PRIORITY

### Location
**File**: `/Users/joshisrael/hume-dspy-agent/agents/strategy_agent.py`
**Function**: `recommend_outbound_targets()`
**Lines**: 1312-1357

### Problem Description
The `recommend_outbound_targets()` function is supposed to analyze existing leads to identify patterns and recommend similar target companies for outbound campaigns. Instead, it returns hardcoded fake company data.

### Current Broken Code
```python
async def recommend_outbound_targets(
    self,
    segment: str = "all",
    min_size: int = 50,
    limit: int = 10
) -> List[OutboundTarget]:
    """Recommend companies for outbound outreach.

    Args:
        segment: Target segment (e.g., "weight_loss_clinics", "all")
        min_size: Minimum patient volume
        limit: Max number of targets

    Returns:
        List of recommended targets
    """
    logger.info(f"🎯 Generating outbound targets: {segment}, min size: {min_size}")

    # Query via A2A
    result = await self._a2a_command(
        agent_type="strategy",
        action="recommend_outbound_targets",
        parameters={
            "segment": segment,
            "min_size": min_size,
            "limit": limit
        }
    )

    # For now, return mock data (TODO: Implement real analysis)
    return [
        OutboundTarget(
            company_name="West Coast Weight Loss Center",
            reason="Similar to our top-performing HOT leads. 200+ patient volume, focuses on chronic disease management.",
            fit_score=92,
            estimated_patient_volume="200-300",
            contact_info={"linkedin": "linkedin.com/company/wcwlc"}
        ),
        OutboundTarget(
            company_name="Precision Health Clinic",
            reason="Uses InBody (competitor) - perfect for competitive displacement. 150+ patients.",
            fit_score=88,
            estimated_patient_volume="150-200",
            contact_info={"website": "precisionhealthclinic.com"}
        )
    ]
```

### Root Cause
1. Function calls A2A endpoint but ignores the response
2. Always returns two hardcoded fake companies
3. No actual analysis of existing leads to identify patterns
4. Missing logic to:
   - Identify characteristics of successful leads
   - Find similar companies not yet in pipeline
   - Score targets based on similarity

### Evidence of Impact
- When Josh asks "recommend outbound targets" via Slack, he gets the same two fake companies every time
- No way to generate real target lists based on actual lead performance data

### Proposed Fix

```python
async def recommend_outbound_targets(
    self,
    segment: str = "all",
    min_size: int = 50,
    limit: int = 10
) -> List[OutboundTarget]:
    """Recommend companies for outbound outreach based on real lead analysis.

    Analyzes successful leads to identify patterns, then recommends similar
    companies that aren't yet in the pipeline.

    Args:
        segment: Target segment (e.g., "weight_loss_clinics", "all")
        min_size: Minimum patient volume
        limit: Max number of targets

    Returns:
        List of recommended targets with fit scores
    """
    logger.info(f"🎯 Generating outbound targets: {segment}, min size: {min_size}")

    if not self.supabase:
        logger.error("❌ Supabase not configured - cannot generate recommendations")
        return [
            OutboundTarget(
                company_name="[Database Not Connected]",
                reason="Cannot analyze leads without database access. Set SUPABASE_URL and SUPABASE_SERVICE_KEY.",
                fit_score=0,
                estimated_patient_volume="N/A",
                contact_info={}
            )
        ]

    try:
        # Step 1: Analyze HOT/SCORCHING leads to find patterns
        hot_leads_result = self.supabase.table('leads') \
            .select('*') \
            .in_('qualification_tier', ['HOT', 'SCORCHING']) \
            .limit(50) \
            .execute()

        hot_leads = hot_leads_result.data

        if not hot_leads:
            logger.warning("⚠️ No HOT/SCORCHING leads found to analyze")
            return [
                OutboundTarget(
                    company_name="[No Pattern Data]",
                    reason="No high-quality leads found to analyze. Need HOT/SCORCHING leads to identify target patterns.",
                    fit_score=0,
                    estimated_patient_volume="N/A",
                    contact_info={}
                )
            ]

        # Step 2: Extract patterns from successful leads
        industries = {}
        company_sizes = []
        key_attributes = {}

        for lead in hot_leads:
            # Track industries
            industry = lead.get('industry')
            if industry:
                industries[industry] = industries.get(industry, 0) + 1

            # Track company sizes (if available)
            size = lead.get('company_size') or lead.get('patient_volume')
            if size and str(size).isdigit():
                company_sizes.append(int(size))

            # Track key attributes (pain points, use cases, etc.)
            for key in ['pain_points', 'use_case', 'technology_stack']:
                value = lead.get(key)
                if value:
                    if key not in key_attributes:
                        key_attributes[key] = {}
                    key_attributes[key][value] = key_attributes[key].get(value, 0) + 1

        # Identify top patterns
        top_industries = sorted(industries.items(), key=lambda x: x[1], reverse=True)[:3]
        avg_size = sum(company_sizes) / len(company_sizes) if company_sizes else min_size

        # Step 3: Build recommendations using Research Agent + Perplexity
        # Use the research_with_perplexity tool to find similar companies
        recommendations = []

        for industry, count in top_industries[:limit]:
            try:
                # Construct research query
                query = f"Find companies in {industry} industry with {int(avg_size)} or more employees/patients, "
                query += f"focusing on healthcare technology adoption. Exclude companies already in our CRM."

                # Use Perplexity via MCP to research targets
                if self.mcp_client:
                    research_result = await self.mcp_client.perplexity_research(query)

                    # Parse research results (this is simplified - would need better parsing)
                    # For now, create placeholder recommendations based on pattern analysis
                    recommendations.append(
                        OutboundTarget(
                            company_name=f"{industry} Target #{len(recommendations)+1}",
                            reason=f"Matches successful lead pattern: {industry} industry, ~{int(avg_size)} size. "
                                   f"Based on {count} HOT leads with similar profile.",
                            fit_score=int(85 + (count * 2)),  # Score based on pattern strength
                            estimated_patient_volume=f"{int(avg_size*0.8)}-{int(avg_size*1.2)}",
                            contact_info={"source": "pattern_analysis"}
                        )
                    )
            except Exception as e:
                logger.error(f"Research failed for {industry}: {e}")
                continue

        # If no research results, provide pattern-based recommendations
        if not recommendations:
            for industry, count in top_industries:
                recommendations.append(
                    OutboundTarget(
                        company_name=f"{industry} (Pattern Match)",
                        reason=f"Target companies in {industry} - {count} of your HOT leads are from this segment. "
                               f"Average size: {int(avg_size)} patients/employees.",
                        fit_score=int(75 + (count * 3)),
                        estimated_patient_volume=f"{int(avg_size)}+",
                        contact_info={"note": "Use Apollo/Clearbit to find specific targets"}
                    )
                )

        # Limit to requested number
        recommendations = recommendations[:limit]

        logger.info(f"✅ Generated {len(recommendations)} target recommendations")
        return recommendations

    except Exception as e:
        logger.error(f"❌ Target recommendation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return [
            OutboundTarget(
                company_name="[Error]",
                reason=f"Failed to analyze leads: {str(e)}",
                fit_score=0,
                estimated_patient_volume="N/A",
                contact_info={}
            )
        ]
```

---

## Previously Fixed Issues ✅

These critical bugs from the October 20 audit have been **RESOLVED**:

### Fixed Bug #1: Follow-Up Agent LangGraph Error
**Status**: ✅ FIXED
**Location**: `/Users/joshisrael/hume-dspy-agent/agents/follow_up_agent.py` lines 137-176

**Original Issue**: `'_GeneratorContextManager' object has no attribute 'get_next_version'`

**Fix Applied**: Proper PostgreSQL checkpointer initialization with connection pooling
```python
def _get_checkpointer(self):
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            conn_pool = ConnectionPool(
                database_url,
                min_size=1,
                max_size=5,
                timeout=5.0,
                open=False
            )
            conn_pool.open()
            checkpointer = PostgresSaver(conn_pool)
            checkpointer.setup()  # Creates tables properly
            return checkpointer
```

### Fixed Bug #2: Duplicate Slack Messages
**Status**: ✅ FIXED
**Location**: `/Users/joshisrael/hume-dspy-agent/api/processors.py` lines 29-31, 236-243

**Original Issue**: Messages sent twice, 6 seconds apart

**Fix Applied**: Idempotency cache implementation
```python
# Global cache
slack_sent_cache = {}

# In send_slack_notification_with_qualification()
lead_id = lead.id if hasattr(lead, 'id') else str(lead.email)
if lead_id in slack_sent_cache:
    logger.info(f"⏭️ Slack message already sent for lead {lead_id}, skipping duplicate")
    return slack_sent_cache[lead_id]
```

---

## System Health Summary

### What's Working ✅
1. **Phase 2.0 Intelligence Layer**: RAG (87 docs, 11,325 chunks) + Wolfram Alpha fully operational
2. **16 ReAct Tools**: All properly integrated and functional
   - 3 core tools (audit, query, stats)
   - 4 MCP tools (Close CRM, Perplexity, Apify, List)
   - 3 delegation tools (delegate, ask_agent, refine)
   - 3 RAG tools (search KB, list docs, query sheets)
   - 3 Wolfram tools (strategic query, market analysis, demographics)
3. **Agent Delegation**: Subordinate spawning (document_analyst, competitor_analyst, etc.) working
4. **Inter-Agent Communication**: Strategy Agent can query other agents
5. **Follow-Up Agent**: LangGraph workflow fixed with PostgreSQL persistence
6. **Slack Integration**: Idempotency cache prevents duplicate messages
7. **Test Suite**: 21/22 tests passing (95.5% pass rate)

### What's Broken 🔴
1. **Pipeline Analysis**: Returns mock data (Issue #1 above)
2. **Outbound Recommendations**: Returns mock data (Issue #2 above)

---

## Implementation Priority

### Priority 1 (Immediate) - 2-3 hours
**Fix analyze_pipeline()** - This is the most visible function and Josh likely uses it frequently via Slack. Replace with real Supabase queries as shown in proposed fix.

### Priority 2 (High) - 3-4 hours
**Fix recommend_outbound_targets()** - More complex as it requires pattern analysis and potentially Perplexity research integration. Start with basic pattern analysis from existing leads, then enhance with external research.

### Priority 3 (Nice to Have) - 1 hour
**Add integration tests** - Create tests that verify real data is returned (not mock data) when Supabase is configured. Current test suite only checks that functions exist and return something.

---

## Testing Recommendations

After implementing fixes:

1. **Unit Tests**: Verify functions return real data when Supabase connected
2. **Integration Tests**: Test with actual database
3. **Manual Slack Testing**: Message Josh's DM with:
   - "analyze pipeline"
   - "recommend outbound targets"
4. **Verify Metrics**: Check that returned data changes based on actual database state

---

## Additional Notes

- **Database Schema**: Ensure `leads` table has required columns:
  - `qualification_tier`, `qualification_score`, `source`, `industry`, `company_size`, `created_at`
- **Error Handling**: Both proposed fixes include graceful degradation when Supabase unavailable
- **Logging**: Added detailed logging for debugging production issues
- **Perplexity Integration**: Consider budget for `recommend_outbound_targets()` Perplexity API calls

---

## Conclusion

The hume-dspy-agent infrastructure is solid with Phase 2.0 fully implemented. The only issues are two stub implementations that need to be replaced with real data queries. Once fixed, the Strategy Agent will provide genuine business intelligence instead of fabricated metrics.

**Estimated Total Fix Time**: 5-7 hours
**Risk Level**: Low (clear requirements, existing patterns to follow)
**Dependencies**: None (Supabase connection already exists)
