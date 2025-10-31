
# A2A Client Integration Guide for InboundAgent

## Quick Integration Steps

### Step 1: Import the Client

Add to your InboundAgent file:

```python
from core.a2a_client import AgentZeroClient, CompanyData, ContactData
```

### Step 2: Initialize in InboundAgent

```python
class InboundAgent:
    def __init__(self):
        # ... existing initialization ...
        self.a2a_client = AgentZeroClient()

    async def cleanup(self):
        """Cleanup resources."""
        await self.a2a_client.close()
```

### Step 3: Add Research to Lead Processing

```python
async def process_inbound_lead(self, lead_data: dict) -> dict:
    """Process inbound lead with A2A enrichment."""

    # Extract lead info
    company_name = lead_data.get("company_name")
    domain = lead_data.get("domain")
    email = lead_data.get("email")

    # Research company (if available)
    company_data = None
    if company_name:
        try:
            company_data = await self.a2a_client.research_company(
                company_name=company_name,
                domain=domain,
                deep_research=False  # Quick research for inbound
            )
            logger.info(f"✅ Company research: {company_data.industry}")
        except Exception as e:
            logger.warning(f"⚠️ Company research failed: {e}")

    # Enrich contact (if available)
    contact_data = None
    if email:
        try:
            contact_data = await self.a2a_client.enrich_contact(
                email=email,
                name=lead_data.get("name"),
                company=company_name
            )
            logger.info(f"✅ Contact enriched: {contact_data.role}")
        except Exception as e:
            logger.warning(f"⚠️ Contact enrichment failed: {e}")

    # Build enriched lead profile
    enriched_lead = {
        "original": lead_data,
        "company": {
            "name": company_data.name if company_data else company_name,
            "industry": company_data.industry if company_data else None,
            "size": company_data.size if company_data else None,
            "technologies": company_data.technologies if company_data else [],
        } if company_data else None,
        "contact": {
            "name": contact_data.name if contact_data else lead_data.get("name"),
            "role": contact_data.role if contact_data else None,
            "linkedin_url": contact_data.linkedin_url if contact_data else None,
            "interests": contact_data.interests if contact_data else [],
        } if contact_data else None,
    }

    return enriched_lead
```

### Step 4: Use Enriched Data for Personalization

```python
async def generate_response(self, enriched_lead: dict) -> str:
    """Generate personalized response using enriched data."""

    # Extract enriched data
    company = enriched_lead.get("company", {})
    contact = enriched_lead.get("contact", {})

    # Build context for response generation
    context = f"""
Company: {company.get('name')}
Industry: {company.get('industry')}
Size: {company.get('size')}
Technologies: {', '.join(company.get('technologies', []))}

Contact: {contact.get('name')}
Role: {contact.get('role')}
Interests: {', '.join(contact.get('interests', []))}
"""

    # Use DSPy module with enriched context
    response = await self.response_generator(
        message=enriched_lead["original"]["message"],
        context=context
    )

    return response
```

### Step 5: Environment Configuration

Add to `.env`:

```bash
# Agent Zero A2A Configuration
AGENT_ZERO_URL=http://agent-zero.railway.internal:80
AGENT_ZERO_TOKEN=your-secure-token-here
```

## Complete Example

```python
from core.a2a_client import AgentZeroClient
import logging

logger = logging.getLogger(__name__)

class InboundAgent:
    def __init__(self):
        self.a2a_client = AgentZeroClient(
            timeout=300,  # 5 minutes
            max_retries=3
        )

    async def handle_inbound_email(self, email_data: dict):
        """Complete inbound email handling with A2A enrichment."""

        # Step 1: Extract lead data
        lead_data = {
            "email": email_data["from"],
            "company_name": email_data.get("company"),
            "domain": email_data.get("domain"),
            "message": email_data["body"],
        }

        # Step 2: Enrich with A2A
        enriched = await self.process_inbound_lead(lead_data)

        # Step 3: Generate personalized response
        response = await self.generate_response(enriched)

        # Step 4: Send response
        await self.send_email(email_data["from"], response)

        return enriched

    async def cleanup(self):
        await self.a2a_client.close()
```

## Testing Integration

```python
import pytest

@pytest.mark.asyncio
async def test_inbound_agent_with_a2a():
    """Test InboundAgent with A2A client."""
    agent = InboundAgent()

    lead_data = {
        "email": "test@acme.com",
        "company_name": "Acme Corp",
        "domain": "acme.com",
        "message": "Interested in your product"
    }

    enriched = await agent.process_inbound_lead(lead_data)

    assert enriched["company"] is not None
    assert enriched["contact"] is not None

    await agent.cleanup()
```

## Performance Tips

1. **Use Quick Research for Inbound Leads**
   ```python
   # Fast research (30-60 seconds)
   company = await client.research_company(name, domain, deep_research=False)
   ```

2. **Batch Process Multiple Leads**
   ```python
   tasks = [client.research_company(name, domain) for name, domain in leads]
   results = await asyncio.gather(*tasks)
   ```

3. **Cache Results**
   ```python
   # Cache company research for 24 hours
   if cached := get_cached_company(domain):
       return cached
   company = await client.research_company(name, domain)
   cache_company(domain, company, ttl=86400)
   ```

## Monitoring

Add Phoenix tracing:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_inbound_lead(self, lead_data):
    with tracer.start_as_current_span("a2a_research") as span:
        span.set_attribute("company", lead_data["company_name"])

        company = await self.a2a_client.research_company(
            company_name=lead_data["company_name"],
            domain=lead_data["domain"]
        )

        span.set_attribute("industry", company.industry)
        return company
```
