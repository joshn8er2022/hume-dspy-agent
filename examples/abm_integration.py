
"""ABM Integration Example - Quick Start Guide

Shows how to integrate the research module into the Hume DSPy ABM system.
"""

import asyncio
from core.research import CompanyResearcher


class ABMOrchestrator:
    """Simple ABM orchestrator using research module."""

    def __init__(self):
        self.researcher = CompanyResearcher(cache_ttl_hours=24)

    async def close(self):
        """Cleanup resources."""
        await self.researcher.close()

    async def qualify_lead(self, email: str, name: str, company: str) -> dict:
        """Qualify a lead for ABM campaign.

        Args:
            email: Lead email
            name: Lead name
            company: Company name

        Returns:
            dict with qualification results
        """
        print(f"
🔍 Qualifying lead: {name} ({email})")

        # Step 1: Enrich contact
        contact = await self.researcher.enrich_contact(email, name, company)
        print(f"  ✅ Enriched: {contact.role or 'Unknown role'}")

        # Step 2: Research company
        if contact.company_domain:
            company_data = await self.researcher.research_company(
                contact.company_domain
            )
            print(f"  ✅ Company: {company_data.name} ({company_data.industry or 'Unknown'})")
        else:
            company_data = None
            print(f"  ⚠️  No company domain found")

        # Step 3: Determine qualification
        is_qualified = False
        reasons = []

        if company_data:
            # Check industry
            if company_data.industry in ["Healthcare", "Technology", "Finance"]:
                is_qualified = True
                reasons.append(f"Target industry: {company_data.industry}")

            # Check role
            if contact.role and any(title in contact.role.lower() for title in ["doctor", "executive", "director", "vp"]):
                is_qualified = True
                reasons.append(f"Decision maker: {contact.role}")

        result = {
            "qualified": is_qualified,
            "contact": contact,
            "company": company_data,
            "reasons": reasons
        }

        print(f"  {'✅ QUALIFIED' if is_qualified else '❌ NOT QUALIFIED'}")
        if reasons:
            for reason in reasons:
                print(f"    - {reason}")

        return result

    async def build_account_campaign(self, target_domain: str) -> dict:
        """Build multi-touch campaign for target account.

        Args:
            target_domain: Target company domain

        Returns:
            dict with campaign data
        """
        print(f"
🎯 Building campaign for: {target_domain}")

        # Step 1: Research company
        print("
📊 Step 1: Research Company")
        company = await self.researcher.research_company(target_domain, deep=True)
        print(f"  ✅ {company.name} - {company.industry or 'Unknown industry'}")

        # Step 2: Find decision makers
        print("
👥 Step 2: Find Decision Makers")
        contacts = await self.researcher.find_contacts(
            company_name=company.name,
            domain=company.domain,
            roles=["executive", "director", "manager", "doctor"]
        )
        print(f"  ✅ Found {len(contacts)} potential contacts")

        # Step 3: Enrich top contacts
        print("
🔍 Step 3: Enrich Top Contacts")
        enriched = []
        for contact in contacts[:5]:  # Top 5
            if contact.email:
                enriched_contact = await self.researcher.enrich_contact(
                    email=contact.email,
                    name=contact.name,
                    company=company.name
                )
                enriched.append(enriched_contact)
        print(f"  ✅ Enriched {len(enriched)} contacts")

        # Step 4: Map relationships
        print("
🔗 Step 4: Map Relationships")
        relationships = {}
        colleagues = []

        for i, c1 in enumerate(enriched):
            for c2 in enriched[i+1:]:
                if c1.email and c2.email:
                    rel = await self.researcher.check_relationship(
                        c1.email, c2.email
                    )
                    if rel == "colleagues":
                        colleagues.append((c1.name, c2.name))
                    relationships[(c1.email, c2.email)] = rel

        print(f"  ✅ Found {len(colleagues)} colleague pairs")

        # Step 5: Build campaign
        campaign = {
            "company": company,
            "contacts": enriched,
            "relationships": relationships,
            "colleague_pairs": colleagues,
            "ready": len(enriched) > 0
        }

        print("
📋 Campaign Summary:")
        print(f"  Company: {company.name}")
        print(f"  Industry: {company.industry or 'Unknown'}")
        print(f"  Decision Makers: {len(enriched)}")
        print(f"  Colleague Pairs: {len(colleagues)}")
        print(f"  Status: {'✅ Ready for outreach' if campaign['ready'] else '❌ Needs more contacts'}")

        return campaign


async def demo_lead_qualification():
    """Demo: Qualify individual leads."""
    print("
" + "="*60)
    print("DEMO: Lead Qualification")
    print("="*60)

    orchestrator = ABMOrchestrator()

    try:
        # Qualify some leads
        leads = [
            ("john.doe@acme.com", "John Doe", "Acme Corp"),
            ("jane.smith@techcorp.com", "Jane Smith", "TechCorp"),
        ]

        qualified_leads = []

        for email, name, company in leads:
            result = await orchestrator.qualify_lead(email, name, company)
            if result["qualified"]:
                qualified_leads.append(result)

        print(f"

📊 Results: {len(qualified_leads)}/{len(leads)} leads qualified")

    finally:
        await orchestrator.close()


async def demo_account_campaign():
    """Demo: Build account-based campaign."""
    print("
" + "="*60)
    print("DEMO: Account-Based Campaign")
    print("="*60)

    orchestrator = ABMOrchestrator()

    try:
        # Build campaign for target account
        campaign = await orchestrator.build_account_campaign("healthcare-inc.com")

        print("

✅ Campaign ready for execution!")

    finally:
        await orchestrator.close()


async def main():
    """Run all demos."""
    await demo_lead_qualification()
    await demo_account_campaign()


if __name__ == "__main__":
    asyncio.run(main())
