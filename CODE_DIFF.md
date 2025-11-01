# Code Diff: recommend_outbound_targets() Bug Fix

## Lines Changed: 1553-1891 (339 new lines)

---

## BEFORE (Lines 1582-1598) - REMOVED ❌

```python
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

**Problem**: Hardcoded fake companies - no real data analysis!

---

## AFTER (Lines 1578-1891) - ADDED ✅

### Part 1: Main Function (Lines 1578-1638)

```python
try:
    # Step 1: Query Supabase for successful leads (meeting_booked, deal_closed)
    if not self.supabase:
        logger.error("❌ Supabase not configured - cannot analyze lead patterns")
        return []

    # Query leads with high success rates
    successful_statuses = ['meeting_booked', 'deal_closed', 'opportunity']
    successful_tiers = ['HOT', 'SCORCHING']

    # Get successful leads
    logger.info("📊 Querying successful leads from Supabase...")
    success_query = self.supabase.table('leads').select('*').or_(
        f"status.in.({','.join(successful_statuses)}),qualification_tier.in.({','.join(successful_tiers)})"
    ).limit(100).execute()

    successful_leads = success_query.data
    logger.info(f"   Found {len(successful_leads)} successful leads")

    if not successful_leads:
        logger.warning("⚠️ No successful leads found - cannot generate recommendations")
        return []

    # Step 2: Analyze patterns using DSPy reasoning
    logger.info("🧠 Analyzing patterns with DSPy...")
    patterns = await self._analyze_lead_patterns(successful_leads)
    logger.info(f"   Identified patterns: {patterns}")

    # Step 3: Use Wolfram Alpha for market intelligence (optional enhancement)
    market_insights = None
    if patterns.get('top_industry'):
        try:
            logger.info(f"🔬 Querying Wolfram Alpha for {patterns['top_industry']} market data...")
            from tools.strategy_tools import wolfram_market_analysis
            market_insights = await wolfram_market_analysis(
                market=patterns['top_industry'],
                metric="market size and growth rate",
                comparison_regions=["United States"]
            )
            logger.info(f"   Market insights: {market_insights[:100]}...")
        except Exception as e:
            logger.warning(f"⚠️ Wolfram Alpha query failed (non-critical): {e}")

    # Step 4: Generate recommendations using DSPy with real patterns
    logger.info("🎯 Generating recommendations with DSPy...")
    recommendations = await self._generate_target_recommendations(
        patterns=patterns,
        market_insights=market_insights,
        segment=segment,
        min_size=min_size,
        limit=limit
    )

    logger.info(f"✅ Generated {len(recommendations)} recommendations from REAL data")
    return recommendations

except Exception as e:
    logger.error(f"❌ Error generating outbound targets: {e}")
    import traceback
    logger.error(traceback.format_exc())
    return []
