# ABM Data Model Documentation

## Overview

The Account-Based Marketing (ABM) Data Model provides a comprehensive database schema and data access layer for multi-contact orchestration, relationship mapping, and intelligent conversation tracking.

## Database Schema

### Entity Relationship Diagram

```
COMPANIES (1) ──────< (N) CONTACTS
    │                      │
    │                      │
    │                      ├──< (N) RELATIONSHIPS (N) >──┤
    │                      │                              │
    │                      │                              │
    └──────< (N) CONVERSATIONS (N) >────────────────────┘
                   │
                   │
                   └──────< (N) TOUCHPOINTS
```

### Tables

#### 1. Companies
Stores company/account data for ABM campaigns.

**Key Fields:**
- `id` (UUID): Primary key
- `name` (TEXT): Company name
- `domain` (TEXT): Unique domain identifier
- `industry` (TEXT): Industry classification
- `research_data` (JSONB): Cached research results
- `account_tier` (TEXT): Strategic importance (strategic, tier1, tier2, tier3)
- `account_status` (TEXT): Relationship status (prospecting, engaged, customer, churned)
- `total_contacts` (INTEGER): Auto-updated contact count
- `active_conversations` (INTEGER): Auto-updated active conversation count

**Indexes:**
- Domain, industry, account_tier, account_status
- GIN index on research_data for JSONB queries

#### 2. Contacts
Individual contacts within companies for multi-contact orchestration.

**Key Fields:**
- `id` (UUID): Primary key
- `company_id` (UUID): Foreign key to companies
- `first_name`, `last_name` (TEXT): Contact name
- `email` (TEXT): Unique email address
- `title`, `role`, `department` (TEXT): Professional information
- `seniority_level` (TEXT): c-level, vp, director, manager, individual_contributor
- `interests` (JSONB): Array of topics for personalization
- `research_data` (JSONB): Cached enrichment data
- `engagement_score` (INTEGER): 0-100 engagement level
- `is_primary_contact`, `is_decision_maker`, `is_champion` (BOOLEAN): Contact flags

**Indexes:**
- company_id, email, role, status
- Partial indexes on primary_contact, decision_maker
- GIN indexes on interests and research_data
- Composite index on (company_id, role)

**Triggers:**
- Auto-updates company.total_contacts on INSERT/DELETE

#### 3. Relationships
Maps relationships between contacts for context-aware messaging.

**Key Fields:**
- `id` (UUID): Primary key
- `contact_id_1`, `contact_id_2` (UUID): Contact pair
- `relationship_type` (TEXT): colleagues, reports_to, manager_of, etc.
- `strength` (TEXT): weak, medium, strong
- `confidence_score` (DECIMAL): AI confidence 0.0-1.0
- `metadata` (JSONB): Additional relationship context

**Constraints:**
- Unique constraint on (contact_id_1, contact_id_2)
- Check constraint preventing self-relationships
- Trigger preventing duplicate reverse relationships

**Helper Functions:**
- `get_contact_relationships(contact_id)`: Get all relationships (bidirectional)
- `get_colleagues(contact_id)`: Get colleagues within same company

#### 4. Conversations
Tracks conversation state and context for multi-touch campaigns.

**Key Fields:**
- `id` (UUID): Primary key
- `contact_id` (UUID): Foreign key to contacts
- `company_id` (UUID): Foreign key to companies
- `status` (TEXT): active, paused, closed, won, lost, nurturing
- `qualification_tier` (TEXT): scorching, hot, warm, cool, cold
- `touchpoint_count` (INTEGER): Auto-updated touchpoint count
- `context` (JSONB): Conversation context (topics, pain points, objections)
- `sequence_step` (INTEGER): Current step in automated sequence
- `estimated_value`, `actual_value` (DECIMAL): Value tracking

**Indexes:**
- contact_id, company_id, status, qualification_tier
- next_touchpoint_at for follow-up queries
- GIN indexes on context and metadata
- Composite indexes on (company_id, status) and (contact_id, status)

**Triggers:**
- Auto-updates company.active_conversations on status changes
- Auto-sets closed_at when status changes to closed/won/lost

**Helper Functions:**
- `get_active_conversations(company_id)`: Get active conversations for company
- `get_conversations_needing_followup()`: Get overdue conversations

#### 5. Touchpoints
Individual communication events within conversations.

**Key Fields:**
- `id` (UUID): Primary key
- `conversation_id` (UUID): Foreign key to conversations
- `channel` (TEXT): email, sms, call, linkedin, mail, whatsapp, meeting
- `direction` (TEXT): outbound, inbound
- `content`, `response` (TEXT): Message content
- `sent_at`, `delivered_at`, `opened_at`, `clicked_at`, `replied_at` (TIMESTAMPTZ): Engagement tracking
- `outcome` (TEXT): sent, delivered, opened, clicked, replied, bounced, failed
- `metadata` (JSONB): Template, campaign, tracking data

**Indexes:**
- conversation_id, channel, direction, outcome
- Temporal indexes on sent_at, replied_at
- GIN index on metadata
- Composite indexes on (conversation_id, channel) and (conversation_id, created_at)

