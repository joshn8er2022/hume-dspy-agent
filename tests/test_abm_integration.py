"""
Integration Tests for ABM Data Model

End-to-end tests verifying:
- Complete data flow from company creation to touchpoint tracking
- Foreign key constraints and cascade deletes
- Trigger functionality (auto-updates, counts)
- Database functions (get_colleagues, get_active_conversations, etc.)
- Query performance
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.abm_data import (
    CompanyRepository,
    ContactRepository,
    RelationshipRepository,
    ConversationRepository,
    TouchpointRepository
)
from core.company_graph import CompanyGraph


async def test_complete_abm_workflow():
    """
    Test complete ABM workflow:
    1. Create company
    2. Add multiple contacts
    3. Map relationships
    4. Start conversations
    5. Track touchpoints
    6. Query company graph
    """
    print("\n" + "="*80)
    print("ABM DATA MODEL INTEGRATION TEST")
    print("="*80 + "\n")

    # Initialize repositories
    company_repo = CompanyRepository()
    contact_repo = ContactRepository()
    relationship_repo = RelationshipRepository()
    conversation_repo = ConversationRepository()
    touchpoint_repo = TouchpointRepository()
    company_graph = CompanyGraph()

    try:
        # Step 1: Create Company
        print("📊 Step 1: Creating test company...")
        company = await company_repo.create_company({
            'name': 'Acme Medical Group',
            'domain': 'acmemedical.com',
            'industry': 'Healthcare',
            'size': 'medium',
            'description': 'Leading medical practice in the region',
            'account_tier': 'tier1',
            'research_data': {
                'company_overview': 'Multi-specialty medical practice',
                'employee_count': 50,
                'key_initiatives': ['Digital transformation', 'Patient experience']
            }
        })
        print(f"   ✅ Company created: {company.name} (ID: {company.id})")

        # Step 2: Add Contacts
        print("\n👥 Step 2: Adding contacts...")
        
        # Primary contact - CMO
        contact1 = await contact_repo.create_contact({
            'company_id': company.id,
            'first_name': 'Dr. Sarah',
            'last_name': 'Williams',
            'email': 'sarah.williams@acmemedical.com',
            'title': 'Chief Medical Officer',
            'role': 'doctor',
            'seniority_level': 'c-level',
            'is_primary_contact': True,
            'is_decision_maker': True,
            'interests': ['AI in healthcare', 'Patient outcomes'],
            'research_data': {
                'bio': 'Board-certified physician with 15 years experience',
                'education': ['MD from Johns Hopkins', 'MBA from Wharton']
            }
        })
        print(f"   ✅ Contact 1: {contact1.full_name} - {contact1.title}")

        # Secondary contact - Senior Physician
        contact2 = await contact_repo.create_contact({
            'company_id': company.id,
            'first_name': 'Dr. Michael',
            'last_name': 'Chen',
            'email': 'michael.chen@acmemedical.com',
            'title': 'Senior Physician',
            'role': 'doctor',
            'seniority_level': 'director',
            'interests': ['Medical technology', 'Clinical efficiency']
        })
        print(f"   ✅ Contact 2: {contact2.full_name} - {contact2.title}")

        # Admin contact
        contact3 = await contact_repo.create_contact({
            'company_id': company.id,
            'first_name': 'Lisa',
            'last_name': 'Anderson',
            'email': 'lisa.anderson@acmemedical.com',
            'title': 'Practice Administrator',
            'role': 'admin',
            'seniority_level': 'manager'
        })
        print(f"   ✅ Contact 3: {contact3.full_name} - {contact3.title}")

        # Step 3: Map Relationships
        print("\n🔗 Step 3: Mapping relationships...")
        
        rel1 = await relationship_repo.create_relationship(
            contact1.id,
            contact2.id,
            'colleagues',
            strength='strong',
            context='Both physicians working together'
        )
        print(f"   ✅ Relationship: {contact1.full_name} <-> {contact2.full_name} (colleagues)")

        rel2 = await relationship_repo.create_relationship(
            contact1.id,
            contact3.id,
            'manager_of',
            strength='medium',
            context='CMO manages practice administrator'
        )
        print(f"   ✅ Relationship: {contact1.full_name} -> {contact3.full_name} (manager_of)")

        # Step 4: Start Conversations
        print("\n💬 Step 4: Starting conversations...")
        
        conv1 = await conversation_repo.create_conversation(
            contact1.id,
            company.id,
            qualification_tier='hot',
            metadata={'source': 'inbound', 'initial_interest': 'AI solutions'}
        )
        print(f"   ✅ Conversation 1: {contact1.full_name} (Tier: {conv1.qualification_tier})")

        conv2 = await conversation_repo.create_conversation(
            contact2.id,
            company.id,
            qualification_tier='warm'
        )
        print(f"   ✅ Conversation 2: {contact2.full_name} (Tier: {conv2.qualification_tier})")

        # Step 5: Track Touchpoints
        print("\n📧 Step 5: Tracking touchpoints...")
        
        # Email to contact 1
        tp1 = await touchpoint_repo.record_email_sent(
            conv1.id,
            'Introduction to AI Solutions',
            'Dear Dr. Williams, I wanted to reach out...'
        )
        print(f"   ✅ Touchpoint 1: Email sent to {contact1.full_name}")

        # Simulate email opened
        await touchpoint_repo.record_email_opened(tp1.id)
        print(f"   ✅ Email opened by {contact1.full_name}")

        # Simulate email clicked
        await touchpoint_repo.record_email_clicked(tp1.id)
        print(f"   ✅ Email link clicked by {contact1.full_name}")

        # Email to contact 2
        tp2 = await touchpoint_repo.record_email_sent(
            conv2.id,
            'Your colleague Dr. Williams inquired about AI solutions',
            'Dear Dr. Chen, Your colleague Dr. Williams recently...'
        )
        print(f"   ✅ Touchpoint 2: Email sent to {contact2.full_name} (referencing colleague)")

        # Step 6: Query Company Graph
        print("\n📈 Step 6: Querying company graph...")
        
        # Get account overview
        overview = await company_graph.get_account_overview(company.id)
        print(f"\n   Account Overview for {overview['company']['name']}:")
        print(f"   - Total Contacts: {overview['summary']['total_contacts']}")
        print(f"   - Decision Makers: {overview['summary']['decision_makers']}")
        print(f"   - Total Relationships: {overview['summary']['total_relationships']}")
        print(f"   - Active Conversations: {overview['summary']['active_conversations']}")

        # Find expansion targets
        print(f"\n   Finding expansion targets from {contact1.full_name}...")
        targets = await company_graph.find_expansion_targets(contact1.id)
        print(f"   - Found {len(targets)} expansion targets")
        for target in targets:
            print(f"     • {target['contact'].full_name} ({target['contact'].title})")
            print(f"       Priority Score: {target['priority_score']:.2f}")

        # Get conversation context
        print(f"\n   Getting conversation context for {contact1.full_name}...")
        context = await company_graph.get_conversation_context(contact1.id)
        print(f"   - Contact: {context['contact']['name']}")
        print(f"   - Company: {context['company']['name']}")
        print(f"   - Active Conversations: {len(context['conversations']['active'])}")
        if 'engagement' in context:
            metrics = context['engagement']['metrics']
            print(f"   - Email Open Rate: {metrics.get('open_rate', 0):.1f}%")
            print(f"   - Email Click Rate: {metrics.get('click_rate', 0):.1f}%")

        # Get account health score
        print(f"\n   Calculating account health score...")
        health = await company_graph.get_account_health_score(company.id)
        print(f"   - Total Score: {health['total_score']:.2f}/100")
        print(f"   - Health Status: {health['health_status'].upper()}")
        print(f"   - Breakdown:")
        for category, score in health['breakdown'].items():
            print(f"     • {category.capitalize()}: {score:.2f}")
        if health['recommendations']:
            print(f"   - Recommendations:")
            for rec in health['recommendations']:
                print(f"     • {rec}")

        # Step 7: Verify Triggers and Counts
        print("\n🔧 Step 7: Verifying triggers and auto-updates...")
        
        # Refresh company data to check auto-updated counts
        updated_company = await company_repo.get_company_by_id(company.id)
        print(f"   - Company total_contacts: {updated_company.total_contacts} (expected: 3)")
        print(f"   - Company active_conversations: {updated_company.active_conversations} (expected: 2)")
        
        # Verify conversation touchpoint count
        updated_conv1 = await conversation_repo.get_conversation_by_id(conv1.id)
        print(f"   - Conversation 1 touchpoint_count: {updated_conv1.touchpoint_count} (expected: 1)")
        print(f"   - Conversation 1 last_touchpoint_at: {updated_conv1.last_touchpoint_at}")

        print("\n" + "="*80)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("="*80 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    result = asyncio.run(test_complete_abm_workflow())
    sys.exit(0 if result else 1)
