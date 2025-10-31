"""
AccountOrchestrator Usage Examples

Demonstrates practical usage of the AccountOrchestrator agent for:
- Multi-contact ABM campaigns
- Colleague reference messaging
- Channel escalation
- Conflict detection
- Autonomous scheduling
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.account_orchestrator import AccountOrchestrator, CampaignChannel
from workflows.abm_campaign import create_campaign_workflow, CampaignState


# ============================================================================
# Example 1: Basic Single-Contact Campaign
# ============================================================================

async def example_1_basic_campaign():
    """
    Example 1: Launch a basic ABM campaign for a single contact.
    
    Use Case: Simple outreach to a primary decision-maker.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Single-Contact Campaign")
    print("="*80)
    
    # Initialize orchestrator
    orchestrator = AccountOrchestrator()
    
    # Define lead data
    lead_data = {
        "account_id": "acc_acme_corp",
        "id": "lead_001",
        "name": "Dr. Sarah Chen",
        "email": "sarah.chen@acmecorp.com",
        "phone": "+1-555-0123",
        "title": "Chief Technology Officer",
        "metadata": {
            "company_name": "Acme Corporation",
            "industry": "Healthcare Technology",
            "company_size": "500-1000 employees"
        }
    }
    
    # Process new lead and initiate campaign
    result = await orchestrator.process_new_lead(lead_data)
    
    print(f"\nCampaign Initiated:")
    print(f"  Campaign ID: {result['campaign_id']}")
    print(f"  Contacts: {result['contacts_count']}")
    print(f"  First Touchpoint: {result.get('first_touchpoint', {}).get('scheduled_time')}")
    
    # Get campaign status
    status = orchestrator.get_campaign_status(result['campaign_id'])
    print(f"\nCampaign Status:")
    print(f"  Status: {status['status']}")
    print(f"  Current Step: {status['current_step']}")
    print(f"  Total Touchpoints: {status['total_touchpoints']}")
    
    return result['campaign_id']


# ============================================================================
# Example 2: Multi-Contact Account Campaign
# ============================================================================

async def example_2_multi_contact_campaign():
    """
    Example 2: Launch ABM campaign targeting multiple contacts in an account.
    
    Use Case: Engage multiple stakeholders (CTO, VP Engineering, Director).
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Multi-Contact Account Campaign")
    print("="*80)
    
    orchestrator = AccountOrchestrator()
    
    # Define account with multiple contacts
    lead_data = {
        "account_id": "acc_techstart_inc",
        "id": "lead_002",
        "name": "Michael Rodriguez",
        "email": "michael.rodriguez@techstart.com",
        "phone": "+1-555-0124",
        "title": "Chief Technology Officer",
        "account_contacts": [
            {
                "id": "contact_002_1",
                "name": "Jennifer Wu",
                "email": "jennifer.wu@techstart.com",
                "phone": "+1-555-0125",
                "title": "VP of Engineering"
            },
            {
                "id": "contact_002_2",
                "name": "David Park",
                "email": "david.park@techstart.com",
                "phone": "+1-555-0126",
                "title": "Director of Product"
            }
        ],
        "metadata": {
            "company_name": "TechStart Inc",
            "industry": "SaaS",
            "company_size": "100-250 employees"
        }
    }
    
    result = await orchestrator.process_new_lead(lead_data)
    
    print(f"\nMulti-Contact Campaign Initiated:")
    print(f"  Campaign ID: {result['campaign_id']}")
    print(f"  Total Contacts: {result['contacts_count']}")
    
    # Show contact prioritization
    campaign = orchestrator.active_campaigns[result['campaign_id']]
    print(f"\nContact Priority Order:")
    for idx, contact in enumerate(campaign['contacts'], 1):
        print(f"  {idx}. {contact['name']} - {contact['title']} (Score: {contact.get('priority_score', 0)})")
    
    return result['campaign_id']


# ============================================================================
# Example 3: Colleague Reference Messaging
# ============================================================================

async def example_3_colleague_messaging():
    """
    Example 3: Generate colleague reference messages.
    
    Use Case: "Sue, your colleague Dr. XYZ inquired about..."
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Colleague Reference Messaging")
    print("="*80)
    
    orchestrator = AccountOrchestrator()
    
    # Simulate campaign with primary contact engagement
    campaign = {
        "campaign_id": "camp_demo_003",
        "current_step": 3,
        "touchpoints": [
            {
                "contact_id": "primary_contact",
                "topic": "AI-powered sales automation",
                "channel": "email"
            }
        ],
        "metadata": {
            "company_name": "Innovation Labs"
        }
    }
    
    # Define contacts
    primary_contact = {
        "contact_id": "primary_contact",
        "name": "Dr. Emily Johnson",
        "title": "Chief Innovation Officer",
        "email": "emily.johnson@innovationlabs.com"
    }
    
    secondary_contact = {
        "contact_id": "secondary_contact",
        "name": "Robert Martinez",
        "title": "VP of Sales Operations",
        "email": "robert.martinez@innovationlabs.com"
    }
    
    # Generate colleague reference message
    message = await orchestrator.generate_colleague_message(
        campaign,
        secondary_contact,
        primary_contact
    )
    
    print(f"\nColleague Reference Message:")
    print(f"\nTo: {secondary_contact['name']} ({secondary_contact['title']})")
    print(f"Referencing: {primary_contact['name']} ({primary_contact['title']})")
    print(f"\n{'-'*80}")
    print(message)
    print(f"{'-'*80}")


