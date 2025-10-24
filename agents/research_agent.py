"""Research Agent for Deep Lead Intelligence Gathering.

This agent performs deep research on leads and companies using:
- MCP tools (Firecrawl, Perplexity, web search)
- External APIs (Clearbit, Apollo, LinkedIn)
- Public data sources (company websites, news, social media)

The Research Agent enriches lead data to enable account-based engagement strategies.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import httpx
import os
import dspy

logger = logging.getLogger(__name__)


# ===== DSPy Signatures =====

class ResearchPlanning(dspy.Signature):
    """Plan research strategy for a lead.
    
    Given information about a lead, determine what research to conduct
    and prioritize information gathering steps.
    """
    lead_info: str = dspy.InputField(desc="Available information about the lead")
    research_goals: str = dspy.InputField(desc="What information we need")
    
    research_plan: str = dspy.OutputField(desc="Step-by-step research plan")
    priority_targets: str = dspy.OutputField(desc="High-priority information to find")


class ResearchSynthesis(dspy.Signature):
    """Synthesize research findings into actionable insights.
    
    Analyze collected data and generate strategic recommendations
    for engaging with the lead.
    """
    person_data: str = dspy.InputField(desc="Information about the person")
    company_data: str = dspy.InputField(desc="Information about the company")
    
    key_insights: str = dspy.OutputField(desc="Key insights from research")
    engagement_strategy: str = dspy.OutputField(desc="Recommended engagement approach")
    talking_points: str = dspy.OutputField(desc="Relevant talking points for outreach")


# ===== Data Models =====

class PersonProfile(BaseModel):
    """Enriched person profile from research."""
    name: str
    email: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    social_presence: Dict[str, str] = Field(default_factory=dict)
    recent_activity: List[str] = Field(default_factory=list)
    research_timestamp: datetime = Field(default_factory=datetime.utcnow)


class CompanyProfile(BaseModel):
    """Enriched company profile from research."""
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None
    description: Optional[str] = None
    funding_stage: Optional[str] = None
    total_funding: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    social_links: Dict[str, str] = Field(default_factory=dict)
    recent_news: List[Dict[str, str]] = Field(default_factory=list)
    competitors: List[str] = Field(default_factory=list)
    key_decision_makers: List[Dict[str, str]] = Field(default_factory=list)
    research_timestamp: datetime = Field(default_factory=datetime.utcnow)


class Contact(BaseModel):
    """Additional contact at a company."""
    name: str
    email: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    department: Optional[str] = None
    seniority: Optional[str] = None


class ResearchResult(BaseModel):
    """Combined research result."""
    lead_id: str
    person_profile: Optional[PersonProfile] = None
    company_profile: Optional[CompanyProfile] = None
    additional_contacts: List[Contact] = Field(default_factory=list)
    research_score: int = Field(0, description="Quality score 0-100")
    research_summary: str = ""
    actionable_insights: List[str] = Field(default_factory=list)


# ===== Research Agent =====

class ResearchAgent(dspy.Module):
    """Agent for conducting deep research on leads and companies.
    
    Refactored as dspy.Module for better architecture and DSPy optimization.
    Phase 0.3 - October 19, 2025
    """
    
    def __init__(self):
        super().__init__()  # Initialize dspy.Module
        
        # DSPy modules for research workflow
        self.plan_research = dspy.ChainOfThought(ResearchPlanning)
        self.synthesize_findings = dspy.ChainOfThought(ResearchSynthesis)
        self.clearbit_api_key = os.getenv("CLEARBIT_API_KEY")
        self.apollo_api_key = os.getenv("APOLLO_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        
        logger.info("🔍 Research Agent initialized")
        logger.info("   DSPy Modules: ✅ Research planning + synthesis")
        if self.clearbit_api_key:
            logger.info("   ✅ Clearbit API configured")
        if self.apollo_api_key:
            logger.info("   ✅ Apollo API configured")
        if self.perplexity_api_key:
            logger.info("   ✅ Perplexity API configured")
    
    def forward(
        self,
        lead_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """DSPy Module forward pass - main entry point.
        
        This is the standard dspy.Module interface that enables:
        - DSPy compilation/optimization
        - Consistent API across all modules
        - Better composability
        
        Args:
            lead_id: Lead UUID
            name: Person's name
            email: Person's email  
            company: Company name
        
        Returns:
            Dict with research results
        """
        # Forward() is a sync wrapper around async research_lead_deeply
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context
                return loop.create_task(
                    self.research_lead_deeply(
                        lead_id=lead_id,
                        name=name,
                        email=email,
                        company=company
                    )
                )
            else:
                # We're in sync context
                return loop.run_until_complete(
                    self.research_lead_deeply(
                        lead_id=lead_id,
                        name=name,
                        email=email,
                        company=company
                    )
                )
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(
                self.research_lead_deeply(
                    lead_id=lead_id,
                    name=name,
                    email=email,
                    company=company
                )
            )
    
    async def research_lead_deeply(
        self,
        lead_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        include_company_intel: bool = True,
        find_additional_contacts: bool = True
    ) -> ResearchResult:
        """Perform comprehensive research on a lead.
        
        Args:
            lead_id: Lead UUID
            name: Person's name
            email: Person's email
            company: Company name
            include_company_intel: Whether to research the company
            find_additional_contacts: Whether to find co-workers
        
        Returns:
            ResearchResult with enriched data
        """
        logger.info(f"🔍 Starting deep research for lead: {lead_id}")
        
        tasks = []
        
        # Research the person
        if name or email:
            tasks.append(self.research_person(name, email, company))
        
        # Research the company
        if company and include_company_intel:
            tasks.append(self.research_company(company))
        
        # Execute research in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        person_profile = None
        company_profile = None
        additional_contacts = []
        
        # Parse results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Research task failed: {str(result)}")
                continue
            
            if isinstance(result, PersonProfile):
                person_profile = result
            elif isinstance(result, CompanyProfile):
                company_profile = result
        
        # Find additional contacts if requested
        if find_additional_contacts and company:
            try:
                additional_contacts = await self.find_additional_contacts(company)
            except Exception as e:
                logger.error(f"Failed to find contacts: {str(e)}")
        
        # Calculate research score
        research_score = self._calculate_research_score(
            person_profile,
            company_profile,
            additional_contacts
        )
        
        # Generate insights
        insights = self._generate_insights(
            person_profile,
            company_profile,
            additional_contacts
        )
        
        # Create summary
        summary = self._create_summary(person_profile, company_profile)
        
        result = ResearchResult(
            lead_id=lead_id,
            person_profile=person_profile,
            company_profile=company_profile,
            additional_contacts=additional_contacts,
            research_score=research_score,
            research_summary=summary,
            actionable_insights=insights
        )
        
        logger.info(f"✅ Research complete for lead: {lead_id}")
        logger.info(f"   Score: {research_score}/100")
        logger.info(f"   Insights: {len(insights)}")
        
        return result
    
    async def research_person(
        self,
        name: Optional[str],
        email: Optional[str],
        company: Optional[str] = None
    ) -> PersonProfile:
        """Research an individual person.
        
        Uses:
        1. Clearbit Person API (email enrichment)
        2. Google/Perplexity search for LinkedIn profile
        3. Web scraping for professional info
        """
        logger.info(f"🔍 Researching person: {name} ({email})")
        
        profile_data = {
            "name": name or "Unknown",
            "email": email,
            "company": company
        }
        
        # Try Clearbit enrichment if we have email
        if email and self.clearbit_api_key:
            try:
                clearbit_data = await self._clearbit_person_lookup(email)
                if clearbit_data:
                    profile_data.update(clearbit_data)
                    logger.info("   ✅ Clearbit enrichment successful")
            except Exception as e:
                logger.warning(f"   ⚠️ Clearbit failed: {str(e)}")
        
        # Search for LinkedIn profile
        if name and company:
            try:
                linkedin_url = await self._find_linkedin_profile(name, company)
                if linkedin_url:
                    profile_data["linkedin_url"] = linkedin_url
                    logger.info(f"   ✅ Found LinkedIn: {linkedin_url}")
            except Exception as e:
                logger.warning(f"   ⚠️ LinkedIn search failed: {str(e)}")
        
        # Search for recent activity (news, social media)
        if name and company:
            try:
                activity = await self._find_recent_activity(name, company)
                profile_data["recent_activity"] = activity
            except Exception as e:
                logger.warning(f"   ⚠️ Activity search failed: {str(e)}")
        
        return PersonProfile(**profile_data)
    
    async def research_company(
        self,
        company_name: str,
        domain: Optional[str] = None
    ) -> CompanyProfile:
        """Research a company.
        
        Uses:
        1. Clearbit Company API
        2. BuiltWith tech stack analysis
        3. News search for recent developments
        4. Competitor analysis
        """
        logger.info(f"🔍 Researching company: {company_name}")
        
        profile_data = {
            "name": company_name,
            "domain": domain
        }
        
        # Try Clearbit company enrichment
        if self.clearbit_api_key:
            try:
                clearbit_data = await self._clearbit_company_lookup(company_name, domain)
                if clearbit_data:
                    profile_data.update(clearbit_data)
                    logger.info("   ✅ Clearbit company enrichment successful")
            except Exception as e:
                logger.warning(f"   ⚠️ Clearbit company failed: {str(e)}")
        
        # Search for recent news
        try:
            news = await self._find_company_news(company_name)
            profile_data["recent_news"] = news
            logger.info(f"   ✅ Found {len(news)} recent news items")
        except Exception as e:
            logger.warning(f"   ⚠️ News search failed: {str(e)}")
        
        # Tech stack analysis (if we have domain)
        if domain:
            try:
                tech_stack = await self._analyze_tech_stack(domain)
                profile_data["tech_stack"] = tech_stack
                logger.info(f"   ✅ Identified {len(tech_stack)} technologies")
            except Exception as e:
                logger.warning(f"   ⚠️ Tech stack analysis failed: {str(e)}")
        
        return CompanyProfile(**profile_data)
    
    async def find_additional_contacts(
        self,
        company_name: str,
        titles: Optional[List[str]] = None
    ) -> List[Contact]:
        """Find additional contacts at a company.
        
        Args:
            company_name: Company to search
            titles: Target titles (e.g., ["CEO", "Director", "Manager"])
        
        Returns:
            List of contacts
        """
        logger.info(f"🔍 Finding contacts at: {company_name}")
        
        contacts = []
        
        # Try Apollo.io if configured
        if self.apollo_api_key:
            try:
                apollo_contacts = await self._apollo_find_contacts(company_name, titles)
                contacts.extend(apollo_contacts)
                logger.info(f"   ✅ Found {len(apollo_contacts)} contacts via Apollo")
            except Exception as e:
                logger.warning(f"   ⚠️ Apollo search failed: {str(e)}")
        
        # Try LinkedIn company page scraping (if no Apollo)
        if not contacts:
            logger.info("   ⚠️ No API contacts found, would need LinkedIn scraping")
        
        return contacts
    
    # ===== Internal Methods =====
    
    async def _clearbit_person_lookup(self, email: str) -> Optional[Dict[str, Any]]:
        """Look up person via Clearbit Enrichment API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://person.clearbit.com/v2/combined/find?email={email}",
                auth=(self.clearbit_api_key, ""),
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                person = data.get("person", {})
                
                return {
                    "name": person.get("name", {}).get("fullName"),
                    "title": person.get("employment", {}).get("title"),
                    "company": person.get("employment", {}).get("name"),
                    "location": person.get("location"),
                    "bio": person.get("bio"),
                    "linkedin_url": person.get("linkedin", {}).get("handle"),
                    "social_presence": {
                        "twitter": person.get("twitter", {}).get("handle"),
                        "facebook": person.get("facebook", {}).get("handle")
                    }
                }
            
            return None
    
    async def _clearbit_company_lookup(
        self,
        company_name: str,
        domain: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Look up company via Clearbit Company API."""
        if not domain:
            # Try to find domain first
            domain = await self._find_company_domain(company_name)
        
        if not domain:
            return None
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://company.clearbit.com/v2/companies/find?domain={domain}",
                auth=(self.clearbit_api_key, ""),
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "domain": data.get("domain"),
                    "industry": data.get("category", {}).get("industry"),
                    "employee_count": data.get("metrics", {}).get("employees"),
                    "founded_year": data.get("foundedYear"),
                    "headquarters": data.get("location"),
                    "description": data.get("description"),
                    "tech_stack": data.get("tech", []),
                    "social_links": {
                        "linkedin": data.get("linkedin", {}).get("handle"),
                        "twitter": data.get("twitter", {}).get("handle"),
                        "facebook": data.get("facebook", {}).get("handle")
                    }
                }
            
            return None
    
    async def _find_linkedin_profile(
        self,
        name: str,
        company: str
    ) -> Optional[str]:
        """Find LinkedIn profile URL via search.
        
        TODO: Implement using Perplexity or Google Search MCP
        """
        # Placeholder - would use MCP tool or Perplexity API
        logger.debug(f"LinkedIn search: {name} at {company}")
        return None
    
    async def _find_recent_activity(
        self,
        name: str,
        company: str
    ) -> List[str]:
        """Find recent professional activity.
        
        TODO: Implement using news search and social media APIs
        """
        return []
    
    async def _find_company_news(self, company_name: str) -> List[Dict[str, str]]:
        """Find recent company news.
        
        TODO: Implement using Perplexity or news APIs
        """
        return []
    
    async def _analyze_tech_stack(self, domain: str) -> List[str]:
        """Analyze company's tech stack.
        
        TODO: Implement using BuiltWith API or similar
        """
        return []
    
    async def _find_company_domain(self, company_name: str) -> Optional[str]:
        """Find company domain from name.
        
        TODO: Implement domain lookup
        """
        # Simple heuristic for now
        clean_name = company_name.lower().replace(" ", "").replace(",", "")
        return f"{clean_name}.com"
    
    async def _apollo_find_contacts(
        self,
        company_name: str,
        titles: Optional[List[str]]
    ) -> List[Contact]:
        """Find contacts using Apollo.io API.
        
        TODO: Implement Apollo.io people search
        """
        return []
    
    def _calculate_research_score(
        self,
        person: Optional[PersonProfile],
        company: Optional[CompanyProfile],
        contacts: List[Contact]
    ) -> int:
        """Calculate research quality score 0-100."""
        score = 0
        
        if person:
            if person.linkedin_url:
                score += 20
            if person.title:
                score += 15
            if person.bio:
                score += 10
            if person.recent_activity:
                score += 10
        
        if company:
            if company.employee_count:
                score += 15
            if company.tech_stack:
                score += 10
            if company.recent_news:
                score += 10
            if company.funding_stage:
                score += 5
        
        if contacts:
            score += min(len(contacts) * 2, 15)
        
        return min(score, 100)
    
    def _generate_insights(
        self,
        person: Optional[PersonProfile],
        company: Optional[CompanyProfile],
        contacts: List[Contact]
    ) -> List[str]:
        """Generate actionable insights from research."""
        insights = []
        
        if person and person.linkedin_url:
            insights.append(f"Connect with {person.name} on LinkedIn: {person.linkedin_url}")
        
        if company and company.employee_count:
            if company.employee_count > 100:
                insights.append(f"Enterprise-scale company with {company.employee_count}+ employees")
            elif company.employee_count > 50:
                insights.append(f"Mid-market company with {company.employee_count} employees")
        
        if company and company.recent_news:
            insights.append(f"Recent company activity: {len(company.recent_news)} news items")
        
        if contacts:
            insights.append(f"Found {len(contacts)} additional contacts for multi-touch outreach")
        
        if not insights:
            insights.append("Limited public information available - manual research recommended")
        
        return insights
    
    def _create_summary(
        self,
        person: Optional[PersonProfile],
        company: Optional[CompanyProfile]
    ) -> str:
        """Create human-readable research summary."""
        parts = []
        
        if person:
            parts.append(f"{person.name} ({person.title or 'Unknown title'})")
            if person.company:
                parts.append(f"at {person.company}")
        
        if company:
            parts.append(f"Company: {company.name}")
            if company.employee_count:
                parts.append(f"({company.employee_count} employees)")
            if company.industry:
                parts.append(f"Industry: {company.industry}")
        
        return " | ".join(parts) if parts else "Limited research data available"


    async def respond(self, message: str) -> str:
        """A2A endpoint - respond to inter-agent messages about lead research.
        
        Args:
            message: JSON string with lead info or natural language query
            
        Returns:
            String response with research results
        """
        import json
        import asyncio
        
        try:
            # Parse JSON request
            try:
                data = json.loads(message)
                lead_id = data.get('lead_id')
                name = data.get('name')
                email = data.get('email')
                company = data.get('company')
                
                if not lead_id:
                    return "❌ Error: No lead_id provided in request"
                    
            except json.JSONDecodeError:
                return "❌ Error: Please provide lead info in JSON format: {\"lead_id\": \"...\", \"name\": \"...\", \"email\": \"...\", \"company\": \"...\"}"
                
            # Conduct research
            results = self.forward(
                lead_id=lead_id,
                name=name,
                email=email,
                company=company
            )
            
            # Handle async result if needed
            if asyncio.iscoroutine(results):
                results = await results
                
            # Format response
            response_parts = [
                f"🔍 **Research Results: {name or 'Lead'}**",
                f"",
                f"**Lead ID:** {lead_id}",
                f""
            ]
            
            # Add key insights
            if 'key_insights' in results:
                response_parts.extend([
                    f"**Key Insights:**",
                    results['key_insights'],
                    f""
                ])
                
            # Add engagement strategy
            if 'engagement_strategy' in results:
                response_parts.extend([
                    f"**Engagement Strategy:**",
                    results['engagement_strategy'],
                    f""
                ])
                
            # Add talking points
            if 'talking_points' in results:
                response_parts.extend([
                    f"**Talking Points:**",
                    results['talking_points']
                ])
                
            return "\n".join(response_parts)
            
        except Exception as e:
            import traceback
            return f"❌ Error conducting research: {str(e)}\n\n{traceback.format_exc()}"

# ===== Export =====
__all__ = ['ResearchAgent', 'PersonProfile', 'CompanyProfile', 'Contact', 'ResearchResult']
