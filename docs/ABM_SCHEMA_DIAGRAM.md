# ABM Database Schema Diagram

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            COMPANIES                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ PK  id                    UUID                                          │
│     name                  TEXT                                          │
│ UK  domain                TEXT                                          │
│     industry              TEXT                                          │
│     size                  TEXT                                          │
│     research_data         JSONB    ← Research Agent cache              │
│     account_tier          TEXT     (strategic, tier1, tier2, tier3)    │
│     account_status        TEXT     (prospecting, engaged, customer)    │
│     total_contacts        INTEGER  ← Auto-updated by trigger           │
│     active_conversations  INTEGER  ← Auto-updated by trigger           │
│     created_at            TIMESTAMPTZ                                   │
│     updated_at            TIMESTAMPTZ                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            CONTACTS                                      │
├─────────────────────────────────────────────────────────────────────────┤
│ PK  id                    UUID                                          │
│ FK  company_id            UUID    → companies.id (CASCADE)             │
│     first_name            TEXT                                          │
│     last_name             TEXT                                          │
│ UK  email                 TEXT                                          │
│     title                 TEXT                                          │
│     role                  TEXT    (doctor, admin, executive, etc.)     │
│     seniority_level       TEXT    (c-level, vp, director, etc.)        │
│     interests             JSONB   ["topic1", "topic2", ...]            │
│     research_data         JSONB   ← Research Agent enrichment          │
│     engagement_score      INTEGER (0-100)                              │
│     is_primary_contact    BOOLEAN                                       │
│     is_decision_maker     BOOLEAN                                       │
│     total_touchpoints     INTEGER ← Auto-updated by trigger            │
│     last_engaged_at       TIMESTAMPTZ                                   │
│     created_at            TIMESTAMPTZ                                   │
└─────────────────────────────────────────────────────────────────────────┘
         │                                    │
         │ N:N                                │ 1:N
         ▼                                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────────────┐
│    RELATIONSHIPS         │    │         CONVERSATIONS                   │
├──────────────────────────┤    ├─────────────────────────────────────────┤
│ PK  id            UUID   │    │ PK  id                    UUID         │
│ FK  contact_id_1  UUID ──┼────┤ FK  contact_id            UUID         │
│ FK  contact_id_2  UUID ──┼────┤ FK  company_id            UUID         │
│     type          TEXT   │    │     status                TEXT         │
│     strength      TEXT   │    │     qualification_tier    TEXT         │
│     confidence    DECIMAL│    │     touchpoint_count      INTEGER      │
│     metadata      JSONB  │    │     context               JSONB        │
│     created_at    TSTZ   │    │     next_touchpoint_at    TIMESTAMPTZ  │
└──────────────────────────┘    │     created_at            TIMESTAMPTZ  │
                                └─────────────────────────────────────────┘
                                                │
                                                │ 1:N
                                                ▼
                                ┌─────────────────────────────────────────┐
                                │         TOUCHPOINTS                     │
                                ├─────────────────────────────────────────┤
                                │ PK  id                UUID              │
                                │ FK  conversation_id   UUID              │
                                │     channel           TEXT              │
                                │     direction         TEXT              │
                                │     content           TEXT              │
                                │     sent_at           TIMESTAMPTZ       │
                                │     opened_at         TIMESTAMPTZ       │
                                │     clicked_at        TIMESTAMPTZ       │
                                │     replied_at        TIMESTAMPTZ       │
                                │     outcome           TEXT              │
                                │     metadata          JSONB             │
                                │     created_at        TIMESTAMPTZ       │
                                └─────────────────────────────────────────┘
```

## Data Flow

### 1. Company Onboarding
```
1. Create COMPANY
   ↓
2. Add CONTACTS (auto-increments company.total_contacts)
   ↓
3. Map RELATIONSHIPS between contacts
   ↓
4. Research Agent enriches company.research_data and contacts.research_data
```

### 2. Conversation Lifecycle
```
1. Create CONVERSATION (auto-increments company.active_conversations)
   ↓
2. Send TOUCHPOINT (auto-increments conversation.touchpoint_count)
   ↓
3. Track engagement (opened_at, clicked_at, replied_at)
   ↓
4. Update conversation.context with insights
   ↓
5. Close conversation (auto-decrements company.active_conversations)
```

### 3. Multi-Contact Orchestration
```
1. Start conversation with PRIMARY CONTACT
   ↓
2. Query RELATIONSHIPS to find colleagues
   ↓
3. Use CompanyGraph.find_expansion_targets()
   ↓
4. Create conversations with expansion targets
   ↓
5. Reference primary contact in messaging:
   "Your colleague Dr. XYZ inquired about..."
```

## Trigger Chain

### Contact Creation
```
INSERT INTO contacts
  ↓
TRIGGER: contacts_count_trigger
  ↓
UPDATE companies.total_contacts += 1
```

### Touchpoint Creation
```
INSERT INTO touchpoints
  ↓
TRIGGER: touchpoints_update_conversation_trigger
  ↓
UPDATE conversations.touchpoint_count += 1
UPDATE conversations.last_touchpoint_at
UPDATE contacts.total_touchpoints += 1
UPDATE contacts.last_engaged_at
```

### Conversation Status Change
```
UPDATE conversations SET status = 'won'
  ↓
TRIGGER: conversations_closed_at_trigger
  ↓
SET conversations.closed_at = NOW()
  ↓
TRIGGER: conversations_count_trigger
  ↓
UPDATE companies.active_conversations -= 1
```

## Query Patterns

### Get Account Overview
```sql
SELECT * FROM account_overview WHERE company_id = ?;
```

### Find Expansion Targets
```sql
SELECT * FROM get_colleagues(?);
```

### Get Conversations Needing Follow-up
```sql
SELECT * FROM get_conversations_needing_followup();
```

### Get Engagement Metrics
```sql
SELECT * FROM get_conversation_engagement_metrics(?);
```

## Index Strategy

### Primary Indexes
- All foreign keys indexed
- Unique constraints on domain, email
- Composite indexes on common query patterns

### Performance Indexes
- GIN indexes on JSONB columns
- Partial indexes on filtered queries
- Full-text search using pg_trgm

### Analytics Indexes
- Time-based indexes for reporting
- Outcome tracking indexes
- Engagement metric indexes

## Scalability Considerations

### Current Capacity
- **Companies**: Millions of records
- **Contacts**: Tens of millions of records
- **Relationships**: Hundreds of millions of edges
- **Conversations**: Hundreds of millions of records
- **Touchpoints**: Billions of records (with partitioning)

### Future Optimizations
- Partition touchpoints by date (when volume > 10M)
- Archive closed conversations (when volume > 1M)
- Implement read replicas for analytics queries
- Add caching layer for frequently accessed accounts

