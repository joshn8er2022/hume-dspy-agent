# ABM Integration Guide

## Overview

This guide documents the integration of the AccountOrchestrator with InboundAgent and FollowUpAgent to enable multi-contact Account-Based Marketing (ABM) campaigns.

## Architecture

```
┌─────────────────┐
│  Typeform Lead  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         InboundAgent                    │
│  - Qualifies lead (6-tier system)      │
│  - Generates email/SMS templates       │
│  - Saves to Agent Zero memory          │
│  - **NEW: Initiates ABM campaign**     │
└────────┬────────────────────────────────┘
         │
         │ (if HOT/SCORCHING/WARM)
         ▼
┌─────────────────────────────────────────┐
│      AccountOrchestrator                │
│  - Creates account record               │
│  - Researches company & colleagues      │
│  - Builds relationship graph            │
│  - Plans multi-contact campaign         │
│  - Tracks touchpoints & responses       │
└────────┬────────────────────────────────┘
         │
         │ (campaign steps)
         ▼
┌─────────────────────────────────────────┐
│       FollowUpAgent                     │
│  - Sends initial email to primary      │
│  - Monitors for responses               │
│  - **NEW: Executes campaign steps**    │
│  - **NEW: Contacts colleagues if no    │
│    response from primary**              │
│  - Updates Slack with progress          │
└─────────────────────────────────────────┘
```

## Integration Points

### 1. InboundAgent Integration

**File**: `agents/inbound_agent.py`

**Changes**:
- Added `AccountOrchestrator` import and initialization
- Added ABM campaign initiation after lead qualification
- Campaign only initiated for qualified leads (HOT, SCORCHING, WARM tiers)
- Graceful degradation if ABM fails (non-critical)

**Code Flow**:
```python
# In InboundAgent.forward()
if is_qualified and tier in [LeadTier.SCORCHING, LeadTier.HOT, LeadTier.WARM]:
    campaign_data = {
        'company_name': lead.get_field('company'),
        'contact_name': f"{first_name} {last_name}",
        'contact_email': lead.email,
        'inquiry_topic': lead.get_field('ai_summary'),
        'qualification_tier': tier.value,
        # ... more fields
    }
    
    campaign_result = asyncio.run(
        self.orchestrator.process_new_lead(campaign_data)
    )
    
    result.campaign_id = campaign_result.get('campaign_id')
```

### 2. FollowUpAgent Integration

**File**: `agents/follow_up_agent.py`

**Changes**:
- Added `AccountOrchestrator` and `CompanyGraph` imports
- Added initialization of orchestrator and graph
- Enhanced `send_follow_up()` to check for active ABM campaigns
- Executes next campaign step (may contact colleagues)

**Code Flow**:
```python
# In FollowUpAgent.send_follow_up()
campaign_context = asyncio.run(
    self.company_graph.get_conversation_context(state['lead_id'])
)

if campaign_context and campaign_context.get('campaign_id'):
    campaign_result = asyncio.run(
        self.orchestrator.execute_campaign_step(
            campaign_context['campaign_id']
        )
    )
    
    if campaign_result.get('colleague_contacted'):
        logger.info(f"👥 ABM: Contacted colleague for {state['email']}")
```

### 3. QualificationResult Model

**File**: `models/qualification.py`

**Changes**:
- Added `campaign_id: Optional[str]` field to track ABM campaigns
- Field is populated when ABM campaign is initiated

## Multi-Contact Campaign Flow

### Scenario: "Sue, your colleague Dr. XYZ inquired..."

1. **Day 0**: Dr. XYZ submits form
   - InboundAgent qualifies as HOT
   - AccountOrchestrator initiates campaign
   - Research finds colleague Sue Smith
   - Email sent to Dr. XYZ

2. **Day 2**: No response from Dr. XYZ
   - FollowUpAgent checks campaign status
   - AccountOrchestrator executes next step
   - Email sent to Sue: "Your colleague Dr. XYZ recently inquired about..."

3. **Day 3**: Sue responds
   - Campaign marked as won
   - Both contacts tracked in account graph

## Data Flow

### Lead → Account → Campaign

```
Lead Data (Typeform)
  ↓
Qualification (InboundAgent)
  ↓
Account Creation (AccountOrchestrator)
  ├─ Company record
  ├─ Primary contact
  └─ Research colleagues
      ↓
Campaign Planning
  ├─ Touchpoint sequence
  ├─ Channel selection (email → SMS → call)
  └─ Multi-contact strategy
      ↓
Execution (FollowUpAgent)
  ├─ Send to primary
  ├─ Monitor response
  └─ Escalate to colleagues if needed
```

## Configuration

### Environment Variables

Required for ABM functionality:
```bash
# Supabase (for account/campaign storage)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Research APIs (for finding colleagues)
APOLLO_API_KEY=your_apollo_key  # Optional
CLEARBIT_API_KEY=your_clearbit_key  # Optional

# Email/SMS (for touchpoints)
GMASS_API_KEY=your_gmass_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

### Feature Flags

ABM is automatically enabled for qualified leads (HOT/SCORCHING/WARM).

To disable ABM for specific tiers, modify `InboundAgent.forward()`:
```python
# Only enable for SCORCHING leads
if tier == LeadTier.SCORCHING:
    # initiate ABM
```

## Error Handling

### Graceful Degradation

All ABM operations use graceful degradation:

1. **Research Failure**: Campaign continues with primary contact only
2. **Database Failure**: Logged but doesn't block lead qualification
3. **Email Failure**: Falls back to SMS or logs error

### Monitoring

Key log messages:
- `🎯 ABM Campaign initiated: {campaign_id}` - Campaign started
- `👥 ABM: Contacted colleague for {email}` - Colleague contacted
- `⚠️ ABM campaign initiation failed` - Non-critical error

## Testing

### Unit Tests

Run integration tests:
```bash
pytest tests/test_e2e_abm.py -v
```

### Manual Testing

1. Submit test lead via Typeform
2. Check logs for campaign initiation
3. Verify campaign in Supabase
4. Simulate no response (wait or manually update)
5. Verify colleague contact

## Troubleshooting

### Campaign Not Initiated

**Symptom**: No `🎯 ABM Campaign initiated` log message

**Causes**:
1. Lead tier not HOT/SCORCHING/WARM
2. ABM initialization failed (check logs)
3. Missing environment variables

**Solution**: Check qualification tier and environment variables

### Colleague Not Contacted

**Symptom**: Only primary contact receives emails

**Causes**:
1. Research API failed to find colleagues
2. Campaign step not executed
3. Primary contact responded before colleague step

**Solution**: Check research logs and campaign status

### Database Errors

**Symptom**: `ValueError: SUPABASE_URL and SUPABASE_KEY must be set`

**Solution**: Set required environment variables in Railway/production

## Performance Considerations

### Research API Calls

- Cached for 24 hours per company
- Rate limited to avoid API quota issues
- Async execution doesn't block lead qualification

### Database Queries

- Indexed on company_name, email, campaign_id
- Batch operations for multiple contacts
- Connection pooling enabled

## Security

### Data Privacy

- All contact data encrypted at rest (Supabase)
- API keys stored in environment variables
- No PII in logs

### Access Control

- Campaign data scoped to organization
- Row-level security in Supabase
- API authentication required

## Next Steps

1. **Phoenix Monitoring**: Add tracing for ABM operations
2. **Analytics Dashboard**: Track campaign performance
3. **A/B Testing**: Test different messaging strategies
4. **Channel Optimization**: Analyze best channels per tier

## Support

For issues or questions:
1. Check logs for error messages
2. Review this guide
3. Contact development team

