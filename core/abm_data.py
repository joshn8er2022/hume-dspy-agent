"""
ABM Data Access Layer

Provides repository classes for all ABM database operations:
- CompanyRepository: Company/account management
- ContactRepository: Contact management and discovery
- RelationshipRepository: Relationship mapping
- ConversationRepository: Conversation tracking
- TouchpointRepository: Communication event tracking
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
import os
from supabase import create_client, Client


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Company:
    """Company/Account data model"""
    id: str
    name: str
    domain: str
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    headquarters_location: Optional[str] = None
    country: Optional[str] = None
    research_data: Dict[str, Any] = None
    account_tier: Optional[str] = None
    account_status: str = 'prospecting'
    total_contacts: int = 0
    active_conversations: int = 0
    last_researched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.research_data is None:
            self.research_data = {}


@dataclass
class Contact:
    """Contact data model"""
    id: str
    company_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    title: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    seniority_level: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    personal_website: Optional[str] = None
    interests: List[str] = None
    communication_preferences: Dict[str, Any] = None
    research_data: Dict[str, Any] = None
    engagement_score: int = 0
    last_engaged_at: Optional[datetime] = None
    total_touchpoints: int = 0
    status: str = 'active'
    is_primary_contact: bool = False
    is_decision_maker: bool = False
    is_champion: bool = False
    last_researched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.interests is None:
            self.interests = []
        if self.communication_preferences is None:
            self.communication_preferences = {}
        if self.research_data is None:
            self.research_data = {}

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class Relationship:
    """Relationship data model"""
    id: str
    contact_id_1: str
    contact_id_2: str
    relationship_type: str
    strength: str = 'medium'
    context: Optional[str] = None
    metadata: Dict[str, Any] = None
    is_verified: bool = False
    confidence_score: float = 0.5
    discovered_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Conversation:
    """Conversation data model"""
    id: str
    contact_id: str
    company_id: str
    status: str = 'active'
    qualification_tier: Optional[str] = None
    last_touchpoint_at: Optional[datetime] = None
    next_touchpoint_at: Optional[datetime] = None
    touchpoint_count: int = 0
    last_response_at: Optional[datetime] = None
    response_count: int = 0
    avg_response_time_hours: Optional[float] = None
    context: Dict[str, Any] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    sequence_step: int = 0
    outcome: Optional[str] = None
    outcome_date: Optional[datetime] = None
    outcome_notes: Optional[str] = None
    estimated_value: Optional[float] = None
    actual_value: Optional[float] = None
    metadata: Dict[str, Any] = None
    started_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Touchpoint:
    """Touchpoint data model"""
    id: str
    conversation_id: str
    channel: str
    direction: str
    subject: Optional[str] = None
    content: Optional[str] = None
    response: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    outcome: Optional[str] = None
    outcome_details: Optional[str] = None
    call_duration_seconds: Optional[int] = None
    call_recording_url: Optional[str] = None
    call_transcript: Optional[str] = None
    call_sentiment: Optional[str] = None
    email_thread_id: Optional[str] = None
    email_message_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_by_user_id: Optional[str] = None
    created_by_automation: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ============================================================================
# SUPABASE CLIENT
# ============================================================================

class SupabaseClient:
    """Singleton Supabase client"""
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client"""
        if cls._instance is None:
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_KEY')
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
            cls._instance = create_client(url, key)
        return cls._instance


# ============================================================================
# COMPANY REPOSITORY
# ============================================================================