# ============================================================================
# Example 4: Channel Escalation
# ============================================================================

async def example_4_channel_escalation():
    """
    Example 4: Demonstrate channel escalation (Email → SMS → Call).
    
    Use Case: Automatic escalation when contact doesn't respond.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Channel Escalation")
    print("="*80)
    
    orchestrator = AccountOrchestrator()
    
    contact = {
        "contact_id": "c_escalation",
        "name": "Alex Thompson",
        "email": "alex.thompson@example.com",
        "phone": "+1-555-0127"
    }
    
    # Simulate campaign progression
    touchpoint_scenarios = [
        {"step": 0, "touchpoints": []},
        {"step": 2, "touchpoints": [
            {"contact_id": "c_escalation", "channel": "email"},
            {"contact_id": "c_escalation", "channel": "email"}
        ]},
        {"step": 4, "touchpoints": [
            {"contact_id": "c_escalation", "channel": "email"},
            {"contact_id": "c_escalation", "channel": "email"},
            {"contact_id": "c_escalation", "channel": "sms"},
            {"contact_id": "c_escalation", "channel": "sms"}
        ]}
    ]
    
    print(f"\nChannel Escalation Path for {contact['name']}:")
    print(f"{'-'*80}")
    
    for scenario in touchpoint_scenarios:
        campaign = {
            "touchpoints": scenario["touchpoints"],
            "current_step": scenario["step"]
        }
        
        channel = orchestrator.select_channel(campaign, contact)
        
        print(f"Step {scenario['step']}: {len(scenario['touchpoints'])} previous touchpoints → {channel.value.upper()}")
    
    print(f"{'-'*80}")
    print("\nEscalation Logic:")
    print("  - Steps 0-1: Email (initial outreach)")
    print("  - Steps 2-3: SMS (after 2 email attempts)")
    print("  - Steps 4+: Call (after 2 SMS attempts)")


# ============================================================================
# Example 5: Conflict Detection
# ============================================================================

async def example_5_conflict_detection():
    """
    Example 5: Demonstrate conflict detection and campaign pausing.
    
    Use Case: Pause campaign when primary contact responds or meeting scheduled.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Conflict Detection")
    print("="*80)
    
    orchestrator = AccountOrchestrator()
    
    # Scenario 1: Meeting scheduled
    print("\nScenario 1: Meeting Scheduled")
    campaign_1 = {
        "campaign_id": "camp_conflict_1",
        "contacts": [{"role": "primary", "contact_id": "c1"}],
        "metadata": {
            "meeting_scheduled": True,
            "meeting_time": "2024-10-25T14:00:00"
        }
    }
    orchestrator.active_campaigns["camp_conflict_1"] = campaign_1
    
    result_1 = await orchestrator.check_conflicts("camp_conflict_1")
    print(f"  Has Conflict: {result_1['has_conflict']}")
    print(f"  Should Pause: {result_1['should_pause']}")
    if result_1['conflicts']:
        print(f"  Conflict Type: {result_1['conflicts'][0]['type']}")
    
    # Scenario 2: Contact unsubscribed
    print("\nScenario 2: Contact Unsubscribed")
    campaign_2 = {
        "campaign_id": "camp_conflict_2",
        "contacts": [
            {
                "role": "primary",
                "contact_id": "c2",
                "name": "Jane Doe",
                "unsubscribed": True
            }
        ],
        "metadata": {}
    }
    orchestrator.active_campaigns["camp_conflict_2"] = campaign_2
    
    result_2 = await orchestrator.check_conflicts("camp_conflict_2")
    print(f"  Has Conflict: {result_2['has_conflict']}")
    print(f"  Should Pause: {result_2['should_pause']}")
    if result_2['conflicts']:
        print(f"  Conflict Type: {result_2['conflicts'][0]['type']}")
        print(f"  Contact: {result_2['conflicts'][0]['contact']}")
    
    # Scenario 3: No conflicts
    print("\nScenario 3: No Conflicts (Campaign Continues)")
    campaign_3 = {
        "campaign_id": "camp_conflict_3",
        "contacts": [{"role": "primary", "contact_id": "c3"}],
        "metadata": {}
    }
    orchestrator.active_campaigns["camp_conflict_3"] = campaign_3
    
    result_3 = await orchestrator.check_conflicts("camp_conflict_3")
    print(f"  Has Conflict: {result_3['has_conflict']}")
    print(f"  Campaign Status: Active")


