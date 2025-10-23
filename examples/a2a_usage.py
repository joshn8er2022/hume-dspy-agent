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
    """
    Example: Research a company and get structured data.
    
    This is the most common use case - researching a company
    to understand their business, size, and key people.
    """
    print("\n" + "="*60)
    print("Example 1: Basic Company Research")
    print("="*60)
    
    async with AgentZeroClient() as client:
        # Research a company
        company_data = await client.research_company(
            company_name="Acme Medical Solutions",
            domain="acmemedical.com",
            deep_research=True  # More thorough but slower
        )
        
        # Display results
        print(f"\n📊 Company: {company_data.name}")
        print(f"   Domain: {company_data.domain}")
        print(f"   Industry: {company_data.industry}")
        print(f"   Size: {company_data.size}")
        print(f"   Location: {company_data.location}")
        print(f"   Description: {company_data.description}")
        
        if company_data.technologies:
            print(f"\n💻 Technologies: {', '.join(company_data.technologies)}")
        
        if company_data.key_people:
            print(f"\n👥 Key People:")
            for person in company_data.key_people:
                print(f"   - {person.get('name')}: {person.get('role')}")
        
        if company_data.recent_news:
            print(f"\n📰 Recent News:")
            for news in company_data.recent_news[:3]:
                print(f"   - {news}")
        
        return company_data


# Example 2: Contact Discovery
async def example_contact_discovery():
    """
    Example: Find contacts at a company with specific roles.
    
    This is useful for finding decision-makers and key contacts
    at target companies.
    """
    print("\n" + "="*60)
    print("Example 2: Contact Discovery")
    print("="*60)
    
    async with AgentZeroClient() as client:
        # Find contacts with specific roles
        contacts = await client.find_contacts(
            company_name="Acme Medical Solutions",
            roles=["doctor", "physician", "medical director", "admin"],
            max_contacts=10
        )
        
        # Display results
        print(f"\n👥 Found {len(contacts)} contacts:")
        for i, contact in enumerate(contacts, 1):
            print(f"\n{i}. {contact.name}")
            print(f"   Role: {contact.role}")
            print(f"   Email: {contact.email or 'N/A'}")
            print(f"   LinkedIn: {contact.linkedin_url or 'N/A'}")
            print(f"   Location: {contact.location or 'N/A'}")
        
        return contacts


# Example 3: Contact Enrichment
async def example_contact_enrichment():
    """
    Example: Enrich contact information.
    
    This is useful when you have partial contact information
    and want to find more details.
    """
    print("\n" + "="*60)
    print("Example 3: Contact Enrichment")
    print("="*60)
    
    async with AgentZeroClient() as client:
        # Enrich contact with just email
        contact = await client.enrich_contact(
            email="john.doe@acmemedical.com",
            name="John Doe"
        )
        
        # Display results
        print(f"\n👤 Enriched Contact: {contact.name}")
        print(f"   Email: {contact.email}")
        print(f"   Role: {contact.role}")
        print(f"   Company: {contact.company}")
        print(f"   LinkedIn: {contact.linkedin_url or 'N/A'}")
        print(f"   Phone: {contact.phone or 'N/A'}")
        print(f"   Location: {contact.location or 'N/A'}")
        
        if contact.interests:
            print(f"   Interests: {', '.join(contact.interests)}")
        
        return contact


# Example 4: Multi-Step Research Workflow
async def example_multi_step_workflow():
    """
    Example: Complete research workflow for a new lead.
    
    This demonstrates a typical workflow:
    1. Research the company
    2. Find key contacts
    3. Enrich contact information
    """
    print("\n" + "="*60)
    print("Example 4: Multi-Step Research Workflow")
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
        for contact in contacts[:3]:  # Enrich top 3
            if contact.email:
                enriched = await client.enrich_contact(
                    email=contact.email,
                    name=contact.name,
                    company=company.name
                )
                enriched_contacts.append(enriched)
                print(f"   ✅ Enriched: {enriched.name}")
        
        # Summary
        print("\n" + "="*60)
        print("📊 Research Summary")
        print("="*60)
        print(f"Company: {company.name}")
        print(f"Industry: {company.industry}")
        print(f"Size: {company.size}")
        print(f"Contacts Found: {len(contacts)}")
        print(f"Contacts Enriched: {len(enriched_contacts)}")
        
        return {
            "company": company,
            "contacts": contacts,
            "enriched_contacts": enriched_contacts
        }


# Example 5: Error Handling and Fallbacks
async def example_error_handling():
    """
    Example: Proper error handling and fallback strategies.
    
    This shows how to handle errors gracefully and implement
    fallback strategies when Agent Zero is unavailable.
    """
    print("\n" + "="*60)
    print("Example 5: Error Handling and Fallbacks")
    print("="*60)
    
    async with AgentZeroClient(timeout=30, max_retries=2) as client:
        try:
            # Try to research company
            company = await client.research_company(
                company_name="Test Company",
                domain="test.com"
            )
            
            # Check if research was successful
            if "error" in company.metadata:
                print("⚠️ Research failed, using fallback data")
                # Implement fallback logic here
                # e.g., use basic heuristics, cached data, or manual input
            else:
                print(f"✅ Research successful: {company.name}")
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            print("❌ Agent Zero unavailable, using fallback strategy")
            
            # Fallback: Create minimal company data
            company = CompanyData(
                name="Test Company",
                domain="test.com",
                metadata={"fallback": True, "error": str(e)}
            )
        
        return company


