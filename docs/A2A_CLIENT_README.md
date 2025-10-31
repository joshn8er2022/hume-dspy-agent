
# Agent Zero A2A Client

## Overview

The Agent Zero A2A (Agent-to-Agent) Client enables the Hume DSPy agent to communicate with Agent Zero for advanced research and enrichment tasks. This implementation follows the FastA2A v0.2+ protocol for seamless agent-to-agent communication.

## Architecture

```
┌─────────────────────┐         FastA2A Protocol        ┌─────────────────────┐
│                     │◄──────────────────────────────►│                     │
│  Hume DSPy Agent    │    HTTP/JSON over Railway      │   Agent Zero        │
│  (InboundAgent)     │    Internal Network            │   (Research Agent)  │
│                     │                                 │                     │
└─────────────────────┘                                 └─────────────────────┘
        │                                                         │
        │ 1. Company Research                                     │
        │ 2. Contact Discovery                                    │
        │ 3. Contact Enrichment                                   │
        │ 4. General Research                                     │
        └─────────────────────────────────────────────────────────┘
```

## Features

✅ **FastA2A Protocol v0.2+** - Full protocol compliance with context preservation  
✅ **Company Research** - Comprehensive company data gathering and enrichment  
✅ **Contact Discovery** - Find contacts at companies with specific roles  
✅ **Contact Enrichment** - Enrich partial contact data with LinkedIn, interests, etc.  
✅ **Error Handling** - Automatic retry with exponential backoff  
✅ **Timeout Management** - Configurable timeouts (default: 5 minutes)  
✅ **Context Preservation** - Maintains conversation context across messages  
✅ **Async/Await** - Full async support for concurrent operations  
✅ **Type Safety** - Pydantic models for all data structures  
✅ **Comprehensive Logging** - Detailed logging for debugging and monitoring  

## Installation

### 1. Install Dependencies

```bash
pip install httpx>=0.27.0
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Agent Zero A2A Configuration
AGENT_ZERO_URL=http://agent-zero.railway.internal:80
AGENT_ZERO_TOKEN=your-api-token-here
```

### 3. Verify Installation

```python
from core.a2a_client import AgentZeroClient

# Test client initialization
client = AgentZeroClient()
print(f"A2A Endpoint: {client.a2a_endpoint}")
```

## Quick Start

### Basic Company Research

```python
import asyncio
from core.a2a_client import AgentZeroClient

async def research_company():
    async with AgentZeroClient() as client:
        company = await client.research_company(
            company_name="Acme Medical Solutions",
            domain="acmemedical.com",
            deep_research=True
        )

        print(f"Company: {company.name}")
        print(f"Industry: {company.industry}")
        print(f"Size: {company.size}")
        print(f"Technologies: {company.technologies}")

asyncio.run(research_company())
```

### Contact Discovery

```python
async def find_contacts():
    async with AgentZeroClient() as client:
        contacts = await client.find_contacts(
            company_name="Acme Medical Solutions",
            roles=["doctor", "physician", "admin"],
            max_contacts=10
        )

        for contact in contacts:
            print(f"{contact.name} - {contact.role}")
            print(f"  Email: {contact.email}")
            print(f"  LinkedIn: {contact.linkedin_url}")

asyncio.run(find_contacts())
```

### Contact Enrichment

```python
async def enrich_contact():
    async with AgentZeroClient() as client:
        contact = await client.enrich_contact(
            email="john@acmemedical.com",
            name="John Doe"
        )

        print(f"Name: {contact.name}")
        print(f"Role: {contact.role}")
        print(f"Company: {contact.company}")
        print(f"Interests: {contact.interests}")

asyncio.run(enrich_contact())
```

## API Reference

### AgentZeroClient

Main client class for A2A communication.

#### Constructor

```python
AgentZeroClient(
    base_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = 300,
    max_retries: int = 3,
    retry_delay: float = 1.0,
)
```

**Parameters:**
- `base_url`: Agent Zero base URL (default: from `AGENT_ZERO_URL` env)
- `token`: API token (default: from `AGENT_ZERO_TOKEN` env)
- `timeout`: Request timeout in seconds (default: 300)
- `max_retries`: Maximum retry attempts (default: 3)
- `retry_delay`: Initial retry delay in seconds (default: 1.0)

#### Methods

##### `research_company()`

Research a company and return structured data.

```python
await client.research_company(
    company_name: str,
    domain: Optional[str] = None,
    deep_research: bool = True,
) -> CompanyData
```

**Returns:** `CompanyData` with fields:
- `name`: Company name
- `domain`: Company domain
- `industry`: Industry classification
- `size`: Company size (e.g., "100-500 employees")
- `location`: Headquarters location
- `description`: Company description
- `technologies`: List of technologies used
- `social_media`: Social media profiles (dict)
- `key_people`: List of key people (list of dicts)
- `recent_news`: Recent news items (list)
- `metadata`: Additional metadata (dict)

##### `find_contacts()`

Find contacts at a company with specific roles.

```python
await client.find_contacts(
    company_name: str,
    roles: Optional[List[str]] = None,
    max_contacts: int = 10,
) -> List[ContactData]
```

**Returns:** List of `ContactData` with fields:
- `name`: Contact name
- `email`: Email address
- `role`: Job title/role
- `company`: Company name
- `linkedin_url`: LinkedIn profile URL
- `phone`: Phone number
- `location`: Location
- `interests`: Professional interests (list)
- `metadata`: Additional metadata (dict)