**Triggers:**
- Auto-updates conversation.touchpoint_count and last_touchpoint_at
- Auto-updates contact.total_touchpoints and last_engaged_at
- Auto-sets outcome based on engagement events

**Helper Functions:**
- `get_touchpoint_history(conversation_id)`: Get chronological touchpoint history
- `get_conversation_engagement_metrics(conversation_id)`: Calculate open/click/reply rates

### Materialized Views

#### account_overview
Aggregated account metrics for fast dashboard queries.

**Fields:**
- Company information
- Contact counts (total, primary, decision makers)
- Conversation counts (total, active, won)
- Touchpoint counts and engagement metrics
- Relationship counts

**Refresh:** Call `refresh_account_overview()` function periodically (recommended: every 15-30 minutes)

## Data Access Layer

### Repository Classes

All repositories are located in `core/abm_data.py`:

#### CompanyRepository
```python
company_repo = CompanyRepository()

# Create company
company = await company_repo.create_company({
    'name': 'Acme Corp',
    'domain': 'acme.com',
    'industry': 'Technology'
})

# Get by domain
company = await company_repo.get_company_by_domain('acme.com')

# Update company
company = await company_repo.update_company(company_id, {
    'account_tier': 'strategic',
    'research_data': {...}
})

# Search companies
results = await company_repo.search_companies('medical')
```

#### ContactRepository
```python
contact_repo = ContactRepository()

# Create contact
contact = await contact_repo.create_contact({
    'company_id': company_id,
    'first_name': 'John',
    'last_name': 'Smith',
    'email': 'john@acme.com',
    'title': 'CTO',
    'is_decision_maker': True
})

# Get by email
contact = await contact_repo.get_contact_by_email('john@acme.com')

# Find contacts by company
contacts = await contact_repo.find_contacts_by_company(company_id)

# Find decision makers
decision_makers = await contact_repo.find_decision_makers(company_id)

# Find by role
doctors = await contact_repo.find_contacts_by_role(company_id, ['doctor'])
```

#### RelationshipRepository
```python
relationship_repo = RelationshipRepository()

# Create relationship
rel = await relationship_repo.create_relationship(
    contact1_id,
    contact2_id,
    'colleagues',
    strength='strong'
)

# Check if relationship exists
rel = await relationship_repo.check_relationship(contact1_id, contact2_id)

# Get all relationships for a contact
rels = await relationship_repo.get_contact_relationships(contact_id)

# Get colleagues
colleagues = await relationship_repo.get_colleagues(contact_id)
```

#### ConversationRepository
```python
conversation_repo = ConversationRepository()

# Create conversation
conv = await conversation_repo.create_conversation(
    contact_id,
    company_id,
    qualification_tier='hot'
)

# Get active conversations
active = await conversation_repo.get_active_conversations(company_id)

# Update status
conv = await conversation_repo.update_conversation_status(
    conversation_id,
    'won',
    outcome='meeting_scheduled'
)

# Update context
conv = await conversation_repo.update_conversation_context(
    conversation_id,
    {'topics_discussed': ['pricing', 'features']}
)

# Get conversations needing follow-up
overdue = await conversation_repo.get_conversations_needing_followup()
```

#### TouchpointRepository
```python
touchpoint_repo = TouchpointRepository()

# Record email sent
tp = await touchpoint_repo.record_email_sent(
    conversation_id,
    'Follow-up Email',
    'Thanks for your time...'
)

# Record engagement events
await touchpoint_repo.record_email_opened(touchpoint_id)
await touchpoint_repo.record_email_clicked(touchpoint_id)
await touchpoint_repo.record_email_replied(touchpoint_id, 'Response text')

# Get touchpoint history
history = await touchpoint_repo.get_touchpoint_history(conversation_id)

# Get engagement metrics
metrics = await touchpoint_repo.get_engagement_metrics(conversation_id)
# Returns: {open_rate, click_rate, reply_rate, emails_sent, etc.}
```

## Company Graph Module

High-level queries for ABM orchestration in `core/company_graph.py`:

### CompanyGraph

```python
from core.company_graph import CompanyGraph

graph = CompanyGraph()

# Get complete account overview
overview = await graph.get_account_overview(company_id)
# Returns: {
#   'company': {...},
#   'contacts': {...},
#   'relationships': [...],
#   'active_conversations': [...],
#   'summary': {...}
# }

# Find expansion targets (colleagues of engaged contacts)
targets = await graph.find_expansion_targets(
    primary_contact_id,
    min_relationship_strength='medium'
)
# Returns: [{
#   'contact': Contact,
#   'relationship_to_primary': {...},
#   'engagement_status': {...},
#   'priority_score': 85.5
# }]

# Get conversation context for personalized messaging
context = await graph.get_conversation_context(
    contact_id,
    include_company_context=True,
    include_relationship_context=True
)
# Returns: {
#   'contact': {...},
#   'company': {...},
#   'conversations': {...},
#   'engagement': {...},
#   'relationships': {...}
# }

# Calculate account health score
health = await graph.get_account_health_score(company_id)
# Returns: {
#   'total_score': 75.5,
#   'breakdown': {...},
#   'health_status': 'good',
#   'recommendations': [...]
# }
```

