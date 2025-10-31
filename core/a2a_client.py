
"""
Agent Zero A2A Client for Research Tasks

This module provides a FastA2A protocol client to communicate with Agent Zero
for advanced research tasks including:
- Company research and enrichment
- Contact discovery and enrichment
- Web scraping and data extraction
- General research queries

FastA2A Protocol v0.2+ Implementation
"""
import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for A2A client. Install with: pip install httpx"
    )

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class A2AMessageRole(str, Enum):
    """Message roles in A2A protocol."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class A2AMessage(BaseModel):
    """A2A protocol message format."""
    role: A2AMessageRole
    content: str
    attachments: Optional[List[str]] = Field(default_factory=list)


class A2ARequest(BaseModel):
    """A2A protocol request format."""
    message: str
    context_id: Optional[str] = None
    attachments: Optional[List[str]] = Field(default_factory=list)


class A2AResponse(BaseModel):
    """A2A protocol response format."""
    response: str
    context_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CompanyData(BaseModel):
    """Structured company research data."""
    name: str
    domain: str
    industry: Optional[str] = None
    size: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = Field(default_factory=list)
    social_media: Optional[Dict[str, str]] = Field(default_factory=dict)
    key_people: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    recent_news: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ContactData(BaseModel):
    """Structured contact data."""
    name: str
    email: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    interests: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AgentZeroClient:
    """Client for communicating with Agent Zero via FastA2A protocol.

    This client implements the FastA2A v0.2+ protocol for agent-to-agent
    communication with Agent Zero. It provides high-level methods for:
    - Company research and enrichment
    - Contact discovery and enrichment
    - General research queries

    Features:
    - Automatic retry with exponential backoff
    - Context preservation across messages
    - Comprehensive error handling
    - Timeout management (5 minutes default)
    - Structured response parsing

    Example:
        >>> client = AgentZeroClient()
        >>> company_data = await client.research_company("Acme Corp", "acme.com")
        >>> contacts = await client.find_contacts("Acme Corp", ["doctor", "admin"])
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize Agent Zero A2A client.

        Args:
            base_url: Agent Zero base URL (default: from AGENT_ZERO_URL env)
            token: API token (default: from AGENT_ZERO_TOKEN env)
            timeout: Request timeout in seconds (default: 300 = 5 minutes)
            max_retries: Maximum retry attempts (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
        """
        self.base_url = base_url or os.getenv(
            "AGENT_ZERO_URL",
            "http://agent-zero.railway.internal:80"
        )
        self.token = token or os.getenv("AGENT_ZERO_TOKEN")

        if not self.token:
            logger.warning(
                "⚠️ AGENT_ZERO_TOKEN not set - A2A client will be unavailable"
            )

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Context management - stores context_id per conversation
        self._contexts: Dict[str, str] = {}

        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

        logger.info("✅ Agent Zero A2A Client initialized")
        logger.info(f"   Base URL: {self.base_url}")
        logger.info(f"   Timeout: {timeout}s")
        logger.info(f"   Max Retries: {max_retries}")

    @property
    def a2a_endpoint(self) -> str:
        """Get the A2A endpoint URL with token."""
        if not self.token:
            raise ValueError("AGENT_ZERO_TOKEN not configured")
        return f"{self.base_url}/a2a/t-{self.token}"

    async def _send_message(
        self,
        message: str,
        context_key: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        reset_context: bool = False,
    ) -> A2AResponse:
        """Send a message to Agent Zero via A2A protocol.

        Args:
            message: Message content to send
            context_key: Key for context preservation (default: "default")
            attachments: Optional file attachments (URLs or paths)
            reset_context: If True, start a new conversation context

        Returns:
            A2AResponse with agent's response and context_id

        Raises:
            httpx.HTTPError: On HTTP errors
            ValueError: On invalid responses
        """
        context_key = context_key or "default"

        # Get existing context_id unless resetting
        context_id = None if reset_context else self._contexts.get(context_key)

        # Build request payload
        payload = {
            "message": message,
        }

        if context_id:
            payload["context_id"] = context_id

        if attachments:
            payload["attachments"] = attachments

        logger.info(f"📤 Sending A2A message (context: {context_key})")
        logger.debug(f"   Message: {message[:100]}...")
        logger.debug(f"   Context ID: {context_id}")

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    self.a2a_endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()

                # Parse response
                data = response.json()

                # Extract response and context_id
                response_text = data.get("response", "")
                new_context_id = data.get("context_id")
                metadata = data.get("metadata", {})

                # Store context_id for future messages
                if new_context_id:
                    self._contexts[context_key] = new_context_id
                    logger.debug(f"   Updated context ID: {new_context_id}")

                logger.info(f"📥 Received A2A response ({len(response_text)} chars)")

                return A2AResponse(
                    response=response_text,
                    context_id=new_context_id,
                    metadata=metadata,
                )

            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    f"⚠️ A2A request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"   Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ A2A request failed after {self.max_retries} attempts")
                    raise

            except Exception as e:
                logger.error(f"❌ Unexpected error in A2A request: {e}")
                raise

        # Should not reach here, but just in case
        raise last_error or Exception("A2A request failed")

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from Agent Zero response.

        Agent Zero may return responses in various formats. This method
        attempts to extract JSON data from the response.

        Args:
            response_text: Raw response text from Agent Zero

        Returns:
            Parsed JSON data as dictionary

        Raises:
            ValueError: If no valid JSON found in response
        """
        # Try to parse entire response as JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code blocks
        import re
        json_pattern = r'```(?:json)?\s*({[^`]+})\s*```'
        matches = re.findall(json_pattern, response_text, re.DOTALL)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Try to find raw JSON objects
        json_pattern = r'{[^{}]*(?:{[^{}]*}[^{}]*)*}'
        matches = re.findall(json_pattern, response_text, re.DOTALL)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        raise ValueError("No valid JSON found in response")

    async def research_company(
        self,
        company_name: str,
        domain: Optional[str] = None,
        deep_research: bool = True,
    ) -> CompanyData:
        """Research a company and return structured data.

        This method delegates to Agent Zero to perform comprehensive company
        research including:
        - Company overview and description
        - Industry and size information
        - Key technologies used
        - Social media presence
        - Key people and leadership
        - Recent news and developments

        Args:
            company_name: Name of the company to research
            domain: Company domain (e.g., "acme.com") - helps with accuracy
            deep_research: If True, perform deep research (slower but more thorough)

        Returns:
            CompanyData with structured research results

        Example:
            >>> client = AgentZeroClient()
            >>> data = await client.research_company("Acme Corp", "acme.com")
            >>> print(data.industry, data.size, data.technologies)
        """
        logger.info(f"🔍 Researching company: {company_name}")

        # Build research prompt
        prompt = f"""
Research the company "{company_name}"{f' (domain: {domain})' if domain else ''} and provide comprehensive information.

Please gather the following information:
1. Company overview and description
2. Industry and company size
3. Location and headquarters
4. Key technologies and tech stack
5. Social media profiles (LinkedIn, Twitter, etc.)
6. Key people and leadership team
7. Recent news and developments

{'Perform deep research using multiple sources.' if deep_research else 'Provide a quick overview.'}

Return the results in JSON format with the following structure:
{{
    "name": "Company Name",
    "domain": "company.com",
    "industry": "Industry",
    "size": "Company size (e.g., 50-200 employees)",
    "location": "City, Country",
    "description": "Brief description",
    "technologies": ["tech1", "tech2"],
    "social_media": {{
        "linkedin": "url",
        "twitter": "url"
    }},
    "key_people": [
        {{"name": "Person Name", "role": "CEO"}}
    ],
    "recent_news": ["news item 1", "news item 2"]
}}
"""

        try:
            # Send research request
            response = await self._send_message(
                message=prompt,
                context_key=f"company_research_{company_name}",
                reset_context=True,  # Fresh context for each research
            )

            # Parse JSON response
            data = self._parse_json_response(response.response)

            # Create CompanyData object
            company_data = CompanyData(
                name=data.get("name", company_name),
                domain=data.get("domain", domain or ""),
                industry=data.get("industry"),
                size=data.get("size"),
                location=data.get("location"),
                description=data.get("description"),
                technologies=data.get("technologies", []),
                social_media=data.get("social_media", {}),
                key_people=data.get("key_people", []),
                recent_news=data.get("recent_news", []),
                metadata={
                    "researched_at": datetime.utcnow().isoformat(),
                    "context_id": response.context_id,
                },
            )

            logger.info(f"✅ Company research complete: {company_name}")
            return company_data

        except Exception as e:
            logger.error(f"❌ Company research failed: {e}")
            # Return minimal data on failure
            return CompanyData(
                name=company_name,
                domain=domain or "",
                metadata={"error": str(e)},
            )

    async def find_contacts(
        self,
        company_name: str,
        roles: Optional[List[str]] = None,
        max_contacts: int = 10,
    ) -> List[ContactData]:
        """Find contacts at a company with specific roles.

        This method delegates to Agent Zero to discover contacts at a company,
        optionally filtering by role (e.g., "doctor", "admin", "CEO").

        Args:
            company_name: Name of the company
            roles: List of roles to search for (e.g., ["doctor", "admin"])
            max_contacts: Maximum number of contacts to return

        Returns:
            List of ContactData objects

        Example:
            >>> client = AgentZeroClient()
            >>> contacts = await client.find_contacts(
            ...     "Acme Medical",
            ...     roles=["doctor", "physician", "admin"]
            ... )
            >>> for contact in contacts:
            ...     print(contact.name, contact.role, contact.email)
        """
        logger.info(f"👥 Finding contacts at: {company_name}")

        # Build search prompt
        roles_str = ", ".join(roles) if roles else "any role"
        prompt = f"""
Find contacts at "{company_name}" with the following roles: {roles_str}

Please search for up to {max_contacts} contacts and gather:
1. Full name
2. Email address (if available)
3. Job title/role
4. LinkedIn profile URL
5. Phone number (if available)
6. Location

Return the results in JSON format as an array:
[
    {{
        "name": "Contact Name",
        "email": "email@company.com",
        "role": "Job Title",
        "company": "{company_name}",
        "linkedin_url": "https://linkedin.com/in/...",
        "phone": "+1234567890",
        "location": "City, Country"
    }}
]
"""

        try:
            # Send contact search request
            response = await self._send_message(
                message=prompt,
                context_key=f"contact_search_{company_name}",
                reset_context=True,
            )

            # Parse JSON response
            data = self._parse_json_response(response.response)

            # Handle both array and object responses
            if isinstance(data, dict) and "contacts" in data:
                contacts_list = data["contacts"]
            elif isinstance(data, list):
                contacts_list = data
            else:
                contacts_list = [data]

            # Create ContactData objects
            contacts = []
            for contact_data in contacts_list[:max_contacts]:
                contact = ContactData(
                    name=contact_data.get("name", ""),
                    email=contact_data.get("email"),
                    role=contact_data.get("role"),
                    company=contact_data.get("company", company_name),
                    linkedin_url=contact_data.get("linkedin_url"),
                    phone=contact_data.get("phone"),
                    location=contact_data.get("location"),
                    metadata={
                        "found_at": datetime.utcnow().isoformat(),
                        "context_id": response.context_id,
                    },
                )
                contacts.append(contact)

            logger.info(f"✅ Found {len(contacts)} contacts at {company_name}")
            return contacts

        except Exception as e:
            logger.error(f"❌ Contact search failed: {e}")
            return []

    async def enrich_contact(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None,
    ) -> ContactData:
        """Enrich contact information (LinkedIn, role, interests).

        This method delegates to Agent Zero to enrich contact data by finding:
        - LinkedIn profile
        - Current role and company
        - Professional interests
        - Additional contact information

        Args:
            email: Contact email address
            name: Contact full name
            company: Contact company name

        Returns:
            ContactData with enriched information

        Note:
            At least one of email, name, or company must be provided.

        Example:
            >>> client = AgentZeroClient()
            >>> contact = await client.enrich_contact(
            ...     email="john@acme.com",
            ...     name="John Doe"
            ... )
            >>> print(contact.linkedin_url, contact.role, contact.interests)
        """
        if not any([email, name, company]):
            raise ValueError("At least one of email, name, or company must be provided")

        logger.info(f"🔍 Enriching contact: {name or email}")

        # Build enrichment prompt
        identifiers = []
        if email:
            identifiers.append(f"Email: {email}")
        if name:
            identifiers.append(f"Name: {name}")
        if company:
            identifiers.append(f"Company: {company}")

        prompt = f"""
Enrich the following contact information:
{chr(10).join(identifiers)}

Please find and provide:
1. Full name
2. Current job title and company
3. LinkedIn profile URL
4. Email address (if not provided)
5. Phone number (if available)
6. Location
7. Professional interests and expertise areas

Return the results in JSON format:
{{
    "name": "Full Name",
    "email": "email@company.com",
    "role": "Job Title",
    "company": "Company Name",
    "linkedin_url": "https://linkedin.com/in/...",
    "phone": "+1234567890",
    "location": "City, Country",
    "interests": ["interest1", "interest2"]
}}
"""

        try:
            # Send enrichment request
            response = await self._send_message(
                message=prompt,
                context_key=f"contact_enrich_{email or name}",
                reset_context=True,
            )

            # Parse JSON response
            data = self._parse_json_response(response.response)

            # Create ContactData object
            contact = ContactData(
                name=data.get("name", name or ""),
                email=data.get("email", email),
                role=data.get("role"),
                company=data.get("company", company),
                linkedin_url=data.get("linkedin_url"),
                phone=data.get("phone"),
                location=data.get("location"),
                interests=data.get("interests", []),
                metadata={
                    "enriched_at": datetime.utcnow().isoformat(),
                    "context_id": response.context_id,
                },
            )

            logger.info(f"✅ Contact enrichment complete: {contact.name}")
            return contact

        except Exception as e:
            logger.error(f"❌ Contact enrichment failed: {e}")
            # Return minimal data on failure
            return ContactData(
                name=name or "",
                email=email,
                company=company,
                metadata={"error": str(e)},
            )

    async def general_research(
        self,
        query: str,
        context_key: Optional[str] = None,
        structured_output: bool = False,
    ) -> str:
        """Perform general research query.

        This is a flexible method for any research task that doesn't fit
        the specific company/contact methods.

        Args:
            query: Research query or task description
            context_key: Optional context key for conversation continuity
            structured_output: If True, attempt to parse JSON response

        Returns:
            Research results as string (or JSON if structured_output=True)

        Example:
            >>> client = AgentZeroClient()
            >>> result = await client.general_research(
            ...     "Find the top 5 medical device companies in California"
            ... )
            >>> print(result)
        """
        logger.info(f"🔍 General research: {query[:100]}...")

        try:
            response = await self._send_message(
                message=query,
                context_key=context_key or "general_research",
            )

            if structured_output:
                try:
                    return self._parse_json_response(response.response)
                except ValueError:
                    logger.warning("Could not parse structured output, returning raw text")

            return response.response

        except Exception as e:
            logger.error(f"❌ General research failed: {e}")
            return f"Research failed: {str(e)}"

    async def reset_context(self, context_key: str = "default"):
        """Reset conversation context for a specific key.

        Args:
            context_key: Context key to reset
        """
        if context_key in self._contexts:
            del self._contexts[context_key]
            logger.info(f"🔄 Reset context: {context_key}")

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        await self.client.aclose()
        logger.info("👋 Agent Zero A2A Client closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
