"""
Unit Tests for ABM Data Access Layer

Tests all repository classes and company graph functionality:
- CompanyRepository
- ContactRepository
- RelationshipRepository
- ConversationRepository
- TouchpointRepository
- CompanyGraph
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.abm_data import (
    CompanyRepository,
    ContactRepository,
    RelationshipRepository,
    ConversationRepository,
    TouchpointRepository,
    Company,
    Contact,
    Relationship,
    Conversation,
    Touchpoint
)
from core.company_graph import CompanyGraph


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def company_repo():
    """Company repository fixture"""
    return CompanyRepository()


@pytest.fixture
def contact_repo():
    """Contact repository fixture"""
    return ContactRepository()


@pytest.fixture
def relationship_repo():
    """Relationship repository fixture"""
    return RelationshipRepository()


@pytest.fixture
def conversation_repo():
    """Conversation repository fixture"""
    return ConversationRepository()


@pytest.fixture
def touchpoint_repo():
    """Touchpoint repository fixture"""
    return TouchpointRepository()


@pytest.fixture
def company_graph():
    """Company graph fixture"""
    return CompanyGraph()


@pytest.fixture
async def sample_company(company_repo):
    """Create sample company for testing"""
    company_data = {
        'name': 'Test Medical Practice',
        'domain': 'testmedical.com',
        'industry': 'Healthcare',
        'size': 'medium',
        'description': 'A test medical practice',
        'account_tier': 'tier1'
    }
    company = await company_repo.create_company(company_data)
    yield company
    # Cleanup handled by cascade delete


@pytest.fixture
async def sample_contacts(contact_repo, sample_company):
    """Create sample contacts for testing"""
    contacts = []
    
    # Primary contact - decision maker
    contact1_data = {
        'company_id': sample_company.id,
        'first_name': 'Dr. John',
        'last_name': 'Smith',
        'email': 'john.smith@testmedical.com',
        'title': 'Chief Medical Officer',
        'role': 'doctor',
        'seniority_level': 'c-level',
        'is_primary_contact': True,
        'is_decision_maker': True
    }
    contact1 = await contact_repo.create_contact(contact1_data)
    contacts.append(contact1)
    
    # Secondary contact - colleague
    contact2_data = {
        'company_id': sample_company.id,
        'first_name': 'Dr. Sue',
        'last_name': 'Johnson',
        'email': 'sue.johnson@testmedical.com',
        'title': 'Senior Physician',
        'role': 'doctor',
        'seniority_level': 'director'
    }
    contact2 = await contact_repo.create_contact(contact2_data)
    contacts.append(contact2)
    
    yield contacts


# ============================================================================
# COMPANY REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_company(company_repo):
    """Test creating a company"""
    company_data = {
        'name': 'Test Company',
        'domain': 'test.com',
        'industry': 'Technology'
    }
    company = await company_repo.create_company(company_data)
    
    assert company.id is not None
    assert company.name == 'Test Company'
    assert company.domain == 'test.com'
    assert company.industry == 'Technology'


@pytest.mark.asyncio
async def test_get_company_by_domain(company_repo, sample_company):
    """Test getting company by domain"""
    company = await company_repo.get_company_by_domain('testmedical.com')
    
    assert company is not None
    assert company.id == sample_company.id
    assert company.name == sample_company.name


@pytest.mark.asyncio
async def test_update_company(company_repo, sample_company):
    """Test updating company"""
    update_data = {
        'account_tier': 'strategic',
        'account_status': 'engaged'
    }
    updated = await company_repo.update_company(sample_company.id, update_data)
    
    assert updated.account_tier == 'strategic'
    assert updated.account_status == 'engaged'


@pytest.mark.asyncio
async def test_search_companies(company_repo, sample_company):
    """Test searching companies"""
    results = await company_repo.search_companies('Test Medical')
    
    assert len(results) > 0
    assert any(c.id == sample_company.id for c in results)


# ============================================================================
# CONTACT REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_contact(contact_repo, sample_company):
    """Test creating a contact"""
    contact_data = {
        'company_id': sample_company.id,
        'first_name': 'Jane',
        'last_name': 'Doe',
        'email': 'jane.doe@testmedical.com',
        'title': 'Administrator'
    }
    contact = await contact_repo.create_contact(contact_data)
    
    assert contact.id is not None
    assert contact.full_name == 'Jane Doe'
    assert contact.email == 'jane.doe@testmedical.com'


@pytest.mark.asyncio
async def test_get_contact_by_email(contact_repo, sample_contacts):
    """Test getting contact by email"""
    contact = await contact_repo.get_contact_by_email('john.smith@testmedical.com')
    
    assert contact is not None
    assert contact.first_name == 'Dr. John'
    assert contact.last_name == 'Smith'


@pytest.mark.asyncio
async def test_find_contacts_by_company(contact_repo, sample_company, sample_contacts):
    """Test finding contacts by company"""
    contacts = await contact_repo.find_contacts_by_company(sample_company.id)
    
    assert len(contacts) >= 2
    assert all(c.company_id == sample_company.id for c in contacts)


@pytest.mark.asyncio
async def test_find_decision_makers(contact_repo, sample_company, sample_contacts):
    """Test finding decision makers"""
    decision_makers = await contact_repo.find_decision_makers(sample_company.id)
    
    assert len(decision_makers) >= 1
    assert all(c.is_decision_maker for c in decision_makers)


@pytest.mark.asyncio
async def test_find_primary_contact(contact_repo, sample_company, sample_contacts):
    """Test finding primary contact"""
    primary = await contact_repo.find_primary_contact(sample_company.id)
    
    assert primary is not None
    assert primary.is_primary_contact
    assert primary.first_name == 'Dr. John'


# ============================================================================
# RELATIONSHIP REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_relationship(relationship_repo, sample_contacts):
    """Test creating a relationship"""
    contact1, contact2 = sample_contacts[0], sample_contacts[1]
    
    relationship = await relationship_repo.create_relationship(
        contact1.id,
        contact2.id,
        'colleagues',
        strength='strong'
    )
    
    assert relationship.id is not None
    assert relationship.relationship_type == 'colleagues'
    assert relationship.strength == 'strong'


@pytest.mark.asyncio
async def test_get_contact_relationships(relationship_repo, sample_contacts):
    """Test getting contact relationships"""
    contact1, contact2 = sample_contacts[0], sample_contacts[1]
    
    # Create relationship
    await relationship_repo.create_relationship(
        contact1.id,
        contact2.id,
        'colleagues'
    )
    
    # Get relationships
    relationships = await relationship_repo.get_contact_relationships(contact1.id)
    
    assert len(relationships) >= 1
    assert any(
        r.contact_id_1 == contact1.id or r.contact_id_2 == contact1.id
        for r in relationships
    )


@pytest.mark.asyncio
async def test_check_relationship(relationship_repo, sample_contacts):
    """Test checking if relationship exists"""
    contact1, contact2 = sample_contacts[0], sample_contacts[1]
    
    # Create relationship
    await relationship_repo.create_relationship(
        contact1.id,
        contact2.id,
        'colleagues'
    )
    
    # Check relationship
    relationship = await relationship_repo.check_relationship(contact1.id, contact2.id)
    
    assert relationship is not None
    assert relationship.relationship_type == 'colleagues'


# ============================================================================
# CONVERSATION REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_conversation(conversation_repo, sample_company, sample_contacts):
    """Test creating a conversation"""
    contact = sample_contacts[0]
    
    conversation = await conversation_repo.create_conversation(
        contact.id,
        sample_company.id,
        qualification_tier='hot'
    )
    
    assert conversation.id is not None
    assert conversation.contact_id == contact.id
    assert conversation.company_id == sample_company.id
    assert conversation.qualification_tier == 'hot'
    assert conversation.status == 'active'


@pytest.mark.asyncio
async def test_update_conversation_status(conversation_repo, sample_company, sample_contacts):
    """Test updating conversation status"""
    contact = sample_contacts[0]
    
    # Create conversation
    conversation = await conversation_repo.create_conversation(
        contact.id,
        sample_company.id
    )
    
    # Update status
    updated = await conversation_repo.update_conversation_status(
        conversation.id,
        'won',
        outcome='meeting_scheduled'
    )
    
    assert updated.status == 'won'
    assert updated.outcome == 'meeting_scheduled'
    assert updated.closed_at is not None


@pytest.mark.asyncio
async def test_update_conversation_context(conversation_repo, sample_company, sample_contacts):
    """Test updating conversation context"""
    contact = sample_contacts[0]
    
    # Create conversation
    conversation = await conversation_repo.create_conversation(
        contact.id,
        sample_company.id
    )
    
    # Update context
    context_updates = {
        'topics_discussed': ['pricing', 'features'],
        'pain_points_identified': ['manual processes']
    }
    updated = await conversation_repo.update_conversation_context(
        conversation.id,
        context_updates
    )
    
    assert 'topics_discussed' in updated.context
    assert 'pain_points_identified' in updated.context


# ============================================================================
# TOUCHPOINT REPOSITORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_touchpoint(touchpoint_repo, conversation_repo, sample_company, sample_contacts):
    """Test creating a touchpoint"""
    contact = sample_contacts[0]
    
    # Create conversation
    conversation = await conversation_repo.create_conversation(
        contact.id,
        sample_company.id
    )
    
    # Create touchpoint
    touchpoint = await touchpoint_repo.create_touchpoint(
        conversation.id,
        'email',
        'outbound',
        {
            'subject': 'Test Email',
            'content': 'Test content',
            'sent_at': datetime.utcnow().isoformat()
        }
    )
    
    assert touchpoint.id is not None
    assert touchpoint.channel == 'email'
    assert touchpoint.direction == 'outbound'
    assert touchpoint.subject == 'Test Email'


@pytest.mark.asyncio
async def test_record_email_sent(touchpoint_repo, conversation_repo, sample_company, sample_contacts):
    """Test recording email sent"""
    contact = sample_contacts[0]
    
    # Create conversation
    conversation = await conversation_repo.create_conversation(
        contact.id,
        sample_company.id
    )
    
    # Record email
    touchpoint = await touchpoint_repo.record_email_sent(
        conversation.id,
        'Follow-up Email',
        'Thanks for your time...'
    )
    
    assert touchpoint.channel == 'email'
    assert touchpoint.direction == 'outbound'
    assert touchpoint.subject == 'Follow-up Email'
    assert touchpoint.sent_at is not None


@pytest.mark.asyncio
async def test_get_touchpoints(touchpoint_repo, conversation_repo, sample_company, sample_contacts):
    """Test getting touchpoints for a conversation"""
    contact = sample_contacts[0]
    
    # Create conversation
    conversation = await conversation_repo.create_conversation(
        contact.id,
        sample_company.id
    )
    
    # Create multiple touchpoints
    await touchpoint_repo.record_email_sent(conversation.id, 'Email 1', 'Content 1')
    await touchpoint_repo.record_email_sent(conversation.id, 'Email 2', 'Content 2')
    
    # Get touchpoints
    touchpoints = await touchpoint_repo.get_touchpoints(conversation.id)
    
    assert len(touchpoints) >= 2
    assert all(t.conversation_id == conversation.id for t in touchpoints)


# ============================================================================
# COMPANY GRAPH TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_account_overview(company_graph, sample_company, sample_contacts):
    """Test getting account overview"""
    overview = await company_graph.get_account_overview(sample_company.id)
    
    assert overview['company']['id'] == sample_company.id
    assert len(overview['contacts']) >= 2
    assert overview['summary']['total_contacts'] >= 2
    assert overview['summary']['decision_makers'] >= 1


@pytest.mark.asyncio
async def test_find_expansion_targets(
    company_graph,
    relationship_repo,
    sample_contacts
):
    """Test finding expansion targets"""
    contact1, contact2 = sample_contacts[0], sample_contacts[1]
    
    # Create relationship
    await relationship_repo.create_relationship(
        contact1.id,
        contact2.id,
        'colleagues',
        strength='strong'
    )
    
    # Find expansion targets
    targets = await company_graph.find_expansion_targets(contact1.id)
    
    assert len(targets) >= 1
    assert any(t['contact'].id == contact2.id for t in targets)


@pytest.mark.asyncio
async def test_get_conversation_context(
    company_graph,
    conversation_repo,
    sample_company,
    sample_contacts
):
    """Test getting conversation context"""
    contact = sample_contacts[0]
    
    # Create conversation
    await conversation_repo.create_conversation(
        contact.id,
        sample_company.id,
        qualification_tier='hot'
    )
    
    # Get context
    context = await company_graph.get_conversation_context(contact.id)
    
    assert context['contact']['id'] == contact.id
    assert 'company' in context
    assert 'conversations' in context
    assert context['conversations']['total'] >= 1


@pytest.mark.asyncio
async def test_get_account_health_score(
    company_graph,
    conversation_repo,
    sample_company,
    sample_contacts
):
    """Test calculating account health score"""
    # Create some conversations
    for contact in sample_contacts:
        await conversation_repo.create_conversation(
            contact.id,
            sample_company.id
        )
    
    # Get health score
    health = await company_graph.get_account_health_score(sample_company.id)
    
    assert 'total_score' in health
    assert 'breakdown' in health
    assert 'health_status' in health
    assert 'recommendations' in health
    assert 0 <= health['total_score'] <= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