## Use Cases

### 1. Multi-Contact Orchestration

**Scenario:** "Sue, your colleague Dr. XYZ inquired about..."

```python
# Get primary contact's colleagues
targets = await graph.find_expansion_targets(primary_contact_id)

for target in targets:
    # Get context including colleague relationship
    context = await graph.get_conversation_context(target['contact'].id)
    
    # Create personalized message referencing colleague
    message = f"Dear {target['contact'].first_name}, your colleague "
    message += f"{context['relationships']['colleagues'][0]['name']} "
    message += f"recently inquired about our AI solutions..."
    
    # Create conversation and send touchpoint
    conv = await conversation_repo.create_conversation(
        target['contact'].id,
        target['contact'].company_id
    )
    await touchpoint_repo.record_email_sent(conv.id, subject, message)
```

### 2. Account Health Monitoring

```python
# Get all tier1 accounts
companies = await company_repo.list_companies(account_tier='tier1')

for company in companies:
    # Calculate health score
    health = await graph.get_account_health_score(company.id)
    
    if health['health_status'] in ['poor', 'critical']:
        print(f"⚠️  {company.name}: {health['total_score']}/100")
        print(f"   Recommendations: {health['recommendations']}")
```

### 3. Follow-up Automation

```python
# Get conversations needing follow-up
overdue = await conversation_repo.get_conversations_needing_followup()

for conv_data in overdue:
    # Get full context
    context = await graph.get_conversation_context(conv_data['contact_id'])
    
    # Generate personalized follow-up
    # ... (use context for personalization)
    
    # Send touchpoint
    await touchpoint_repo.record_email_sent(
        conv_data['conversation_id'],
        subject,
        content
    )
```

### 4. Engagement Analytics

```python
# Get engagement metrics for a conversation
metrics = await touchpoint_repo.get_engagement_metrics(conversation_id)

print(f"Open Rate: {metrics['open_rate']:.1f}%")
print(f"Click Rate: {metrics['click_rate']:.1f}%")
print(f"Reply Rate: {metrics['reply_rate']:.1f}%")
```

## Performance Considerations

### Indexes

- **GIN indexes** on JSONB columns for fast JSON queries
- **Partial indexes** on filtered queries (e.g., active conversations only)
- **Composite indexes** for common multi-column queries
- **Full-text search** using pg_trgm extension

### Materialized Views

- `account_overview`: Refresh every 15-30 minutes for dashboard queries
- Use `SELECT refresh_account_overview();` to update

### Query Optimization

- Use database functions for complex queries (get_colleagues, get_active_conversations)
- Leverage triggers for auto-updating counts (avoid manual COUNT queries)
- Use partial indexes for filtered queries

## Migration Files

All migrations are in `/migrations/`:

1. `004_create_companies_table.sql` - Companies table with indexes and triggers
2. `005_create_contacts_table.sql` - Contacts table with relationship to companies
3. `006_create_relationships_table.sql` - Relationships with bidirectional support
4. `007_create_conversations_table.sql` - Conversations with status tracking
5. `008_create_touchpoints_table.sql` - Touchpoints with engagement tracking
6. `009_create_indexes.sql` - Performance indexes and materialized views

## Testing

### Unit Tests

Run unit tests for all repositories:

```bash
pytest tests/test_abm_data.py -v
```

### Integration Tests

Run end-to-end integration test:

```bash
python tests/test_abm_integration.py
```

This tests:
- Complete data flow from company to touchpoint
- Foreign key constraints
- Trigger functionality
- Database functions
- Company graph queries

## Next Steps

### Phase 3: Account Orchestrator

Build the `AccountOrchestrator` class that uses this data model to:

1. **Multi-Contact Campaigns**: Coordinate outreach across multiple contacts
2. **Relationship-Aware Messaging**: Reference colleagues in personalized messages
3. **Intelligent Sequencing**: Adapt sequences based on engagement and relationships
4. **Context Preservation**: Maintain conversation context across touchpoints

### Integration with Research Agent

The ABM data model integrates with the Research Agent (`core/research.py`) to:

1. **Company Research**: Populate `companies.research_data`
2. **Contact Enrichment**: Populate `contacts.research_data`
3. **Relationship Discovery**: Identify relationships via LinkedIn, company websites
4. **Interest Mapping**: Discover contact interests for personalization

## API Reference

See inline documentation in:
- `core/abm_data.py` - Repository classes and data models
- `core/company_graph.py` - Company graph queries

## Database Functions Reference

### Relationship Functions
- `get_contact_relationships(contact_id UUID)` - Get all relationships for a contact
- `get_colleagues(contact_id UUID)` - Get colleagues within same company

### Conversation Functions
- `get_active_conversations(company_id UUID)` - Get active conversations for company
- `get_conversations_needing_followup()` - Get overdue conversations

### Touchpoint Functions
- `get_touchpoint_history(conversation_id UUID)` - Get chronological touchpoint history
- `get_conversation_engagement_metrics(conversation_id UUID)` - Calculate engagement rates

### Utility Functions
- `refresh_account_overview()` - Refresh materialized view