```

### Part 2: Pattern Analysis (Lines 1640-1713)

```python
async def _analyze_lead_patterns(self, leads: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze patterns in successful leads using DSPy reasoning."""
    try:
        # Extract key attributes
        industries = []
        company_sizes = []
        tech_stacks = []
        revenues = []
        locations = []

        for lead in leads:
            metadata = lead.get('metadata', {})
            if lead.get('company'):
                industries.append(metadata.get('industry', 'unknown'))
            if metadata.get('company_size'):
                company_sizes.append(metadata.get('company_size'))
            # ... more extractions

        # Calculate frequencies
        from collections import Counter
        industry_counts = Counter(industries)
        size_counts = Counter(company_sizes)
        tech_counts = Counter(tech_stacks)
        location_counts = Counter(locations)

        # Calculate average qualification score
        scores = [lead.get('qualification_score', 0) for lead in leads if lead.get('qualification_score')]
        avg_score = sum(scores) / len(scores) if scores else 0

        patterns = {
            'total_analyzed': len(leads),
            'avg_score': avg_score,
            'top_industry': industry_counts.most_common(1)[0][0] if industry_counts else 'healthcare',
            'common_industries': [ind for ind, count in industry_counts.most_common(3)],
            'common_sizes': [size for size, count in size_counts.most_common(3)],
            'common_tech': [tech for tech, count in tech_counts.most_common(5)],
            'top_locations': [loc for loc, count in location_counts.most_common(5)],
            'success_factors': self._identify_success_factors(leads)
        }

        logger.info(f"📊 Pattern analysis: {patterns}")
        return patterns

    except Exception as e:
        logger.error(f"❌ Error analyzing patterns: {e}")
        # Return safe defaults
        return { ... }
```

### Part 3: Success Factors (Lines 1715-1749)

```python
def _identify_success_factors(self, leads: List[Dict[str, Any]]) -> List[str]:
    """Identify common success factors from lead data."""
    factors = []

    for lead in leads:
        metadata = lead.get('metadata', {})
        
        if metadata.get('has_budget'):
            factors.append('Budget confirmed')
        if metadata.get('decision_maker'):
            factors.append('Direct decision maker contact')
        if metadata.get('pain_points'):
            factors.append('Clear pain points identified')
        if lead.get('engagement_score', 0) > 40:
            factors.append('High engagement score')
        if lead.get('business_fit_score', 0) > 40:
            factors.append('Strong business fit')

    from collections import Counter
    factor_counts = Counter(factors)
    return [factor for factor, count in factor_counts.most_common(5)]
```

### Part 4: DSPy Recommendations (Lines 1751-1839)

```python
async def _generate_target_recommendations(
    self,
    patterns: Dict[str, Any],
    market_insights: Optional[str],
    segment: str,
    min_size: int,
    limit: int
) -> List[OutboundTarget]:
    """Generate target recommendations using DSPy reasoning over real patterns."""
    try:
        # Create DSPy signature for recommendation generation
        class OutboundTargetRecommendation(dspy.Signature):
            """Generate outbound target recommendations based on successful lead patterns."""
            patterns = dspy.InputField(desc="Patterns from successful leads")
            market_insights = dspy.InputField(desc="Market intelligence from Wolfram Alpha")
            segment = dspy.InputField(desc="Target segment filter")
            min_size = dspy.InputField(desc="Minimum company size")
            recommendations = dspy.OutputField(desc="JSON list of recommended targets")

        # Use ChainOfThought for reasoning
        recommender = dspy.ChainOfThought(OutboundTargetRecommendation)

        # Format inputs
        patterns_str = json.dumps(patterns, indent=2)
        market_str = market_insights if market_insights else "No market insights available"

        # Generate recommendations with Sonnet 4.5
        with dspy.context(lm=self.sonnet_lm):
            result = recommender(
                patterns=patterns_str,
                market_insights=market_str,
                segment=segment,
                min_size=str(min_size)
            )

        # Parse and return OutboundTarget objects
        # ... (includes JSON parsing and fallback logic)
```

### Part 5: Fallback Method (Lines 1841-1891)

```python
def _create_pattern_based_recommendations(
    self,
    patterns: Dict[str, Any],
    limit: int
) -> List[OutboundTarget]:
    """Create recommendations directly from patterns (fallback method)."""
    targets = []
    
    top_industry = patterns.get('top_industry', 'healthcare')
    success_factors = patterns.get('success_factors', [])
    avg_score = patterns.get('avg_score', 0)

    recommendation_templates = [
        {
            'name_template': f"{top_industry.title()} leader with similar profile",
            'reason': f"Matches successful lead patterns: {', '.join(success_factors[:2])}. Average qualification score: {avg_score:.0f}/100",
            'fit_score': min(95, int(avg_score * 1.1))
        },
        # ... more templates
    ]

    for i, template in enumerate(recommendation_templates[:limit]):
        targets.append(OutboundTarget(
            company_name=f"[Pattern Match {i+1}] {template['name_template']}",
            reason=template['reason'],
            fit_score=template['fit_score'],
            estimated_patient_volume="Based on successful lead pattern analysis",
            contact_info={"note": "Use research tools to identify specific companies"}
        ))

    return targets
```

---

## Summary of Changes

| Metric | Before | After |
|--------|--------|-------|
| **Lines of code** | 16 | 339 |
| **Data source** | Hardcoded | Supabase database |
| **Analysis** | None | Pattern analysis |
| **AI reasoning** | None | DSPy ChainOfThought |
| **Market intelligence** | None | Wolfram Alpha |
| **Error handling** | None | Comprehensive |
| **Functions** | 1 | 5 |

---

## Key Improvements

✅ **Real Data**: Queries Supabase for actual successful leads
✅ **Pattern Analysis**: Extracts industries, sizes, tech, success factors
✅ **AI Reasoning**: Uses DSPy with Claude Sonnet 4.5
✅ **Market Context**: Integrates Wolfram Alpha
✅ **Error Handling**: Comprehensive try/catch blocks
✅ **Logging**: Detailed logging at every step
✅ **Fallback**: Pattern-based recommendations if DSPy fails
✅ **Type Safety**: Maintains proper type hints
✅ **Async**: Proper async/await syntax

---

**Result**: Function now analyzes REAL lead patterns instead of returning fake companies!