##### `enrich_contact()`

Enrich contact information.

```python
await client.enrich_contact(
    email: Optional[str] = None,
    name: Optional[str] = None,
    company: Optional[str] = None,
) -> ContactData
```

**Note:** At least one of `email`, `name`, or `company` must be provided.

**Returns:** `ContactData` with enriched information.

##### `general_research()`

Perform general research query.

```python
await client.general_research(
    query: str,
    context_key: Optional[str] = None,
    structured_output: bool = False,
) -> str | dict
```

**Returns:** Research results as string or dict (if `structured_output=True`).

##### `reset_context()`

Reset conversation context.

```python
await client.reset_context(context_key: str = "default")
```

## Integration with InboundAgent

### Example: Enrich Inbound Lead

```python
from core.a2a_client import AgentZeroClient

class InboundAgent:
    def __init__(self):
        self.a2a_client = AgentZeroClient()

    async def process_inbound_lead(self, lead_data: dict):
        """Process and enrich inbound lead."""

        # Step 1: Research company
        company = await self.a2a_client.research_company(
            company_name=lead_data["company_name"],
            domain=lead_data["domain"],
            deep_research=False  # Quick research for inbound
        )

        # Step 2: Enrich contact
        contact = await self.a2a_client.enrich_contact(
            email=lead_data["email"],
            company=lead_data["company_name"]
        )

        # Step 3: Build enriched profile
        enriched_lead = {
            "company": {
                "name": company.name,
                "industry": company.industry,
                "size": company.size,
                "technologies": company.technologies,
            },
            "contact": {
                "name": contact.name,
                "role": contact.role,
                "linkedin_url": contact.linkedin_url,
                "interests": contact.interests,
            },
        }

        return enriched_lead
```

## Error Handling

The client implements comprehensive error handling:

### Automatic Retry

```python
# Automatically retries on HTTP errors with exponential backoff
client = AgentZeroClient(max_retries=3, retry_delay=1.0)

# First attempt fails -> retry after 1s
# Second attempt fails -> retry after 2s
# Third attempt fails -> raise exception
```

### Graceful Degradation

```python
try:
    company = await client.research_company("Acme Corp")

    if "error" in company.metadata:
        # Research failed, use fallback
        print("Using fallback data")
except Exception as e:
    # Agent Zero unavailable
    print(f"A2A unavailable: {e}")
    # Use cached data or manual input
```

### Timeout Handling

```python
# Configure timeout for long-running research
client = AgentZeroClient(timeout=600)  # 10 minutes

try:
    result = await client.research_company("Complex Corp")
except asyncio.TimeoutError:
    print("Research timed out")
```

## Testing

### Run Unit Tests

```bash
pytest tests/test_a2a_client.py -v
```

### Run Specific Test

```bash
pytest tests/test_a2a_client.py::TestAgentZeroClient::test_research_company_success -v
```

### Run with Coverage

```bash
pytest tests/test_a2a_client.py --cov=core.a2a_client --cov-report=html
```

## Examples

See `examples/a2a_usage.py` for comprehensive examples:

1. **Basic Company Research** - Simple company lookup
2. **Contact Discovery** - Find contacts with specific roles
3. **Multi-Step Workflow** - Complete research pipeline
4. **InboundAgent Integration** - Integration with Hume agent
5. **Batch Processing** - Process multiple companies concurrently

Run examples:

```bash
python examples/a2a_usage.py
```

## Performance Considerations

### Concurrent Requests

```python
# Process multiple companies concurrently
async with AgentZeroClient() as client:
    tasks = [
        client.research_company(name, domain)
        for name, domain in companies
    ]
    results = await asyncio.gather(*tasks)
```

### Context Reuse

```python
# Reuse context for follow-up questions
async with AgentZeroClient() as client:
    # First message
    await client.general_research(
        "Tell me about Acme Corp",
        context_key="acme_research"
    )

    # Follow-up (uses same context)
    await client.general_research(
        "What are their main products?",
        context_key="acme_research"
    )
```

## Troubleshooting

### Issue: "AGENT_ZERO_TOKEN not configured"

**Solution:** Set the environment variable:

```bash
export AGENT_ZERO_TOKEN=your-token-here
```

### Issue: Connection timeout

**Solution:** Increase timeout or check Agent Zero availability:

```python
client = AgentZeroClient(timeout=600)  # 10 minutes
```

### Issue: "No valid JSON found in response"

**Solution:** Agent Zero returned non-JSON response. Check logs or use `general_research()` without `structured_output=True`.

### Issue: Retry exhausted

**Solution:** Agent Zero is unavailable. Implement fallback:

```python
try:
    result = await client.research_company("Acme")
except Exception:
    # Use fallback data source
    result = get_cached_data("Acme")
```

## Logging

The client uses Python's standard logging module:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger("core.a2a_client")
logger.setLevel(logging.DEBUG)
```

## Contributing

When adding new features:

1. Add method to `AgentZeroClient` class
2. Add corresponding Pydantic model if needed
3. Add unit tests in `tests/test_a2a_client.py`
4. Add usage example in `examples/a2a_usage.py`
5. Update this README

## License

Part of the Hume DSPy Agent project.

## Support

For issues or questions:
- Check the examples in `examples/a2a_usage.py`
- Review test cases in `tests/test_a2a_client.py`
- Check Agent Zero logs for debugging
