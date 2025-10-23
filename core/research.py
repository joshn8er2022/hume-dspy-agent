
"""Lightweight research module for ABM using existing MCPs.

Provides company research, contact discovery, relationship mapping,
and contact enrichment capabilities without Agent Zero dependency.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import httpx
import asyncio
import json
import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import logging

logger = logging.getLogger(__name__)


class CompanyData(BaseModel):
    """Company information model."""
    name: str
    domain: str
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    employees: List[str] = Field(default_factory=list)
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None
    researched_at: Optional[datetime] = None


class ContactData(BaseModel):
    """Contact information model."""
    name: str
    email: Optional[str] = None
    role: Optional[str] = None
    company: str
    company_domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    researched_at: Optional[datetime] = None


class ResearchCache:
    """Simple in-memory cache for research results."""

    def __init__(self, ttl_hours: int = 24):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(hours=ttl_hours)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if not expired."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None

    def set(self, key: str, data: Dict[str, Any]):
        """Cache data with timestamp."""
        self.cache[key] = (data, datetime.now())

    def clear(self):
        """Clear all cached data."""
        self.cache.clear()


class CompanyResearcher:
    """Lightweight research using existing MCPs."""

    def __init__(self, cache_ttl_hours: int = 24):
        """Initialize researcher with optional caching.

        Args:
            cache_ttl_hours: Hours to cache research results (default: 24)
        """
        self.cache = ResearchCache(ttl_hours=cache_ttl_hours)
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("CompanyResearcher initialized")

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search web using DuckDuckGo MCP.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of search results with title, url, snippet
        """
        try:
            # Simulate DuckDuckGo search results
            # In production, this would call the actual MCP
            logger.info(f"Searching: {query}")

            # For now, return mock data structure
            # TODO: Integrate with actual duckduckgo.search MCP tool
            results = []

            # Parse query to determine what we're searching for
            if "site:linkedin.com" in query.lower():
                # LinkedIn search
                results.append({
                    "title": f"LinkedIn search results for {query}",
                    "url": f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(query)}",
                    "snippet": "LinkedIn professional profiles"
                })
            else:
                # General company search
                results.append({
                    "title": f"Search results for {query}",
                    "url": f"https://www.google.com/search?q={quote_plus(query)}",
                    "snippet": "Company information and details"
                })

            return results[:max_results]

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def _extract_domain_info(self, domain: str) -> Dict[str, Any]:
        """Extract basic info from domain using heuristics.

        Args:
            domain: Company domain

        Returns:
            Dict with extracted info
        """
        # Clean domain
        domain = domain.lower().replace('www.', '').replace('http://', '').replace('https://', '')
        domain = domain.split('/')[0]  # Remove path

        # Extract company name from domain (heuristic)
        name_parts = domain.split('.')[0].split('-')
        company_name = ' '.join(word.capitalize() for word in name_parts)

        return {
            "name": company_name,
            "domain": domain,
            "website_url": f"https://{domain}"
        }

    async def research_company(self, domain: str, deep: bool = False) -> CompanyData:
        """Research company using web search and scraping.

        Args:
            domain: Company domain (e.g., 'acme.com')
            deep: If True, do deep research (slower). If False, quick lookup.

        Returns:
            CompanyData with name, industry, size, description, employees
        """
        cache_key = f"company:{domain}"

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached and not deep:
            logger.info(f"Using cached data for {domain}")
            return CompanyData(**cached)

        logger.info(f"Researching company: {domain} (deep={deep})")

        try:
            # 1. Extract basic info from domain
            info = await self._extract_domain_info(domain)

            # 2. Search for company information
            search_query = f"{info['name']} company"
            search_results = await self._search_web(search_query, max_results=3)

            # 3. Extract additional info from search results (heuristic)
            description = None
            industry = None

            if search_results:
                # Use first result snippet as description
                description = search_results[0].get('snippet', '')

                # Try to infer industry from description
                industry_keywords = {
                    'healthcare': ['health', 'medical', 'hospital', 'clinic', 'doctor'],
                    'technology': ['software', 'tech', 'saas', 'cloud', 'ai'],
                    'finance': ['bank', 'financial', 'investment', 'insurance'],
                    'retail': ['retail', 'store', 'shop', 'ecommerce'],
                    'manufacturing': ['manufacturing', 'factory', 'production']
                }

                desc_lower = description.lower()
                for ind, keywords in industry_keywords.items():
                    if any(kw in desc_lower for kw in keywords):
                        industry = ind.capitalize()
                        break

            # 4. If deep research, find employees
            employees = []
            if deep:
                # Search LinkedIn for company employees
                linkedin_query = f"site:linkedin.com {info['name']} employees"
                linkedin_results = await self._search_web(linkedin_query, max_results=5)

                # Extract employee names from results (simplified)
                for result in linkedin_results:
                    # In production, would scrape LinkedIn pages
                    # For now, just note that we found the company
                    if 'linkedin.com/company' in result.get('url', ''):
                        info['linkedin_url'] = result['url']

            # 5. Create CompanyData object
            company_data = CompanyData(
                name=info['name'],
                domain=domain,
                industry=industry,
                size=None,  # Would need LinkedIn scraping
                description=description,
                employees=employees,
                linkedin_url=info.get('linkedin_url'),
                website_url=info['website_url'],
                researched_at=datetime.now()
            )

            # Cache the result
            self.cache.set(cache_key, company_data.model_dump())

            logger.info(f"✅ Researched {company_data.name}")
            return company_data

        except Exception as e:
            logger.error(f"Error researching company {domain}: {e}")
            # Return minimal data on error
            info = await self._extract_domain_info(domain)
            return CompanyData(
                name=info['name'],
                domain=domain,
                website_url=info['website_url'],
                researched_at=datetime.now()
            )

    async def find_contacts(
        self, 
        company_name: str, 
        domain: str, 
        roles: List[str]
    ) -> List[ContactData]:
        """Find contacts at company with specific roles.

        Args:
            company_name: Company name (e.g., 'Acme Corp')
            domain: Company domain (e.g., 'acme.com')
            roles: List of roles to find (e.g., ['doctor', 'admin', 'executive'])

        Returns:
            List of ContactData with name, email, role, linkedin_url
        """
        cache_key = f"contacts:{domain}:{'_'.join(sorted(roles))}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Using cached contacts for {domain}")
            return [ContactData(**c) for c in cached]

        logger.info(f"Finding contacts at {company_name} with roles: {roles}")

        contacts = []

        try:
            # Search for each role
            for role in roles:
                # Search LinkedIn for people with this role at company
                query = f"site:linkedin.com {company_name} {role}"
                results = await self._search_web(query, max_results=3)

                # Extract contact info from results
                for result in results:
                    url = result.get('url', '')
                    title = result.get('title', '')

                    # Extract name from title (heuristic)
                    # LinkedIn titles often like: "John Doe - Doctor at Acme Corp"
                    name_match = re.match(r'^([^-|]+)', title)
                    name = name_match.group(1).strip() if name_match else "Unknown"

                    # Create contact
                    contact = ContactData(
                        name=name,
                        email=None,  # Would need email finder service
                        role=role.capitalize(),
                        company=company_name,
                        company_domain=domain,
                        linkedin_url=url if 'linkedin.com/in/' in url else None,
                        researched_at=datetime.now()
                    )

                    contacts.append(contact)

            # Cache results
            if contacts:
                self.cache.set(cache_key, [c.model_dump() for c in contacts])

            logger.info(f"✅ Found {len(contacts)} contacts at {company_name}")
            return contacts

        except Exception as e:
            logger.error(f"Error finding contacts: {e}")
            return []

    async def enrich_contact(
        self, 
        email: str, 
        name: str, 
        company: str
    ) -> ContactData:
        """Enrich contact information.

        Args:
            email: Contact email
            name: Contact name
            company: Company name

        Returns:
            ContactData with enriched info (role, linkedin_url, interests)
        """
        cache_key = f"contact:{email}"

        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Using cached data for {email}")
            return ContactData(**cached)

        logger.info(f"Enriching contact: {name} ({email})")

        try:
            # Extract domain from email
            domain = email.split('@')[1] if '@' in email else None

            # Search for LinkedIn profile
            query = f"site:linkedin.com {name} {company}"
            results = await self._search_web(query, max_results=3)

            linkedin_url = None
            role = None
            interests = []

            # Extract info from search results
            for result in results:
                url = result.get('url', '')
                if 'linkedin.com/in/' in url:
                    linkedin_url = url

                    # Try to extract role from title
                    title = result.get('title', '')
                    role_match = re.search(r'-\\s*([^|]+?)\s*(?:at|\|)', title)
                    if role_match:
                        role = role_match.group(1).strip()

                    break

            # Create enriched contact
            contact = ContactData(
                name=name,
                email=email,
                role=role,
                company=company,
                company_domain=domain,
                linkedin_url=linkedin_url,
                interests=interests,
                researched_at=datetime.now()
            )

            # Cache result
            self.cache.set(cache_key, contact.model_dump())

            logger.info(f"✅ Enriched contact: {name}")
            return contact

        except Exception as e:
            logger.error(f"Error enriching contact: {e}")
            # Return basic contact on error
            return ContactData(
                name=name,
                email=email,
                company=company,
                company_domain=email.split('@')[1] if '@' in email else None,
                researched_at=datetime.now()
            )

    async def check_relationship(
        self, 
        contact1_email: str, 
        contact2_email: str
    ) -> str:
        """Check if two contacts work together.

        Args:
            contact1_email: First contact email
            contact2_email: Second contact email

        Returns:
            Relationship type: 'colleagues' (same company), 'unknown'
        """
        # Simple heuristic: same email domain = colleagues
        domain1 = contact1_email.split('@')[1] if '@' in contact1_email else ''
        domain2 = contact2_email.split('@')[1] if '@' in contact2_email else ''

        if domain1 and domain1 == domain2:
            logger.info(f"✅ {contact1_email} and {contact2_email} are colleagues")
            return 'colleagues'

        logger.info(f"❓ Relationship unknown between {contact1_email} and {contact2_email}")
        return 'unknown'

    async def batch_research_companies(
        self, 
        domains: List[str], 
        deep: bool = False
    ) -> List[CompanyData]:
        """Research multiple companies in parallel.

        Args:
            domains: List of company domains
            deep: If True, do deep research for all

        Returns:
            List of CompanyData objects
        """
        logger.info(f"Batch researching {len(domains)} companies")

        tasks = [self.research_company(domain, deep=deep) for domain in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        companies = [r for r in results if isinstance(r, CompanyData)]

        logger.info(f"✅ Batch research complete: {len(companies)}/{len(domains)} successful")
        return companies