# ============================================================================
# Example 6: Complete Campaign Workflow with LangGraph
# ============================================================================

async def example_6_complete_workflow():
    """
    Example 6: Execute complete campaign workflow using LangGraph.
    
    Use Case: Full autonomous campaign execution with state management.
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Complete Campaign Workflow (LangGraph)")
    print("="*80)
    
    # Initialize orchestrator and workflow
    orchestrator = AccountOrchestrator()
    workflow = create_campaign_workflow(orchestrator)
    
    # Define initial campaign state
    initial_state = {
        "campaign_id": "camp_workflow_001",
        "account_id": "acc_workflow_test",
        "status": "active",
        "current_step": 0,
        "contacts": [
            {
                "contact_id": "wf_c1",
                "name": "Lisa Anderson",
                "email": "lisa.anderson@example.com",
                "phone": "+1-555-0128",
                "title": "CEO",
                "role": "primary",
                "priority": 1
            }
        ],
        "touchpoints": [],
        "responses": [],
        "conflicts": [],
        "next_action": None,
        "error": None,
        "metadata": {
            "company_name": "Workflow Demo Corp"
        }
    }
    
    print("\nInitial State:")
    print(f"  Campaign ID: {initial_state['campaign_id']}")
    print(f"  Account: {initial_state['metadata']['company_name']}")
    print(f"  Primary Contact: {initial_state['contacts'][0]['name']}")
    
    # Execute workflow
    print("\nExecuting Workflow...")
    final_state = await workflow.execute(initial_state)
    
    print("\nFinal State:")
    print(f"  Status: {final_state.get('status')}")
    print(f"  Current Step: {final_state.get('current_step')}")
    print(f"  Touchpoints Executed: {len(final_state.get('touchpoints', []))}")
    print(f"  Conflicts Detected: {len(final_state.get('conflicts', []))}")
    
    if final_state.get('error'):
        print(f"  Error: {final_state['error']}")
    
    # Show touchpoint details
    if final_state.get('touchpoints'):
        print("\nTouchpoint Details:")
        for idx, tp in enumerate(final_state['touchpoints'], 1):
            print(f"  {idx}. {tp.get('contact_name')} via {tp.get('channel')} at {tp.get('executed_at')}")


# ============================================================================
# Example 7: Custom Configuration
# ============================================================================

async def example_7_custom_configuration():
    """
    Example 7: Use custom configuration for campaign behavior.
    
    Use Case: Adjust touchpoint intervals, max attempts, escalation rules.
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Custom Configuration")
    print("="*80)
    
    # Define custom configuration
    custom_config = {
        "max_touchpoints": 10,  # More aggressive campaign
        "touchpoint_intervals": [1, 2, 3, 5, 7, 10, 14, 21],  # Custom intervals
        "channel_escalation": [
            CampaignChannel.EMAIL,
            CampaignChannel.LINKEDIN,
            CampaignChannel.SMS,
            CampaignChannel.CALL
        ],
        "colleague_message_delay": 5,  # Wait 5 days before colleague outreach
        "response_timeout": 72,  # 72 hours to respond
        "max_concurrent_contacts": 5,  # Engage up to 5 contacts
        "conflict_check_enabled": True,
        "auto_pause_on_response": True
    }
    
    orchestrator = AccountOrchestrator(config=custom_config)
    
    print("\nCustom Configuration:")
    print(f"  Max Touchpoints: {orchestrator.config['max_touchpoints']}")
    print(f"  Touchpoint Intervals: {orchestrator.config['touchpoint_intervals']}")
    print(f"  Channel Escalation: {[c.value for c in orchestrator.config['channel_escalation']]}")
    print(f"  Colleague Message Delay: {orchestrator.config['colleague_message_delay']} days")
    print(f"  Response Timeout: {orchestrator.config['response_timeout']} hours")
    print(f"  Max Concurrent Contacts: {orchestrator.config['max_concurrent_contacts']}")
    
    # Launch campaign with custom config
    lead_data = {
        "account_id": "acc_custom_config",
        "email": "contact@customconfig.com",
        "name": "Custom Config Test"
    }
    
    result = await orchestrator.process_new_lead(lead_data)
    print(f"\nCampaign launched with custom configuration: {result['campaign_id']}")


