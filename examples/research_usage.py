
"""Usage examples for the research module.

Demonstrates how to use CompanyResearcher for ABM workflows.
"""

import asyncio
import logging
from core.research import CompanyResearcher, CompanyData, ContactData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def example_1_basic_company_research():
    """Example 1: Basic company research."""
    print("
" + "="*60)
    print("Example 1: Basic Company Research")
    print("="*60)

    researcher = CompanyResearcher()

    try:
        # Research a company
        company = await researcher.research_company("acme.com", deep=False)

        print(f"
✅ Company Research Results:")
        print(f"  Name: {company.name}")
        print(f"  Domain: {company.domain}")
        print(f"  Industry: {company.industry or 'Unknown'}")
        print(f"  Description: {company.description or 'N/A'}")
        print(f"  Website: {company.website_url}")
        print(f"  LinkedIn: {company.linkedin_url or 'Not found'}")
        print(f"  Researched: {company.researched_at}")

    finally:
        await researcher.close()


async def example_2_deep_company_research():
    """Example 2: Deep company research with employee discovery."""
    print("
" + "="*60)
    print("Example 2: Deep Company Research")
    print("="*60)

    researcher = CompanyResearcher()

    try:
        # Deep research (slower, more comprehensive)
        company = await researcher.research_company("techcorp.com", deep=True)

        print(f"
✅ Deep Research Results:")
        print(f"  Company: {company.name}")
        print(f"  Employees Found: {len(company.employees)}")

        if company.employees:
            print("
  Top Employees:")
            for emp in company.employees[:5]:
                print(f"    - {emp}")

    finally:
        await researcher.close()


async def example_3_find_contacts():
    """Example 3: Find contacts at a company by role."""
    print("
" + "="*60)
    print("Example 3: Find Contacts by Role")
    print("="*60)

    researcher = CompanyResearcher()

    try:
        # Find doctors and admins at a healthcare company
        contacts = await researcher.find_contacts(
            company_name="HealthCare Inc",
            domain="healthcare-inc.com",
            roles=["doctor", "admin", "executive"]
        )

        print(f"
✅ Found {len(contacts)} contacts:")

        for contact in contacts:
            print(f"
  {contact.name}")
            print(f"    Role: {contact.role or 'Unknown'}")
            print(f"    Email: {contact.email or 'Not found'}")
            print(f"    LinkedIn: {contact.linkedin_url or 'Not found'}")

    finally:
        await researcher.close()


async def example_4_enrich_contact():
    """Example 4: Enrich contact information."""
    print("
" + "="*60)
    print("Example 4: Contact Enrichment")
    print("="*60)

    researcher = CompanyResearcher()

    try:
        # Enrich a contact
        contact = await researcher.enrich_contact(
            email="john.doe@acme.com",
            name="John Doe",
            company="Acme Corp"
        )

        print(f"
✅ Enriched Contact:")
        print(f"  Name: {contact.name}")
        print(f"  Email: {contact.email}")
        print(f"  Role: {contact.role or 'Unknown'}")
        print(f"  Company: {contact.company}")
        print(f"  Domain: {contact.company_domain}")
        print(f"  LinkedIn: {contact.linkedin_url or 'Not found'}")
        print(f"  Interests: {', '.join(contact.interests) if contact.interests else 'None'}")

    finally:
        await researcher.close()


async def example_5_check_relationships():
    """Example 5: Check if contacts are colleagues."""
    print("
" + "="*60)
    print("Example 5: Relationship Mapping")
    print("="*60)

    researcher = CompanyResearcher()

    try:
        # Check if two contacts work together
        relationship1 = await researcher.check_relationship(
            "john@acme.com",
            "jane@acme.com"
        )

        relationship2 = await researcher.check_relationship(
            "john@acme.com",
            "bob@other.com"
        )

        print(f"
✅ Relationship Analysis:")
        print(f"  john@acme.com + jane@acme.com: {relationship1}")
        print(f"  john@acme.com + bob@other.com: {relationship2}")

    finally:
        await researcher.close()


async def example_6_batch_research():
    """Example 6: Batch research multiple companies."""
    print("
" + "="*60)
    print("Example 6: Batch Company Research")
    print("="*60)

    researcher = CompanyResearcher()

    try:
        # Research multiple companies in parallel
        domains = [
            "acme.com",
            "techcorp.com",
            "healthcare-inc.com",
            "finance-co.com"
        ]

        print(f"
Researching {len(domains)} companies...")
        companies = await researcher.batch_research_companies(domains, deep=False)

        print(f"
✅ Batch Research Complete: {len(companies)} successful")

        for company in companies:
            print(f"
  {company.name}")
            print(f"    Domain: {company.domain}")
            print(f"    Industry: {company.industry or 'Unknown'}")

    finally:
        await researcher.close()


async def example_7_abm_workflow():
    """Example 7: Complete ABM workflow."""
    print("
" + "="*60)
    print("Example 7: Complete ABM Workflow")
    print("="*60)

    researcher = CompanyResearcher()

    try:
        # Step 1: Research target company
        print("
📊 Step 1: Research Company")
        company = await researcher.research_company("target-company.com", deep=True)
        print(f"  ✅ Researched: {company.name}")

        # Step 2: Find decision makers
        print("
👥 Step 2: Find Decision Makers")
        contacts = await researcher.find_contacts(
            company_name=company.name,
            domain=company.domain,
            roles=["executive", "director", "manager"]
        )
        print(f"  ✅ Found {len(contacts)} decision makers")

        # Step 3: Enrich top contacts
        print("
🔍 Step 3: Enrich Top Contacts")
        enriched_contacts = []
        for contact in contacts[:3]:  # Top 3
            if contact.email:
                enriched = await researcher.enrich_contact(
                    email=contact.email,
                    name=contact.name,
                    company=company.name
                )
                enriched_contacts.append(enriched)

        print(f"  ✅ Enriched {len(enriched_contacts)} contacts")

        # Step 4: Map relationships
        print("
🔗 Step 4: Map Relationships")
        if len(enriched_contacts) >= 2:
            for i in range(len(enriched_contacts) - 1):
                c1 = enriched_contacts[i]
                c2 = enriched_contacts[i + 1]
                if c1.email and c2.email:
                    rel = await researcher.check_relationship(c1.email, c2.email)
                    print(f"  {c1.name} + {c2.name}: {rel}")

        # Step 5: Summary
        print("
📋 ABM Research Summary:")
        print(f"  Company: {company.name}")
        print(f"  Industry: {company.industry or 'Unknown'}")
        print(f"  Decision Makers: {len(contacts)}")
        print(f"  Enriched Profiles: {len(enriched_contacts)}")
        print(f"  Ready for outreach: ✅")

    finally:
        await researcher.close()


async def example_8_caching_demo():
    """Example 8: Demonstrate caching behavior."""
    print("
" + "="*60)
    print("Example 8: Caching Demonstration")
    print("="*60)

    researcher = CompanyResearcher(cache_ttl_hours=24)

    try:
        import time

        # First research (cache miss)
        print("
🔍 First research (cache miss)...")
        start = time.time()
        company1 = await researcher.research_company("example.com")
        time1 = time.time() - start
        print(f"  ✅ Completed in {time1:.3f}s")

        # Second research (cache hit)
        print("
⚡ Second research (cache hit)...")
        start = time.time()
        company2 = await researcher.research_company("example.com")
        time2 = time.time() - start
        print(f"  ✅ Completed in {time2:.3f}s")

        print(f"
📊 Cache Performance:")
        print(f"  First call: {time1:.3f}s")
        print(f"  Cached call: {time2:.3f}s")
        print(f"  Speedup: {time1/time2:.1f}x faster")

    finally:
        await researcher.close()


async def main():
    """Run all examples."""
    print("
" + "#"*60)
    print("# Research Module Usage Examples")
    print("#"*60)

    # Run examples
    await example_1_basic_company_research()
    await example_2_deep_company_research()
    await example_3_find_contacts()
    await example_4_enrich_contact()
    await example_5_check_relationships()
    await example_6_batch_research()
    await example_7_abm_workflow()
    await example_8_caching_demo()

    print("
" + "#"*60)
    print("# All Examples Complete!")
    print("#"*60 + "
")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