# Example 6: General Research Query
async def example_general_research():
    """
    Example: Use general research for custom queries.
    
    This is useful for ad-hoc research tasks that don't fit
    the specific company/contact methods.
    """
    print("\n" + "="*60)
    print("Example 6: General Research Query")
    print("="*60)
    
    async with AgentZeroClient() as client:
        # General research query
        result = await client.general_research(
            query="Find the top 5 medical device companies in California "
                  "that specialize in surgical equipment. Include company name, "
                  "location, and website.",
            structured_output=True  # Try to get JSON response
        )
        
        print("\n📊 Research Results:")
        if isinstance(result, dict):
            # Structured output
            import json
            print(json.dumps(result, indent=2))
        else:
            # Plain text output
            print(result)
        
        return result


# Example 7: Integration with InboundAgent
async def example_inbound_agent_integration():
    """
    Example: How to integrate A2A client with InboundAgent.
    
    This shows the pattern for using the A2A client within
    the Hume DSPy agent's InboundAgent workflow.
    """
    print("\n" + "="*60)
    print("Example 7: InboundAgent Integration")
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
        # Step 1: Research company
        print("\n1️⃣ Researching company...")
        company = await client.research_company(
            company_name=lead_data["company_name"],
            domain=lead_data["domain"],
            deep_research=False  # Quick research for inbound leads
        )
        
        # Step 2: Enrich contact
        print("\n2️⃣ Enriching contact...")
        contact = await client.enrich_contact(
            email=lead_data["email"],
            company=lead_data["company_name"]
        )
        
        # Step 3: Build enriched lead profile
        enriched_lead = {
            "original_data": lead_data,
            "company": {
                "name": company.name,
                "domain": company.domain,
                "industry": company.industry,
                "size": company.size,
                "location": company.location,
                "technologies": company.technologies,
            },
            "contact": {
                "name": contact.name,
                "email": contact.email,
                "role": contact.role,
                "linkedin_url": contact.linkedin_url,
                "interests": contact.interests,
            },
            "enrichment_timestamp": company.metadata.get("researched_at"),
        }
        
        print("\n✅ Lead enrichment complete!")
        print(f"   Company: {enriched_lead['company']['name']}")
        print(f"   Industry: {enriched_lead['company']['industry']}")
        print(f"   Contact: {enriched_lead['contact']['name']}")
        print(f"   Role: {enriched_lead['contact']['role']}")
        
        # This enriched data can now be used for:
        # - Lead qualification scoring
        # - Personalized response generation
        # - CRM enrichment
        # - Routing to appropriate sales rep
        
        return enriched_lead


# Example 8: Batch Processing
async def example_batch_processing():
    """
    Example: Process multiple companies in batch.
    
    This shows how to efficiently research multiple companies
    using concurrent requests.
    """
    print("\n" + "="*60)
    print("Example 8: Batch Processing")
    print("="*60)
    
    companies_to_research = [
        {"name": "Acme Medical", "domain": "acmemedical.com"},
        {"name": "Beta Health", "domain": "betahealth.com"},
        {"name": "Gamma Devices", "domain": "gammadevices.com"},
    ]
    
    async with AgentZeroClient() as client:
        # Process companies concurrently
        tasks = [
            client.research_company(
                company_name=company["name"],
                domain=company["domain"],
                deep_research=False  # Faster for batch processing
            )
            for company in companies_to_research
        ]
        
        print(f"\n🔍 Researching {len(tasks)} companies concurrently...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = 0
        failed = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   ❌ {companies_to_research[i]['name']}: Failed")
                failed += 1
            else:
                print(f"   ✅ {result.name}: {result.industry}")
                successful += 1
        
        print(f"\n📊 Batch Results: {successful} successful, {failed} failed")
        
        return [r for r in results if not isinstance(r, Exception)]


# Main function to run all examples
async def main():
    """
    Run all examples.
    
    Uncomment the examples you want to run.
    """
    print("\n" + "="*60)
    print("Agent Zero A2A Client - Usage Examples")
    print("="*60)
    
    # Run examples (uncomment to enable)
    # await example_basic_company_research()
    # await example_contact_discovery()
    # await example_contact_enrichment()
    # await example_multi_step_workflow()
    # await example_error_handling()
    # await example_general_research()
    await example_inbound_agent_integration()
    # await example_batch_processing()
    
    print("\n" + "="*60)
    print("Examples Complete!")
    print("="*60)


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
EXAMPLEOF
echo "✅ Created examples file"