class CompanyRepository:
    """Repository for company/account operations"""

    def __init__(self):
        self.client = SupabaseClient.get_client()

    async def create_company(self, data: Dict[str, Any]) -> Company:
        """Create a new company"""
        result = self.client.table('companies').insert(data).execute()
        return Company(**result.data[0])

    async def get_company_by_id(self, company_id: str) -> Optional[Company]:
        """Get company by ID"""
        result = self.client.table('companies').select('*').eq('id', company_id).execute()
        if result.data:
            return Company(**result.data[0])
        return None

    async def get_company_by_domain(self, domain: str) -> Optional[Company]:
        """Get company by domain"""
        result = self.client.table('companies').select('*').eq('domain', domain).execute()
        if result.data:
            return Company(**result.data[0])
        return None

    async def update_company(self, company_id: str, data: Dict[str, Any]) -> Company:
        """Update company"""
        result = self.client.table('companies').update(data).eq('id', company_id).execute()
        return Company(**result.data[0])

    async def list_companies(
        self,
        account_tier: Optional[str] = None,
        account_status: Optional[str] = None,
        limit: int = 100
    ) -> List[Company]:
        """List companies with optional filters"""
        query = self.client.table('companies').select('*')
        
        if account_tier:
            query = query.eq('account_tier', account_tier)
        if account_status:
            query = query.eq('account_status', account_status)
        
        result = query.limit(limit).execute()
        return [Company(**row) for row in result.data]

    async def search_companies(self, search_term: str, limit: int = 20) -> List[Company]:
        """Search companies by name or domain"""
        result = self.client.table('companies').select('*').or_(
            f'name.ilike.%{search_term}%,domain.ilike.%{search_term}%'
        ).limit(limit).execute()
        return [Company(**row) for row in result.data]


# ============================================================================
# CONTACT REPOSITORY
# ============================================================================

class ContactRepository:
    """Repository for contact operations"""

    def __init__(self):
        self.client = SupabaseClient.get_client()

    async def create_contact(self, data: Dict[str, Any]) -> Contact:
        """Create a new contact"""
        result = self.client.table('contacts').insert(data).execute()
        return Contact(**result.data[0])

    async def get_contact_by_id(self, contact_id: str) -> Optional[Contact]:
        """Get contact by ID"""
        result = self.client.table('contacts').select('*').eq('id', contact_id).execute()
        if result.data:
            return Contact(**result.data[0])
        return None

    async def get_contact_by_email(self, email: str) -> Optional[Contact]:
        """Get contact by email"""
        result = self.client.table('contacts').select('*').eq('email', email).execute()
        if result.data:
            return Contact(**result.data[0])
        return None

    async def find_contacts_by_company(
        self,
        company_id: str,
        status: str = 'active'
    ) -> List[Contact]:
        """Find all contacts for a company"""
        query = self.client.table('contacts').select('*').eq('company_id', company_id)
        
        if status:
            query = query.eq('status', status)
        
        result = query.execute()
        return [Contact(**row) for row in result.data]

    async def find_contacts_by_role(
        self,
        company_id: str,
        roles: List[str]
    ) -> List[Contact]:
        """Find contacts by role within a company"""
        result = self.client.table('contacts').select('*').eq(
            'company_id', company_id
        ).in_('role', roles).execute()
        return [Contact(**row) for row in result.data]

    async def find_decision_makers(self, company_id: str) -> List[Contact]:
        """Find decision makers within a company"""
        result = self.client.table('contacts').select('*').eq(
            'company_id', company_id
        ).eq('is_decision_maker', True).execute()
        return [Contact(**row) for row in result.data]

    async def find_primary_contact(self, company_id: str) -> Optional[Contact]:
        """Find primary contact for a company"""
        result = self.client.table('contacts').select('*').eq(
            'company_id', company_id
        ).eq('is_primary_contact', True).limit(1).execute()
        if result.data:
            return Contact(**result.data[0])
        return None

    async def update_contact(self, contact_id: str, data: Dict[str, Any]) -> Contact:
        """Update contact"""
        result = self.client.table('contacts').update(data).eq('id', contact_id).execute()
        return Contact(**result.data[0])

    async def search_contacts(self, search_term: str, limit: int = 20) -> List[Contact]:
        """Search contacts by name or email"""
        result = self.client.table('contacts').select('*').or_(
            f'first_name.ilike.%{search_term}%,last_name.ilike.%{search_term}%,email.ilike.%{search_term}%'
        ).limit(limit).execute()
        return [Contact(**row) for row in result.data]



# ============================================================================
# RELATIONSHIP REPOSITORY
# ============================================================================