# ============================================================================
# Example 8: Campaign Monitoring and Metrics
# ============================================================================

async def example_8_monitoring_metrics():
    """
    Example 8: Monitor campaign progress and extract metrics.
    
    Use Case: Track campaign performance, engagement rates, channel effectiveness.
    """
    print("\n" + "="*80)
    print("EXAMPLE 8: Campaign Monitoring and Metrics")
    print("="*80)
    
    orchestrator = AccountOrchestrator()
    
    # Create sample campaign with history
    campaign_id = "camp_metrics_001"
    campaign = {
        "campaign_id": campaign_id,
        "account_id": "acc_metrics",
        "status": "active",
        "current_step": 5,
        "contacts": [
            {"contact_id": "m_c1", "name": "Contact 1"},
            {"contact_id": "m_c2", "name": "Contact 2"},
            {"contact_id": "m_c3", "name": "Contact 3"}
        ],
        "touchpoints": [
            {"contact_id": "m_c1", "channel": "email", "executed_at": "2024-10-20T10:00:00"},
            {"contact_id": "m_c1", "channel": "email", "executed_at": "2024-10-21T10:00:00"},
            {"contact_id": "m_c2", "channel": "email", "executed_at": "2024-10-22T10:00:00"},
            {"contact_id": "m_c1", "channel": "sms", "executed_at": "2024-10-23T10:00:00"},
            {"contact_id": "m_c3", "channel": "email", "executed_at": "2024-10-23T14:00:00"}
        ],
        "created_at": "2024-10-20T09:00:00",
        "last_updated": "2024-10-23T14:00:00"
    }
    
    orchestrator.active_campaigns[campaign_id] = campaign
    
    # Get campaign status
    status = orchestrator.get_campaign_status(campaign_id)
    
    print("\nCampaign Metrics:")
    print(f"  Campaign ID: {status['campaign_id']}")
    print(f"  Status: {status['status']}")
    print(f"  Current Step: {status['current_step']}")
    print(f"  Total Touchpoints: {status['total_touchpoints']}")
    print(f"  Contacts Engaged: {status['contacts_engaged']} / {len(campaign['contacts'])}")
    print(f"  Channels Used: {', '.join(status['channels_used'])}")
    print(f"  Created: {status['created_at']}")
    print(f"  Last Updated: {status['last_updated']}")
    
    # Calculate additional metrics
    touchpoints = campaign['touchpoints']
    channel_breakdown = {}
    for tp in touchpoints:
        channel = tp['channel']
        channel_breakdown[channel] = channel_breakdown.get(channel, 0) + 1
    
    print("\nChannel Breakdown:")
    for channel, count in channel_breakdown.items():
        print(f"  {channel.upper()}: {count} touchpoints")
    
    # Contact engagement
    contact_engagement = {}
    for tp in touchpoints:
        contact_id = tp['contact_id']
        contact_engagement[contact_id] = contact_engagement.get(contact_id, 0) + 1
    
    print("\nContact Engagement:")
    for contact_id, count in contact_engagement.items():
        contact_name = next((c['name'] for c in campaign['contacts'] if c['contact_id'] == contact_id), 'Unknown')
        print(f"  {contact_name}: {count} touchpoints")


# ============================================================================
# Main Execution
# ============================================================================

async def main():
    """
    Run all examples sequentially.
    """
    print("\n" + "#"*80)
    print("# AccountOrchestrator Usage Examples")
    print("# Demonstrating Multi-Contact ABM Campaign Management")
    print("#"*80)
    
    try:
        # Run all examples
        await example_1_basic_campaign()
        await example_2_multi_contact_campaign()
        await example_3_colleague_messaging()
        await example_4_channel_escalation()
        await example_5_conflict_detection()
        await example_6_complete_workflow()
        await example_7_custom_configuration()
        await example_8_monitoring_metrics()
        
        print("\n" + "#"*80)
        print("# All Examples Completed Successfully!")
        print("#"*80 + "\n")
        
    except Exception as e:
        print(f"\nError running examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
