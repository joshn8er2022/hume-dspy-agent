
"""Unit tests for research module."""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from core.research import (
    CompanyData,
    ContactData,
    CompanyResearcher,
    ResearchCache
)


class TestResearchCache:
    """Test research cache functionality."""

    def test_cache_set_get(self):
        """Test basic cache operations."""
        cache = ResearchCache(ttl_hours=1)

        # Set data
        cache.set("test_key", {"name": "Test Company"})

        # Get data
        result = cache.get("test_key")
        assert result is not None
        assert result["name"] == "Test Company"

    def test_cache_expiry(self):
        """Test cache expiration."""
        cache = ResearchCache(ttl_hours=0)  # Immediate expiry

        cache.set("test_key", {"name": "Test"})

        # Should be expired
        import time
        time.sleep(0.1)
        result = cache.get("test_key")
        assert result is None

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = ResearchCache()

        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestCompanyData:
    """Test CompanyData model."""

    def test_company_data_creation(self):
        """Test creating CompanyData object."""
        company = CompanyData(
            name="Acme Corp",
            domain="acme.com",
            industry="Technology",
            size="100-500",
            description="A technology company"
        )

        assert company.name == "Acme Corp"
        assert company.domain == "acme.com"
        assert company.industry == "Technology"
        assert company.size == "100-500"
        assert company.description == "A technology company"
        assert company.employees == []

    def test_company_data_with_employees(self):
        """Test CompanyData with employee list."""
        company = CompanyData(
            name="Test Co",
            domain="test.com",
            employees=["John Doe", "Jane Smith"]
        )

        assert len(company.employees) == 2
        assert "John Doe" in company.employees


class TestContactData:
    """Test ContactData model."""

    def test_contact_data_creation(self):
        """Test creating ContactData object."""
        contact = ContactData(
            name="John Doe",
            email="john@acme.com",
            role="Doctor",
            company="Acme Corp",
            linkedin_url="https://linkedin.com/in/johndoe"
        )

        assert contact.name == "John Doe"
        assert contact.email == "john@acme.com"
        assert contact.role == "Doctor"
        assert contact.company == "Acme Corp"
        assert contact.linkedin_url == "https://linkedin.com/in/johndoe"
        assert contact.interests == []

    def test_contact_data_with_interests(self):
        """Test ContactData with interests."""
        contact = ContactData(
            name="Jane Smith",
            company="Test Co",
            interests=["AI", "Healthcare", "Technology"]
        )

        assert len(contact.interests) == 3
        assert "AI" in contact.interests


class TestCompanyResearcher:
    """Test CompanyResearcher functionality."""

    @pytest_asyncio.fixture
    async def researcher(self):
        """Create researcher instance."""
        r = CompanyResearcher(cache_ttl_hours=1)
        yield r
        await r.close()

    @pytest.mark.asyncio
    async def test_research_company_basic(self, researcher):
        """Test basic company research."""
        company = await researcher.research_company("acme.com", deep=False)

        assert isinstance(company, CompanyData)
        assert company.domain == "acme.com"
        assert company.name  # Should have extracted name
        assert company.website_url
        assert company.researched_at is not None

    @pytest.mark.asyncio
    async def test_research_company_caching(self, researcher):
        """Test that company research uses cache."""
        # First research
        company1 = await researcher.research_company("test.com")

        # Second research (should use cache)
        company2 = await researcher.research_company("test.com")

        assert company1.name == company2.name
        assert company1.researched_at == company2.researched_at

    @pytest.mark.asyncio
    async def test_find_contacts(self, researcher):
        """Test finding contacts at company."""
        contacts = await researcher.find_contacts(
            company_name="Acme Corp",
            domain="acme.com",
            roles=["doctor", "admin"]
        )

        assert isinstance(contacts, list)
        # May be empty in test environment, but should not error

    @pytest.mark.asyncio
    async def test_enrich_contact(self, researcher):
        """Test contact enrichment."""
        contact = await researcher.enrich_contact(
            email="john@acme.com",
            name="John Doe",
            company="Acme Corp"
        )

        assert isinstance(contact, ContactData)
        assert contact.name == "John Doe"
        assert contact.email == "john@acme.com"
        assert contact.company == "Acme Corp"
        assert contact.company_domain == "acme.com"

    @pytest.mark.asyncio
    async def test_check_relationship_colleagues(self, researcher):
        """Test relationship check for colleagues."""
        relationship = await researcher.check_relationship(
            "john@acme.com",
            "jane@acme.com"
        )

        assert relationship == "colleagues"

    @pytest.mark.asyncio
    async def test_check_relationship_unknown(self, researcher):
        """Test relationship check for different companies."""
        relationship = await researcher.check_relationship(
            "john@acme.com",
            "jane@other.com"
        )

        assert relationship == "unknown"

    @pytest.mark.asyncio
    async def test_batch_research(self, researcher):
        """Test batch company research."""
        domains = ["acme.com", "test.com", "example.com"]

        companies = await researcher.batch_research_companies(domains)

        assert isinstance(companies, list)
        assert len(companies) <= len(domains)  # May have some failures

        for company in companies:
            assert isinstance(company, CompanyData)
            assert company.domain in domains

    @pytest.mark.asyncio
    async def test_extract_domain_info(self, researcher):
        """Test domain info extraction."""
        # Test various domain formats
        info1 = await researcher._extract_domain_info("acme.com")
        assert info1["domain"] == "acme.com"
        assert info1["name"] == "Acme"

        info2 = await researcher._extract_domain_info("www.acme-corp.com")
        assert info2["domain"] == "acme-corp.com"
        assert "Acme" in info2["name"]

        info3 = await researcher._extract_domain_info("https://example.com/path")
        assert info3["domain"] == "example.com"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
