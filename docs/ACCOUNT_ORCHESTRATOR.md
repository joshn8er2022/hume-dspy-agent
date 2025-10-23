# AccountOrchestrator Agent Documentation

## Overview

The **AccountOrchestrator** is an autonomous agent designed for sophisticated multi-contact Account-Based Marketing (ABM) campaigns. It orchestrates personalized outreach across multiple stakeholders within an account, featuring intelligent conflict detection, channel escalation, and colleague reference messaging.

## Table of Contents

1. [Architecture](#architecture)
2. [Key Features](#key-features)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Core Concepts](#core-concepts)
6. [API Reference](#api-reference)
7. [Workflow Integration](#workflow-integration)
8. [Configuration](#configuration)
9. [Testing](#testing)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                   AccountOrchestrator                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Campaign Management Layer                     │  │
│  │  - Multi-contact coordination                         │  │
│  │  - State management                                   │  │
│  │  - Conflict detection                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Decision Engine                               │  │
│  │  - Contact prioritization                             │  │
│  │  - Channel selection                                  │  │
│  │  - Message generation                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Execution Layer                               │  │
│  │  - Touchpoint execution                               │  │
│  │  - Scheduling                                         │  │
│  │  - Persistence                                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   LangGraph Workflow   │
              │  - State management    │
              │  - Conditional routing │
              │  - Error handling      │
              └────────────────────────┘
```

### Component Breakdown

#### 1. **AccountOrchestrator** (`agents/account_orchestrator.py`)
- Core orchestration logic
- Campaign lifecycle management
- Contact and channel selection
- Message generation

#### 2. **ABMCampaignWorkflow** (`workflows/abm_campaign.py`)
- LangGraph-based state machine
- Workflow nodes and routing
- Autonomous execution

#### 3. **Data Models**
- `CampaignChannel`: Email, SMS, Call, LinkedIn
- `CampaignStatus`: Active, Paused, Completed, Cancelled
- `ContactRole`: Primary, Secondary, Tertiary

---

## Key Features

### 1. Multi-Contact Coordination

**Capability**: Engage multiple stakeholders within a single account simultaneously.

**Benefits**:
- Reach decision-makers at different levels
- Increase account penetration
- Accelerate deal velocity

**Example**:
```python
lead_data = {
    "account_id": "acc_123",
    "email": "cto@company.com",
    "name": "CTO Name",
    "account_contacts": [
        {"email": "vp@company.com", "title": "VP Engineering"},
        {"email": "director@company.com", "title": "Director Product"}
    ]
}
```

### 2. Colleague Reference Messaging

**Capability**: Generate contextual messages referencing previous engagement.

**Pattern**: "Sue, your colleague Dr. XYZ inquired about..."

**Implementation**:
```python
message = await orchestrator.generate_colleague_message(
    campaign,
    target_contact,
    referring_contact
)
```

**Output Example**:
```
Hi Sue,

I noticed Dr. John Smith (CTO) recently inquired about our AI automation 
platform. Given your role at Acme Corp, I thought you might also find 
this relevant.

...
```

### 3. Channel Escalation

**Capability**: Automatically escalate through communication channels based on engagement.

**Escalation Path**:
1. **Email** (Attempts 1-2): Initial outreach
2. **SMS** (Attempts 3-4): Follow-up for non-responders
3. **Call** (Attempts 5+): Direct engagement

**Logic**:
```python
channel = orchestrator.select_channel(campaign, contact)
# Returns: CampaignChannel.EMAIL → SMS → CALL
```

### 4. Conflict Detection

**Capability**: Prevent messaging conflicts when primary contact responds.

**Detected Conflicts**:
- Primary contact responded
- Meeting scheduled
- Unsubscribe request
- Negative sentiment

**Auto-Pause**: Campaign automatically pauses when conflict detected.

```python
conflict = await orchestrator.check_conflicts(campaign_id)
if conflict["has_conflict"]:
    # Campaign paused automatically
    print(f"Paused: {conflict['conflicts'][0]['type']}")
```

### 5. Autonomous Scheduling

**Capability**: Self-scheduling of touchpoints based on configurable intervals.

**Default Intervals**: [2, 3, 5, 7, 10, 14] days

**Customizable**:
```python
config = {
    "touchpoint_intervals": [1, 2, 3, 5, 7, 10, 14, 21]
}
orchestrator = AccountOrchestrator(config=config)
```

---

## Installation

### Prerequisites

```bash
Python 3.9+
Supabase (optional, for persistence)
LangGraph (optional, for workflow)
```

### Setup

```bash
# Clone repository
git clone <repository-url>
cd hume-dspy-agent

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from agents.account_orchestrator import AccountOrchestrator; print('OK')"
```

---

## Quick Start

### Basic Campaign

```python
import asyncio
from agents.account_orchestrator import AccountOrchestrator

async def launch_campaign():
    # Initialize orchestrator
    orchestrator = AccountOrchestrator()
    
    # Define lead
    lead_data = {
        "account_id": "acc_001",
        "email": "contact@example.com",
        "name": "John Doe",
        "title": "CTO",
        "metadata": {
            "company_name": "Example Corp"
        }
    }
    
    # Launch campaign
    result = await orchestrator.process_new_lead(lead_data)
    print(f"Campaign ID: {result['campaign_id']}")
    
    # Execute first step
    step_result = await orchestrator.execute_campaign_step(
        result['campaign_id']
    )
    print(f"Step executed: {step_result}")

asyncio.run(launch_campaign())
```

### Multi-Contact Campaign

```python
lead_data = {
    "account_id": "acc_002",
    "email": "primary@example.com",
    "name": "Primary Contact",
    "account_contacts": [
        {
            "email": "secondary@example.com",
            "name": "Secondary Contact",
            "title": "VP Sales"
        },
        {
            "email": "tertiary@example.com",
            "name": "Tertiary Contact",
            "title": "Director"
        }
    ]
}

result = await orchestrator.process_new_lead(lead_data)
print(f"Contacts: {result['contacts_count']}")
```

---

## Core Concepts

### Campaign Lifecycle

```
┌──────────────┐
│  Initialize  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Active    │◄─────┐
└──────┬───────┘      │
       │              │
       ▼              │
┌──────────────┐      │
│   Execute    │──────┘
│  Touchpoint  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Evaluate   │
└──────┬───────┘
       │
       ├─────► Paused (conflict detected)
       │
       └─────► Completed (max touchpoints)
```

### Contact Prioritization

**Scoring Algorithm**:

```python
title_scores = {
    "ceo": 100,
    "cto": 95,
    "cio": 95,
    "vp": 80,
    "director": 70,
    "manager": 50
}
```

**Priority Order**:
1. C-level executives (CEO, CTO, CIO)
2. Vice Presidents
3. Directors
4. Managers
5. Individual contributors

### Channel Selection Logic

```python
def select_channel(campaign, contact):
    attempts_per_channel = count_attempts(campaign, contact)
    
    for channel in [EMAIL, SMS, CALL]:
        if attempts_per_channel[channel] < 2:
            if contact_has_channel(contact, channel):
                return channel
    
    return EMAIL  # Default fallback
```

---

## API Reference

### AccountOrchestrator

#### Constructor

```python
AccountOrchestrator(
    supabase_client=None,
    config: Optional[Dict] = None
)
```

**Parameters**:
- `supabase_client`: Supabase client for persistence (optional)
- `config`: Configuration dictionary (optional)

**Returns**: AccountOrchestrator instance

---

#### process_new_lead()

```python
async def process_new_lead(lead_data: Dict) -> Dict
```

**Purpose**: Initiate ABM campaign for new lead/account.

**Parameters**:
- `lead_data`: Lead information including contacts
  - `account_id` (required): Account identifier
  - `email` (required): Primary contact email
  - `name`: Contact name
  - `phone`: Contact phone
  - `title`: Contact title
  - `account_contacts`: List of additional contacts
  - `metadata`: Additional account data

**Returns**:
```python
{
    "success": True,
    "campaign_id": "camp_...",
    "contacts_count": 3,
    "first_touchpoint": {...}
}
```

**Example**:
```python
result = await orchestrator.process_new_lead({
    "account_id": "acc_123",
    "email": "contact@example.com",
    "name": "John Doe"
})
```

---

#### execute_campaign_step()

```python
async def execute_campaign_step(campaign_id: str) -> Dict
```

**Purpose**: Execute next step in campaign workflow.

**Parameters**:
- `campaign_id`: Campaign identifier

**Returns**:
```python
{
    "success": True,
    "campaign_id": "camp_...",
    "step": 2,
    "contact": "John Doe",
    "channel": "email",
    "next_touchpoint": {...}
}
```

---

#### generate_colleague_message()

```python
async def generate_colleague_message(
    campaign: Dict,
    target_contact: Dict,
    referring_contact: Dict
) -> str
```

**Purpose**: Generate colleague reference message.

**Parameters**:
- `campaign`: Campaign data
- `target_contact`: Contact receiving message
- `referring_contact`: Contact who previously engaged

**Returns**: Personalized message string

---

#### check_conflicts()

```python
async def check_conflicts(campaign_id: str) -> Dict
```

**Purpose**: Check for conflicts that should pause campaign.

**Returns**:
```python
{
    "has_conflict": True,
    "conflicts": [
        {
            "type": "primary_responded",
            "contact": "John Doe",
            "timestamp": "2024-10-23T10:00:00"
        }
    ],
    "should_pause": True
}
```

---

#### select_channel()

```python
def select_channel(
    campaign: Dict,
    contact: Dict
) -> CampaignChannel
```

**Purpose**: Select communication channel based on escalation logic.

**Returns**: CampaignChannel enum (EMAIL, SMS, CALL, LINKEDIN)

---

#### schedule_next_touchpoint()

```python
async def schedule_next_touchpoint(
    campaign_id: str,
    immediate: bool = False
) -> Optional[Dict]
```

**Purpose**: Schedule next touchpoint with autonomous trigger logic.

**Parameters**:
- `campaign_id`: Campaign identifier
- `immediate`: Execute immediately vs scheduled

**Returns**: Scheduled touchpoint details

---

#### get_campaign_status()

```python
def get_campaign_status(campaign_id: str) -> Optional[Dict]
```

**Purpose**: Get current campaign status and metrics.

**Returns**:
```python
{
    "campaign_id": "camp_...",
    "status": "active",
    "current_step": 3,
    "total_touchpoints": 5,
    "contacts_engaged": 2,
    "channels_used": ["email", "sms"],
    "created_at": "2024-10-20T10:00:00",
    "last_updated": "2024-10-23T10:00:00"
}
```

---

## Workflow Integration

### LangGraph Workflow

```python
from workflows.abm_campaign import create_campaign_workflow

# Create workflow
orchestrator = AccountOrchestrator()
workflow = create_campaign_workflow(orchestrator)

# Define initial state
initial_state = {
    "campaign_id": "camp_001",
    "account_id": "acc_001",
    "status": "active",
    "current_step": 0,
    "contacts": [...],
    "touchpoints": [],
    "responses": [],
    "conflicts": [],
    "metadata": {}
}

# Execute workflow
final_state = await workflow.execute(initial_state)
```

### Workflow Nodes

1. **initialize**: Set up campaign structure
2. **check_conflicts**: Detect response conflicts
3. **select_contact**: Choose next contact
4. **select_channel**: Determine channel
5. **generate_message**: Create content
6. **execute_touchpoint**: Send message
7. **evaluate_response**: Check engagement
8. **schedule_next**: Plan next touchpoint
9. **complete**: Finalize campaign

---

## Configuration

### Default Configuration

```python
default_config = {
    "max_touchpoints": 7,
    "touchpoint_intervals": [2, 3, 5, 7, 10, 14],
    "channel_escalation": [EMAIL, SMS, CALL],
    "colleague_message_delay": 3,
    "response_timeout": 48,
    "max_concurrent_contacts": 3,
    "conflict_check_enabled": True,
    "auto_pause_on_response": True
}
```

### Custom Configuration

```python
custom_config = {
    "max_touchpoints": 10,
    "touchpoint_intervals": [1, 2, 3, 5, 7, 10, 14, 21],
    "channel_escalation": [EMAIL, LINKEDIN, SMS, CALL],
    "colleague_message_delay": 5,
    "response_timeout": 72,
    "max_concurrent_contacts": 5
}

orchestrator = AccountOrchestrator(config=custom_config)
```

---

## Testing

### Run Tests

```bash
# Run all tests
pytest tests/test_account_orchestrator.py -v

# Run specific test class
pytest tests/test_account_orchestrator.py::TestChannelSelection -v

# Run with coverage
pytest tests/test_account_orchestrator.py --cov=agents.account_orchestrator
```

### Test Categories

1. **Initialization** (3 tests)
2. **Contact Extraction** (6 tests)
3. **Process New Lead** (4 tests)
4. **Channel Selection** (8 tests)
5. **Contact Selection** (3 tests)
6. **Colleague Messaging** (3 tests)
7. **Conflict Detection** (4 tests)
8. **Scheduling** (3 tests)
9. **Campaign Execution** (3 tests)
10. **Message Generation** (2 tests)
11. **Campaign Status** (2 tests)
12. **Edge Cases** (6 tests)

**Total**: 40+ comprehensive tests

---

## Best Practices

### 1. Contact Data Quality

✅ **DO**:
- Validate email addresses before campaign launch
- Include phone numbers for SMS/Call escalation
- Provide accurate titles for prioritization

❌ **DON'T**:
- Launch campaigns with missing contact data
- Use generic titles ("Employee", "Staff")
- Skip contact validation

### 2. Campaign Configuration

✅ **DO**:
- Adjust intervals based on industry norms
- Enable conflict detection for all campaigns
- Set realistic max_touchpoints (7-10)

❌ **DON'T**:
- Use aggressive intervals (<24 hours)
- Disable conflict checking
- Set excessive touchpoints (>15)

### 3. Message Personalization

✅ **DO**:
- Include company name in metadata
- Reference specific pain points
- Use colleague messaging strategically

❌ **DON'T**:
- Send generic templates
- Overuse colleague references
- Ignore engagement context

### 4. Monitoring

✅ **DO**:
- Check campaign status regularly
- Monitor conflict detection
- Track channel effectiveness

❌ **DON'T**:
- Set and forget campaigns
- Ignore pause signals
- Skip performance analysis

---

## Troubleshooting

### Common Issues

#### Issue: Campaign not starting

**Symptoms**: `process_new_lead()` returns error

**Solutions**:
1. Verify `account_id` is provided
2. Check at least one contact has email
3. Validate lead_data structure

```python
# Debug
print(f"Account ID: {lead_data.get('account_id')}")
print(f"Email: {lead_data.get('email')}")
```

#### Issue: Channel not escalating

**Symptoms**: Stuck on email channel

**Solutions**:
1. Verify contact has phone number
2. Check touchpoint count
3. Review channel_escalation config

```python
# Debug
contact = campaign['contacts'][0]
print(f"Has phone: {bool(contact.get('phone'))}")
print(f"Touchpoints: {len(campaign['touchpoints'])}")
```

#### Issue: Conflicts not detected

**Symptoms**: Campaign continues after response

**Solutions**:
1. Enable conflict checking in config
2. Verify Supabase connection
3. Check response table structure

```python
# Debug
print(f"Conflict check enabled: {orchestrator.config['conflict_check_enabled']}")
conflict = await orchestrator.check_conflicts(campaign_id)
print(f"Conflicts: {conflict}")
```

#### Issue: Messages not personalized

**Symptoms**: Generic message content

**Solutions**:
1. Include metadata in lead_data
2. Verify contact names present
3. Check message generation logic

```python
# Debug
print(f"Metadata: {campaign.get('metadata')}")
print(f"Contact name: {contact.get('name')}")
```

---

## Advanced Usage

### Custom Message Templates

Extend `generate_message()` for custom templates:

```python
class CustomOrchestrator(AccountOrchestrator):
    async def generate_message(self, campaign, contact, channel):
        # Custom logic
        if channel == CampaignChannel.EMAIL:
            return self._custom_email_template(campaign, contact)
        return await super().generate_message(campaign, contact, channel)
    
    def _custom_email_template(self, campaign, contact):
        return f"""
        Hi {contact['name']},
        
        Custom message for {campaign['metadata']['company_name']}...
        """
```

### Integration with CRM

```python
class CRMIntegratedOrchestrator(AccountOrchestrator):
    def __init__(self, crm_client, **kwargs):
        super().__init__(**kwargs)
        self.crm = crm_client
    
    async def _check_contact_response(self, contact_id):
        # Check CRM for responses
        response = await self.crm.get_contact_activity(contact_id)
        return response
```

---

## Performance Considerations

### Scalability

- **Concurrent Campaigns**: Supports 100+ active campaigns
- **Contacts per Campaign**: Optimized for 1-10 contacts
- **Touchpoints**: Efficient up to 20 touchpoints per campaign

### Optimization Tips

1. **Batch Processing**: Process multiple leads in parallel
2. **Caching**: Cache contact prioritization results
3. **Database Indexing**: Index campaign_id, contact_id fields
4. **Async Operations**: Use async/await throughout

---

## Changelog

### Version 1.0.0 (2024-10-23)

**Initial Release**
- Multi-contact campaign orchestration
- Colleague reference messaging
- Channel escalation (Email → SMS → Call)
- Conflict detection and auto-pause
- Autonomous scheduling
- LangGraph workflow integration
- Comprehensive test suite (40+ tests)

---

## Support

For issues, questions, or contributions:

- **Documentation**: This file
- **Examples**: `examples/orchestrator_usage.py`
- **Tests**: `tests/test_account_orchestrator.py`
- **Source**: `agents/account_orchestrator.py`

---

## License

See project LICENSE file.