class RelationshipRepository:
    """Repository for relationship operations"""

    def __init__(self):
        self.client = SupabaseClient.get_client()

    async def create_relationship(
        self,
        contact1_id: str,
        contact2_id: str,
        relationship_type: str,
        strength: str = 'medium',
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Relationship:
        """Create a new relationship between contacts"""
        data = {
            'contact_id_1': contact1_id,
            'contact_id_2': contact2_id,
            'relationship_type': relationship_type,
            'strength': strength,
            'context': context,
            'metadata': metadata or {}
        }
        result = self.client.table('relationships').insert(data).execute()
        return Relationship(**result.data[0])

    async def get_relationship(
        self,
        contact1_id: str,
        contact2_id: str
    ) -> Optional[Relationship]:
        """Get relationship between two contacts (bidirectional)"""
        result = self.client.table('relationships').select('*').or_(
            f'and(contact_id_1.eq.{contact1_id},contact_id_2.eq.{contact2_id}),'
            f'and(contact_id_1.eq.{contact2_id},contact_id_2.eq.{contact1_id})'
        ).execute()
        if result.data:
            return Relationship(**result.data[0])
        return None

    async def get_contact_relationships(self, contact_id: str) -> List[Relationship]:
        """Get all relationships for a contact"""
        result = self.client.table('relationships').select('*').or_(
            f'contact_id_1.eq.{contact_id},contact_id_2.eq.{contact_id}'
        ).execute()
        return [Relationship(**row) for row in result.data]

    async def get_colleagues(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get colleagues of a contact using database function"""
        result = self.client.rpc('get_colleagues', {'p_contact_id': contact_id}).execute()
        return result.data

    async def check_relationship(
        self,
        contact1_id: str,
        contact2_id: str
    ) -> Optional[Relationship]:
        """Check if relationship exists between two contacts"""
        return await self.get_relationship(contact1_id, contact2_id)

    async def update_relationship(
        self,
        relationship_id: str,
        data: Dict[str, Any]
    ) -> Relationship:
        """Update relationship"""
        result = self.client.table('relationships').update(data).eq(
            'id', relationship_id
        ).execute()
        return Relationship(**result.data[0])

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete relationship"""
        self.client.table('relationships').delete().eq('id', relationship_id).execute()
        return True


# ============================================================================
# CONVERSATION REPOSITORY
# ============================================================================

class ConversationRepository:
    """Repository for conversation operations"""

    def __init__(self):
        self.client = SupabaseClient.get_client()

    async def create_conversation(
        self,
        contact_id: str,
        company_id: str,
        status: str = 'active',
        qualification_tier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Create a new conversation"""
        data = {
            'contact_id': contact_id,
            'company_id': company_id,
            'status': status,
            'qualification_tier': qualification_tier,
            'metadata': metadata or {}
        }
        result = self.client.table('conversations').insert(data).execute()
        return Conversation(**result.data[0])

    async def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        result = self.client.table('conversations').select('*').eq(
            'id', conversation_id
        ).execute()
        if result.data:
            return Conversation(**result.data[0])
        return None

    async def get_active_conversations(
        self,
        company_id: str
    ) -> List[Dict[str, Any]]:
        """Get active conversations for a company using database function"""
        result = self.client.rpc(
            'get_active_conversations',
            {'p_company_id': company_id}
        ).execute()
        return result.data

    async def get_conversations_by_contact(
        self,
        contact_id: str,
        status: Optional[str] = None
    ) -> List[Conversation]:
        """Get conversations for a contact"""
        query = self.client.table('conversations').select('*').eq(
            'contact_id', contact_id
        )
        
        if status:
            query = query.eq('status', status)
        
        result = query.execute()
        return [Conversation(**row) for row in result.data]

    async def get_conversations_by_company(
        self,
        company_id: str,
        status: Optional[str] = None
    ) -> List[Conversation]:
        """Get conversations for a company"""
        query = self.client.table('conversations').select('*').eq(
            'company_id', company_id
        )
        
        if status:
            query = query.eq('status', status)
        
        result = query.execute()
        return [Conversation(**row) for row in result.data]

    async def get_conversations_needing_followup(self) -> List[Dict[str, Any]]:
        """Get conversations needing follow-up using database function"""
        result = self.client.rpc('get_conversations_needing_followup').execute()
        return result.data

    async def update_conversation_status(
        self,
        conversation_id: str,
        status: str,
        outcome: Optional[str] = None,
        outcome_notes: Optional[str] = None
    ) -> Conversation:
        """Update conversation status"""
        data = {'status': status}
        if outcome:
            data['outcome'] = outcome
            data['outcome_date'] = datetime.utcnow().isoformat()
        if outcome_notes:
            data['outcome_notes'] = outcome_notes
        
        result = self.client.table('conversations').update(data).eq(
            'id', conversation_id
        ).execute()
        return Conversation(**result.data[0])

    async def update_conversation(
        self,
        conversation_id: str,
        data: Dict[str, Any]
    ) -> Conversation:
        """Update conversation"""
        result = self.client.table('conversations').update(data).eq(
            'id', conversation_id
        ).execute()
        return Conversation(**result.data[0])

    async def update_conversation_context(
        self,
        conversation_id: str,
        context_updates: Dict[str, Any]
    ) -> Conversation:
        """Update conversation context (merge with existing)"""
        # Get current conversation
        conv = await self.get_conversation_by_id(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Merge context
        current_context = conv.context or {}
        updated_context = {**current_context, **context_updates}
        
        # Update
        return await self.update_conversation(
            conversation_id,
            {'context': updated_context}
        )


# ============================================================================
# TOUCHPOINT REPOSITORY
# ============================================================================

class TouchpointRepository:
    """Repository for touchpoint operations"""

    def __init__(self):
        self.client = SupabaseClient.get_client()

    async def create_touchpoint(
        self,
        conversation_id: str,
        channel: str,
        direction: str,
        data: Dict[str, Any]
    ) -> Touchpoint:
        """Create a new touchpoint"""
        touchpoint_data = {
            'conversation_id': conversation_id,
            'channel': channel,
            'direction': direction,
            **data
        }
        result = self.client.table('touchpoints').insert(touchpoint_data).execute()
        return Touchpoint(**result.data[0])

    async def get_touchpoint_by_id(self, touchpoint_id: str) -> Optional[Touchpoint]:
        """Get touchpoint by ID"""
        result = self.client.table('touchpoints').select('*').eq(
            'id', touchpoint_id
        ).execute()
        if result.data:
            return Touchpoint(**result.data[0])
        return None

    async def get_touchpoints(
        self,
        conversation_id: str,
        limit: int = 100
    ) -> List[Touchpoint]:
        """Get touchpoints for a conversation"""
        result = self.client.table('touchpoints').select('*').eq(
            'conversation_id', conversation_id
        ).order('created_at', desc=True).limit(limit).execute()
        return [Touchpoint(**row) for row in result.data]

    async def get_touchpoint_history(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Get touchpoint history using database function"""
        result = self.client.rpc(
            'get_touchpoint_history',
            {'p_conversation_id': conversation_id}
        ).execute()
        return result.data

    async def get_engagement_metrics(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Get engagement metrics using database function"""
        result = self.client.rpc(
            'get_conversation_engagement_metrics',
            {'p_conversation_id': conversation_id}
        ).execute()
        if result.data:
            return result.data[0]
        return {}

    async def update_touchpoint(
        self,
        touchpoint_id: str,
        data: Dict[str, Any]
    ) -> Touchpoint:
        """Update touchpoint"""
        result = self.client.table('touchpoints').update(data).eq(
            'id', touchpoint_id
        ).execute()
        return Touchpoint(**result.data[0])

    async def record_email_sent(
        self,
        conversation_id: str,
        subject: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Touchpoint:
        """Record an outbound email touchpoint"""
        return await self.create_touchpoint(
            conversation_id=conversation_id,
            channel='email',
            direction='outbound',
            data={
                'subject': subject,
                'content': content,
                'sent_at': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }
        )

    async def record_email_opened(
        self,
        touchpoint_id: str
    ) -> Touchpoint:
        """Record email opened event"""
        return await self.update_touchpoint(
            touchpoint_id,
            {'opened_at': datetime.utcnow().isoformat()}
        )

    async def record_email_clicked(
        self,
        touchpoint_id: str
    ) -> Touchpoint:
        """Record email clicked event"""
        return await self.update_touchpoint(
            touchpoint_id,
            {'clicked_at': datetime.utcnow().isoformat()}
        )

    async def record_email_replied(
        self,
        touchpoint_id: str,
        response: str
    ) -> Touchpoint:
        """Record email reply event"""
        return await self.update_touchpoint(
            touchpoint_id,
            {
                'replied_at': datetime.utcnow().isoformat(),
                'response': response
            }
        )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'Company',
    'Contact',
    'Relationship',
    'Conversation',
    'Touchpoint',
    'CompanyRepository',
    'ContactRepository',
    'RelationshipRepository',
    'ConversationRepository',
    'TouchpointRepository',
    'SupabaseClient'
]
