"""
Integration Tests for Strategy Agent Bug Fixes

These tests verify the two critical bugs are fixed and stay fixed:
1. analyze_pipeline returns REAL data (not mock data)
2. recommend_targets returns REAL companies (not fake companies)

Test Suite:
- test_analyze_pipeline_returns_real_data: Verify no mock/hardcoded data
- test_analyze_pipeline_queries_supabase: Verify Supabase is called
- test_recommend_targets_returns_real_companies: Verify no fake companies
- test_recommend_targets_analyzes_patterns: Verify pattern analysis logic
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Import the Strategy Agent
from agents.strategy_agent import StrategyAgent, PipelineAnalysis, OutboundTarget


class TestAnalyzePipelineFixes:
    """Tests for analyze_pipeline() bug fixes"""

    @pytest.mark.asyncio
    async def test_analyze_pipeline_returns_real_data(self, mock_supabase_client, mock_leads_data):
        """
        CRITICAL TEST: Verify analyze_pipeline returns REAL data from Supabase.

        This test ensures the bug is fixed where analyze_pipeline was returning
        mock/hardcoded data instead of querying actual database.

        Assertions:
        - Must query Supabase
        - Must NOT contain mock company names
        - Must reflect actual data from database query
        """
        # Setup: Create agent with mocked Supabase
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        # Configure mock to return test data
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=mock_leads_data
        )

        # Execute: Call analyze_pipeline
        result = await agent.analyze_pipeline(days=7)

        # Verify: Results should be based on REAL data
        assert isinstance(result, PipelineAnalysis)
        assert result.total_leads == len(mock_leads_data), "Total leads must match actual data count"

        # CRITICAL: Verify no mock/fake data patterns
        mock_companies = [
            "West Coast Weight Loss Center",
            "Precision Health Clinic",
            "Example Corp",
            "Mock Company",
            "Test Clinic"
        ]

        # Check insights don't contain mock company names
        insights_text = " ".join(result.insights)
        for mock_name in mock_companies:
            assert mock_name not in insights_text, f"Found mock company '{mock_name}' in insights - data is NOT real!"

        # Check top_industries contains actual data patterns
        if result.top_industries:
            for industry in result.top_industries:
                assert industry != "Mock Industry", "Found mock industry data"
                assert len(industry) > 0, "Industry name should not be empty"

        # Verify tier counts match actual data distribution
        expected_hot_count = sum(1 for lead in mock_leads_data if lead.get('tier') in ['HOT', 'SCORCHING'])
        actual_hot_count = result.by_tier.get('HOT', 0) + result.by_tier.get('SCORCHING', 0)
        assert actual_hot_count == expected_hot_count, "HOT lead count must match actual data"

        print("✅ analyze_pipeline returns REAL data (no mock data found)")

    @pytest.mark.asyncio
    async def test_analyze_pipeline_queries_supabase(self, mock_supabase_client, mock_leads_data):
        """
        CRITICAL TEST: Verify analyze_pipeline actually queries Supabase.

        This test ensures the method calls Supabase, not just returning hardcoded values.

        Assertions:
        - Supabase client.table() is called
        - Query filters by date range
        - Query executes and returns data
        """
        # Setup
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        # Mock the Supabase query chain
        mock_execute = Mock(data=mock_leads_data)
        mock_gte = Mock()
        mock_gte.execute.return_value = mock_execute
        mock_select = Mock()
        mock_select.gte.return_value = mock_gte
        mock_table = Mock()
        mock_table.select.return_value = mock_select
        mock_supabase_client.table.return_value = mock_table

        # Execute
        result = await agent.analyze_pipeline(days=7)

        # Verify: Supabase was queried
        mock_supabase_client.table.assert_called_once()
        table_name = mock_supabase_client.table.call_args[0][0]
        assert table_name == 'raw_events', f"Should query 'raw_events' table, got '{table_name}'"

        # Verify: Query used date filtering
        mock_select.gte.assert_called_once()
        filter_call = mock_select.gte.call_args
        assert filter_call[0][0] == 'created_at', "Should filter by created_at column"

        # Verify: Date range is correct
        date_arg = filter_call[0][1]
        expected_date = (datetime.now() - timedelta(days=7)).isoformat()
        # Check date is within 1 second (account for test execution time)
        assert abs((datetime.fromisoformat(date_arg) - datetime.fromisoformat(expected_date)).total_seconds()) < 1

        # Verify: Execute was called
        mock_gte.execute.assert_called_once()

        print("✅ analyze_pipeline queries Supabase correctly")

    @pytest.mark.asyncio
    async def test_analyze_pipeline_handles_empty_data(self, mock_supabase_client):
        """
        Test analyze_pipeline handles empty/no data gracefully.

        Edge case: What happens when there are no leads?
        """
        # Setup
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        # Mock empty results
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=[]
        )

        # Execute
        result = await agent.analyze_pipeline(days=7)

        # Verify: Handles empty data
        assert result.total_leads == 0
        assert len(result.insights) > 0, "Should provide insights even with no data"
        assert any("No leads" in insight for insight in result.insights), "Should mention no leads in insights"

        print("✅ analyze_pipeline handles empty data gracefully")

    @pytest.mark.asyncio
    async def test_analyze_pipeline_calculates_correct_metrics(self, mock_supabase_client, mock_leads_data):
        """
        Test analyze_pipeline calculates metrics correctly from real data.

        Verifies:
        - Tier counts are accurate
        - Source counts are accurate
        - Conversion rate is calculated correctly
        """
        # Setup
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=mock_leads_data
        )

        # Execute
        result = await agent.analyze_pipeline(days=7)

        # Verify tier counts
        for tier in ['HOT', 'WARM', 'COOL', 'COLD']:
            expected_count = sum(1 for lead in mock_leads_data if lead.get('tier') == tier)
            actual_count = result.by_tier.get(tier, 0)
            assert actual_count == expected_count, f"{tier} count mismatch: expected {expected_count}, got {actual_count}"

        # Verify source counts
        sources = set(lead.get('source', 'unknown') for lead in mock_leads_data)
        for source in sources:
            expected_count = sum(1 for lead in mock_leads_data if lead.get('source') == source)
            actual_count = result.by_source.get(source, 0)
            assert actual_count == expected_count, f"{source} count mismatch"

        # Verify conversion rate
        total = len(mock_leads_data)
        hot_leads = sum(1 for lead in mock_leads_data if lead.get('tier') in ['HOT', 'SCORCHING'])
        expected_rate = hot_leads / total if total > 0 else 0
        assert abs(result.conversion_rate - expected_rate) < 0.001, f"Conversion rate mismatch: expected {expected_rate}, got {result.conversion_rate}"

        print("✅ analyze_pipeline calculates metrics correctly")


class TestRecommendTargetsFixes:
    """Tests for recommend_outbound_targets() bug fixes"""

    @pytest.mark.asyncio
    async def test_recommend_targets_returns_real_companies(self, mock_supabase_client, mock_leads_data):
        """
        CRITICAL TEST: Verify recommend_targets returns REAL companies.

        This test ensures the bug is fixed where recommend_targets was returning
        hardcoded fake companies instead of analyzing actual patterns.

        Assertions:
        - Must NOT contain mock company names
        - Must analyze actual lead patterns
        - Must derive targets from real data
        """
        # Setup
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=mock_leads_data
        )

        # Execute
        result = await agent.recommend_outbound_targets(segment="all", min_size=50, limit=10)

        # Verify: Results are OutboundTarget objects
        assert isinstance(result, list)
        for target in result:
            assert isinstance(target, OutboundTarget)

        # CRITICAL: Verify NO fake/mock companies
        fake_companies = [
            "West Coast Weight Loss Center",
            "Precision Health Clinic",
            "Example Corp",
            "Mock Company",
            "Test Clinic",
            "Acme Corporation",
            "Sample Inc"
        ]

        for target in result:
            assert target.company_name not in fake_companies, \
                f"Found fake company '{target.company_name}' - data is NOT real!"

            # Verify company names are realistic (not obviously fake)
            assert len(target.company_name) > 3, "Company name too short"
            assert not target.company_name.startswith("Test"), "Company name looks like test data"
            assert not target.company_name.startswith("Mock"), "Company name looks like mock data"

        print("✅ recommend_targets returns REAL companies (no fake data found)")

    @pytest.mark.asyncio
    async def test_recommend_targets_analyzes_patterns(self, mock_supabase_client, mock_leads_data):
        """
        CRITICAL TEST: Verify recommend_targets analyzes actual lead patterns.

        This test ensures the method:
        1. Queries actual leads from database
        2. Identifies patterns (industries, sizes, use cases)
        3. Generates recommendations based on those patterns

        Assertions:
        - Must query Supabase for leads
        - Recommendations should reference actual pattern analysis
        - Fit scores should be calculated from data
        """
        # Setup
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        # Mock leads with clear patterns
        patterned_leads = [
            {"tier": "HOT", "company": "Wellness Clinic A", "industry": "healthcare", "patient_volume": 200},
            {"tier": "HOT", "company": "Wellness Clinic B", "industry": "healthcare", "patient_volume": 250},
            {"tier": "HOT", "company": "Wellness Clinic C", "industry": "healthcare", "patient_volume": 180},
            {"tier": "WARM", "company": "Other Business", "industry": "other", "patient_volume": 50},
        ]

        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=patterned_leads
        )

        # Execute
        result = await agent.recommend_outbound_targets(segment="all", min_size=50, limit=10)

        # Verify: Pattern analysis in reasons
        assert len(result) > 0, "Should return recommendations"

        for target in result:
            # Fit score should be meaningful (not just random)
            assert 0 <= target.fit_score <= 100, f"Fit score out of range: {target.fit_score}"

            # Reason should reference analysis
            reason_lower = target.reason.lower()
            assert len(target.reason) > 20, "Reason should be detailed"

            # Reason should NOT be generic/template
            generic_phrases = [
                "similar to our top-performing",
                "uses inbody (competitor)",
                "perfect for competitive displacement"
            ]
            # At least one reason should be non-generic OR contain data-specific details
            is_generic = any(phrase in reason_lower for phrase in generic_phrases)
            has_specifics = any(keyword in reason_lower for keyword in ['healthcare', 'wellness', 'clinic', 'patient'])

            # Either non-generic OR has specific details from pattern analysis
            assert not is_generic or has_specifics, \
                f"Reason appears too generic/templated: {target.reason}"

        print("✅ recommend_targets analyzes patterns correctly")

    @pytest.mark.asyncio
    async def test_recommend_targets_respects_filters(self, mock_supabase_client, mock_leads_data):
        """
        Test recommend_targets respects segment and size filters.

        Verifies:
        - Filters by segment when specified
        - Respects min_size parameter
        - Respects limit parameter
        """
        # Setup
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=mock_leads_data
        )

        # Execute with limit
        result = await agent.recommend_outbound_targets(segment="all", min_size=100, limit=5)

        # Verify limit is respected
        assert len(result) <= 5, f"Should return max 5 results, got {len(result)}"

        # Verify min_size filter (if patient volume is included)
        for target in result:
            if target.estimated_patient_volume:
                # Parse volume (handle formats like "200-300" or "200+")
                volume_str = target.estimated_patient_volume.replace('+', '').split('-')[0]
                if volume_str.isdigit():
                    min_volume = int(volume_str)
                    assert min_volume >= 100, f"Target volume {min_volume} below min_size 100"

        print("✅ recommend_targets respects filters")

    @pytest.mark.asyncio
    async def test_recommend_targets_handles_no_patterns(self, mock_supabase_client):
        """
        Test recommend_targets handles case with no clear patterns.

        Edge case: What happens when there's insufficient data for pattern analysis?
        """
        # Setup
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        # Mock very limited data
        limited_data = [
            {"tier": "COLD", "company": "Random Co", "industry": "unknown", "patient_volume": 10}
        ]

        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=limited_data
        )

        # Execute
        result = await agent.recommend_outbound_targets(segment="all", min_size=50, limit=10)

        # Verify: Should still return results (even if based on broad criteria)
        # OR return empty list with appropriate handling
        assert isinstance(result, list)

        # If results returned, they should still be valid
        for target in result:
            assert isinstance(target, OutboundTarget)
            assert len(target.company_name) > 0
            assert len(target.reason) > 0

        print("✅ recommend_targets handles no patterns gracefully")


class TestIntegrationEnd2End:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_full_pipeline_analysis_workflow(self, mock_supabase_client, mock_leads_data):
        """
        Full workflow test: Analyze pipeline -> Generate recommendations

        This tests the complete flow to ensure both methods work together correctly.
        """
        # Setup
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=mock_leads_data
        )

        # Execute full workflow
        # 1. Analyze pipeline
        analysis = await agent.analyze_pipeline(days=7)

        # 2. Use analysis to inform recommendations
        targets = await agent.recommend_outbound_targets(segment="all", min_size=50, limit=10)

        # Verify: Analysis produced useful data
        assert analysis.total_leads > 0
        assert len(analysis.by_tier) > 0

        # Verify: Recommendations were generated
        assert isinstance(targets, list)

        # Verify: Data consistency
        # If we have HOT leads in analysis, recommendations should reference high-quality patterns
        if analysis.by_tier.get('HOT', 0) > 0:
            # At least some targets should have high fit scores
            fit_scores = [t.fit_score for t in targets if hasattr(t, 'fit_score')]
            if fit_scores:
                assert max(fit_scores) >= 75, "With HOT leads, should have high-fit recommendations"

        print("✅ Full workflow: pipeline analysis -> recommendations works correctly")


# Test for regression prevention
class TestRegressionPrevention:
    """Tests to prevent regression of fixed bugs"""

    @pytest.mark.asyncio
    async def test_no_mock_data_regression(self, mock_supabase_client, mock_leads_data):
        """
        REGRESSION TEST: Ensure mock data never returns.

        This test should fail if anyone reintroduces mock/hardcoded data.
        """
        agent = StrategyAgent()
        agent.supabase = mock_supabase_client

        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
            data=mock_leads_data
        )

        # Test both methods
        analysis = await agent.analyze_pipeline(days=7)
        targets = await agent.recommend_outbound_targets(segment="all", min_size=50, limit=10)

        # Define ALL known mock/fake data patterns
        FORBIDDEN_PATTERNS = [
            "West Coast Weight Loss Center",
            "Precision Health Clinic",
            "Example Corp",
            "Mock Company",
            "Test Clinic",
            "Acme Corporation",
            "Sample Inc",
            "Fake Company",
            "Demo Corp",
            "TODO:",
            "FIXME:",
            "placeholder",
            "mock data",
            "fake data"
        ]

        # Check analysis
        analysis_text = json.dumps(analysis.model_dump())
        for pattern in FORBIDDEN_PATTERNS:
            assert pattern not in analysis_text, \
                f"REGRESSION: Found forbidden pattern '{pattern}' in analysis!"

        # Check targets
        targets_text = json.dumps([t.model_dump() for t in targets])
        for pattern in FORBIDDEN_PATTERNS:
            assert pattern not in targets_text, \
                f"REGRESSION: Found forbidden pattern '{pattern}' in targets!"

        print("✅ No mock data regression detected")
