"""
Pytest Configuration and Fixtures

Provides common test fixtures for all test modules including:
- Mock Supabase client
- Mock environment variables
- Sample lead data
- Test database setup/teardown
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import os
from datetime import datetime, timedelta

# Import mock data
from tests.fixtures.mock_leads import (
    MOCK_LEADS_DIVERSE,
    MOCK_LEADS_HEALTHCARE,
    MOCK_LEADS_MINIMAL,
    MOCK_LEADS_EMPTY,
    MOCK_LEADS_WITH_PATTERNS
)


# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """
    Setup test environment variables.

    This fixture runs once per test session and sets up necessary
    environment variables for testing.
    """
    # Save original env vars
    original_env = os.environ.copy()

    # Set test environment variables
    test_env = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_KEY": "test_key_12345",
        "SUPABASE_KEY": "test_key_12345",
        "OPENROUTER_API_KEY": "test_openrouter_key",
        "OPENAI_API_KEY": "test_openai_key",
        "SLACK_BOT_TOKEN": "xoxb-test-token",
        "JOSH_SLACK_DM_CHANNEL": "C12345TEST",
        "A2A_API_KEY": "test_a2a_key",
        "A2A_ENDPOINT": "http://localhost:8080/a2a/introspect",
        # Disable actual external API calls during tests
        "TESTING": "true",
        "PYTEST_CURRENT_TEST": "true",
    }

    os.environ.update(test_env)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# MOCK SUPABASE CLIENT
# ============================================================================

@pytest.fixture
def mock_supabase_client():
    """
    Mock Supabase client for testing.

    Returns a MagicMock configured to simulate Supabase query chains:
    - client.table(name).select().gte().execute()
    - client.table(name).insert().execute()
    - client.table(name).update().execute()
    - client.table(name).delete().execute()

    Usage:
        def test_something(mock_supabase_client):
            agent.supabase = mock_supabase_client
            mock_supabase_client.table.return_value.select.return_value.execute.return_value = Mock(data=[...])
    """
    # Create mock client
    mock_client = MagicMock()

    # Setup default return values for common query patterns
    mock_execute = Mock()
    mock_execute.data = []
    mock_execute.count = 0

    # Setup query chain
    mock_query = Mock()
    mock_query.execute.return_value = mock_execute
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.neq.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.ilike.return_value = mock_query

    mock_table = Mock()
    mock_table.select.return_value = mock_query
    mock_table.insert.return_value = mock_query
    mock_table.update.return_value = mock_query
    mock_table.delete.return_value = mock_query

    mock_client.table.return_value = mock_table

    # RPC function support
    mock_client.rpc.return_value = mock_query

    return mock_client


@pytest.fixture
def mock_supabase_with_data(mock_supabase_client):
    """
    Mock Supabase client pre-configured with MOCK_LEADS_DIVERSE data.

    This is a convenience fixture that configures the mock client
    to return diverse lead data by default.
    """
    mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = Mock(
        data=MOCK_LEADS_DIVERSE
    )
    return mock_supabase_client


# ============================================================================
# MOCK LEAD DATA FIXTURES
# ============================================================================

@pytest.fixture
def mock_leads_data():
    """Returns diverse mock lead data for testing."""
    return MOCK_LEADS_DIVERSE.copy()


@pytest.fixture
def mock_leads_healthcare():
    """Returns healthcare-specific mock lead data."""
    return MOCK_LEADS_HEALTHCARE.copy()


@pytest.fixture
def mock_leads_minimal():
    """Returns minimal mock lead data (single lead)."""
    return MOCK_LEADS_MINIMAL.copy()


@pytest.fixture
def mock_leads_empty():
    """Returns empty lead data for testing zero-lead scenarios."""
    return MOCK_LEADS_EMPTY.copy()


@pytest.fixture
def mock_leads_with_patterns():
    """Returns lead data with clear patterns for recommendation testing."""
    return MOCK_LEADS_WITH_PATTERNS.copy()


# ============================================================================
# MOCK AGENT COMPONENTS
# ============================================================================

@pytest.fixture
def mock_dspy_lm():
    """
    Mock DSPy language model.

    Returns a mock that simulates DSPy LM responses.
    """
    mock_lm = MagicMock()

    # Configure default response
    mock_response = Mock()
    mock_response.response = "Test response from DSPy"
    mock_response.suggested_actions = ""

    mock_lm.return_value = mock_response

    return mock_lm


@pytest.fixture
def mock_audit_agent():
    """
    Mock AuditAgent for testing Strategy Agent delegation.
    """
    mock_agent = MagicMock()

    # Configure audit_lead_flow method
    async def mock_audit_lead_flow(timeframe_hours=24):
        return {
            "timeframe_hours": timeframe_hours,
            "lead_capture": {
                "total_leads": 10,
                "by_tier": {"HOT": 3, "WARM": 4, "COOL": 2, "COLD": 1}
            },
            "email_campaigns": {
                "sent": 50,
                "delivered": 48,
                "opened": 25,
                "clicked": 10
            }
        }

    mock_agent.audit_lead_flow = AsyncMock(side_effect=mock_audit_lead_flow)

    # Configure format_audit_report method
    def mock_format_report(audit_data):
        return f"Audit Report: {audit_data['timeframe_hours']} hours"

    mock_agent.format_audit_report = Mock(side_effect=mock_format_report)

    return mock_agent


@pytest.fixture
def mock_inbound_agent():
    """Mock InboundAgent for testing."""
    mock_agent = MagicMock()

    async def mock_qualify(lead_data):
        return {
            "tier": "HOT",
            "score": 85,
            "qualification_complete": True
        }

    mock_agent.qualify_lead = AsyncMock(side_effect=mock_qualify)

    return mock_agent


@pytest.fixture
def mock_research_agent():
    """Mock ResearchAgent for testing."""
    mock_agent = MagicMock()

    async def mock_research(company_name):
        return {
            "company": company_name,
            "employee_count": 50,
            "industry": "healthcare",
            "contacts": []
        }

    mock_agent.research_company = AsyncMock(side_effect=mock_research)

    return mock_agent


# ============================================================================
# MOCK EXTERNAL SERVICES
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """
    Mock OpenAI client for embeddings.
    """
    mock_client = AsyncMock()

    # Mock embeddings.create response
    mock_embedding_response = Mock()
    mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
    mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

    return mock_client


@pytest.fixture
def mock_slack_client():
    """
    Mock Slack client for message posting.
    """
    mock_client = AsyncMock()

    # Mock chat.postMessage response
    async def mock_post_message(*args, **kwargs):
        return {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C12345TEST"
        }

    mock_client.chat_postMessage = AsyncMock(side_effect=mock_post_message)

    return mock_client


# ============================================================================
# ASYNC TEST SUPPORT
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for async tests.

    This fixture ensures async tests work properly with pytest-asyncio.
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# TEST DATABASE HELPERS
# ============================================================================

@pytest.fixture
def clean_database(mock_supabase_client):
    """
    Fixture that provides a clean database state for each test.

    Usage:
        def test_something(clean_database):
            # Database is clean at start
            # Run test
            pass
            # Database cleaned up after
    """
    # Setup: Clear any test data
    yield mock_supabase_client

    # Teardown: Could add cleanup logic here if needed
    pass


# ============================================================================
# PATCHING HELPERS
# ============================================================================

@pytest.fixture
def patch_supabase():
    """
    Patch Supabase client creation to return mock.

    Usage:
        def test_something(patch_supabase, mock_supabase_client):
            with patch_supabase(mock_supabase_client):
                # Code that creates Supabase client will get mock
                agent = StrategyAgent()
                # agent.supabase is now the mock
    """
    def _patch(mock_client):
        return patch('supabase.create_client', return_value=mock_client)

    return _patch


# ============================================================================
# TIME MANIPULATION
# ============================================================================

@pytest.fixture
def freeze_time():
    """
    Freeze time for testing time-dependent logic.

    Usage:
        def test_something(freeze_time):
            with freeze_time("2024-01-15 10:00:00"):
                # Time is frozen at specified datetime
                result = some_time_dependent_function()
    """
    try:
        from freezegun import freeze_time as _freeze_time
        return _freeze_time
    except ImportError:
        # Return a no-op context manager if freezegun not installed
        from contextlib import contextmanager

        @contextmanager
        def _freeze_time(*args, **kwargs):
            yield

        return _freeze_time


# ============================================================================
# ASSERTION HELPERS
# ============================================================================

@pytest.fixture
def assert_no_mock_data():
    """
    Helper to assert that results don't contain mock/fake data.

    Usage:
        def test_something(assert_no_mock_data):
            result = agent.analyze_pipeline()
            assert_no_mock_data(result)
    """
    def _assert_no_mock_data(data):
        """Assert data doesn't contain known mock/fake patterns."""
        forbidden_patterns = [
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

        # Convert data to string for searching
        import json
        data_str = json.dumps(data) if not isinstance(data, str) else data

        for pattern in forbidden_patterns:
            assert pattern not in data_str, \
                f"Found forbidden mock pattern: '{pattern}'"

    return _assert_no_mock_data


# ============================================================================
# TEST MARKERS
# ============================================================================

def pytest_configure(config):
    """
    Register custom markers.
    """
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires external services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (fast, no external deps)"
    )
    config.addinivalue_line(
        "markers", "bug_fix: mark test as verifying a specific bug fix"
    )


# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_runtest_setup(item):
    """
    Setup hook that runs before each test.

    Can be used to:
    - Skip tests based on markers
    - Setup test-specific environment
    - Log test start
    """
    # Log test start
    print(f"\n{'='*80}")
    print(f"Running: {item.name}")
    print(f"{'='*80}")


def pytest_runtest_teardown(item):
    """
    Teardown hook that runs after each test.

    Can be used to:
    - Clean up resources
    - Log test completion
    - Verify no leaked state
    """
    pass


# ============================================================================
# REPORTING
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def test_run_summary(request):
    """
    Print test run summary at end of session.
    """
    yield

    # Print summary after all tests
    print("\n" + "="*80)
    print("TEST RUN COMPLETE")
    print("="*80)
