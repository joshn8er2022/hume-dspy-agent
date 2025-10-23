
"""
Agent Zero A2A Client Usage Examples

This file demonstrates how to use the AgentZeroClient for various
research and enrichment tasks in the Hume ABM system.

Examples:
1. Basic company research
2. Contact discovery and enrichment
3. Multi-step research workflow
4. Error handling and fallbacks
5. Integration with InboundAgent
"""
import asyncio
import logging
from typing import List, Dict, Any

from core.a2a_client import AgentZeroClient, CompanyData, ContactData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Example 1: Basic Company Research
async def example_basic_company_research():
    """Example: Research a company and get structured data."""
    print("\n" + "="*60)
    print("Example 1: Basic Company Research")
    print("="*60)

    async with AgentZeroClient() as client:
        company_data = await client.research_company(
            company_name="Acme Medical Solutions",
            domain="acmemedical.com",
            deep_research=True
        )

        print(f"\n📊 Company: {company_data.name}")
        print(f"   Domain: {company_data.domain}")
        print(f"   Industry: {company_data.industry}")
        print(f"   Size: {company_data.size}")

        return company_data


# Example 2: Contact Discovery
async def example_contact_discovery():
    """Example: Find contacts at a company with specific roles."""
    print("\n" + "="*60)
    print("Example 2: Contact Discovery")
    print("="*60)

    async with AgentZeroClient() as client:
        contacts = await client.find_contacts(
            company_name="Acme Medical Solutions",
            roles=["doctor", "physician", "medical director", "admin"],
            max_contacts=10
        )

        print(f"\n👥 Found {len(contacts)} contacts")
        for i, contact in enumerate(contacts, 1):
            print(f"\n{i}. {contact.name}")
            print(f"   Role: {contact.role}")
            print(f"   Email: {contact.email or 'N/A'}")

        return contacts


# Example 3: Multi-Step Workflow
async def example_multi_step_workflow():
    """Example: Complete research workflow for a new lead."""
    print("\n" + "="*60)
    print("Example 3: Multi-Step Research Workflow")
    print("="*60)

    async with AgentZeroClient() as client:
        # Step 1: Research company
        print("\n🔍 Step 1: Researching company...")
        company = await client.research_company(
            company_name="Acme Medical Solutions",
            domain="acmemedical.com"
        )
        print(f"   ✅ Found: {company.name} ({company.industry})")

        # Step 2: Find contacts
        print("\n🔍 Step 2: Finding contacts...")
        contacts = await client.find_contacts(
            company_name=company.name,
            roles=["doctor", "admin"],
            max_contacts=5
        )
        print(f"   ✅ Found {len(contacts)} contacts")

        # Step 3: Enrich top contacts
        print("\n🔍 Step 3: Enriching contacts...")
        enriched_contacts = []
        for contact in contacts[:3]:
            if contact.email:
                enriched = await client.enrich_contact(
                    email=contact.email,
                    name=contact.name,
                    company=company.name
                )
                enriched_contacts.append(enriched)
                print(f"   ✅ Enriched: {enriched.name}")

        return {
            "company": company,
            "contacts": contacts,
            "enriched_contacts": enriched_contacts
        }


# Example 4: InboundAgent Integration
async def example_inbound_agent_integration():
    """Example: How to integrate A2A client with InboundAgent."""
    print("\n" + "="*60)
    print("Example 4: InboundAgent Integration")
    print("="*60)

    # Simulated inbound lead data
    lead_data = {
        "email": "inquiry@acmemedical.com",
        "company_name": "Acme Medical Solutions",
        "domain": "acmemedical.com",
        "message": "Interested in your medical software solutions"
    }

    print(f"\n📧 Processing inbound lead from: {lead_data['company_name']}")

    async with AgentZeroClient() as client:
        # Research company
        print("\n1️⃣ Researching company...")
        company = await client.research_company(
            company_name=lead_data["company_name"],
            domain=lead_data["domain"],
            deep_research=False
        )

        # Enrich contact
        print("\n2️⃣ Enriching contact...")
        contact = await client.enrich_contact(
            email=lead_data["email"],
            company=lead_data["company_name"]
        )

        # Build enriched lead profile
        enriched_lead = {
            "original_data": lead_data,
            "company": {
                "name": company.name,
                "domain": company.domain,
                "industry": company.industry,
                "size": company.size,
            },
            "contact": {
                "name": contact.name,
                "email": contact.email,
                "role": contact.role,
            },
        }

        print("\n✅ Lead enrichment complete!")
        print(f"   Company: {enriched_lead['company']['name']}")
        print(f"   Contact: {enriched_lead['contact']['name']}")

        return enriched_lead


# Example 5: Batch Processing
async def example_batch_processing():
    """Example: Process multiple companies in batch."""
    print("\n" + "="*60)
    print("Example 5: Batch Processing")
    print("="*60)

    companies_to_research = [
        {"name": "Acme Medical", "domain": "acmemedical.com"},
        {"name": "Beta Health", "domain": "betahealth.com"},
        {"name": "Gamma Devices", "domain": "gammadevices.com"},
    ]

    async with AgentZeroClient() as client:
        tasks = [
            client.research_company(
                company_name=company["name"],
                domain=company["domain"],
                deep_research=False
            )
            for company in companies_to_research
        ]

        print(f"\n🔍 Researching {len(tasks)} companies concurrently...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful

        print(f"\n📊 Batch Results: {successful} successful, {failed} failed")

        return [r for r in results if not isinstance(r, Exception)]


async def main():
    """Run examples."""
    print("\n" + "="*60)
    print("Agent Zero A2A Client - Usage Examples")
    print("="*60)

    # Uncomment to run specific examples
    # await example_basic_company_research()
    # await example_contact_discovery()
    # await example_multi_step_workflow()
    await example_inbound_agent_integration()
    # await example_batch_processing()

    print("\n" + "="*60)
    print("Examples Complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
