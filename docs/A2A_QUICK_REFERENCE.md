
# A2A Client Quick Reference Card

## 🚀 Quick Start (30 seconds)

```python
from core.a2a_client import AgentZeroClient

# Initialize
client = AgentZeroClient()

# Research company
company = await client.research_company("Acme Corp", "acme.com")

# Find contacts
contacts = await client.find_contacts("Acme Corp", ["doctor", "admin"])

# Enrich contact
contact = await client.enrich_contact(email="john@acme.com")
```

## 📋 Common Patterns

### Pattern 1: Inbound Lead Enrichment
```python
async def enrich_lead(lead_data):
    async with AgentZeroClient() as client:
        company = await client.research_company(
            lead_data["company_name"],
            lead_data["domain"],
            deep_research=False  # Fast
        )
        contact = await client.enrich_contact(
            email=lead_data["email"]
        )
        return {"company": company, "contact": contact}
```

### Pattern 2: Batch Processing
```python
async def research_multiple(companies):
    async with AgentZeroClient() as client:
        tasks = [
            client.research_company(name, domain)
            for name, domain in companies
        ]
        return await asyncio.gather(*tasks)
```

### Pattern 3: Error Handling
```python
try:
    company = await client.research_company("Acme")
    if "error" in company.metadata:
        # Use fallback
        company = get_cached_data("Acme")
except Exception as e:
    logger.error(f"A2A failed: {e}")
    # Use manual data
```

## 🔧 Configuration

```bash
# .env file
AGENT_ZERO_URL=http://agent-zero.railway.internal:80
AGENT_ZERO_TOKEN=your-token-here
```

## 📊 Data Models

### CompanyData
```python
company.name          # str
company.domain        # str
company.industry      # Optional[str]
company.size          # Optional[str]
company.technologies  # List[str]
company.key_people    # List[dict]
```

### ContactData
```python
contact.name          # str
contact.email         # Optional[str]
contact.role          # Optional[str]
contact.linkedin_url  # Optional[str]
contact.interests     # List[str]
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Token not configured | Set `AGENT_ZERO_TOKEN` env var |
| Connection timeout | Increase `timeout` parameter |
| No JSON in response | Use `general_research()` |
| Retry exhausted | Check Agent Zero availability |

## 📚 Resources

- **Full Docs:** `docs/A2A_CLIENT_README.md`
- **Integration:** `docs/A2A_INTEGRATION_GUIDE.md`
- **Examples:** `examples/a2a_usage.py`
- **Tests:** `tests/test_a2a_client.py`
