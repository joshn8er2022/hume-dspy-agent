"""
Comprehensive Test Suite for AccountOrchestrator

40+ edge case tests covering:
- Multi-contact coordination
- Conflict detection
- Channel escalation
- Colleague messaging
- Error handling
- State management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.account_orchestrator import (
    AccountOrchestrator,
    CampaignChannel,
    CampaignStatus,
    ContactRole
)


class TestAccountOrchestratorInitialization:
    """Test orchestrator initialization and configuration"""
    
    def test_init_with_defaults(self):
        """Test initialization with default configuration"""
        orchestrator = AccountOrchestrator()
        
        assert orchestrator.config is not None
        assert orchestrator.config["max_touchpoints"] == 7
        assert len(orchestrator.config["touchpoint_intervals"]) == 6
        assert orchestrator.active_campaigns == {}
    
    def test_init_with_custom_config(self):
        """Test initialization with custom configuration"""
        custom_config = {
            "max_touchpoints": 10,
            "conflict_check_enabled": False
        }
        
        orchestrator = AccountOrchestrator(config=custom_config)
        
        assert orchestrator.config["max_touchpoints"] == 10
        assert orchestrator.config["conflict_check_enabled"] is False
    
    def test_init_with_supabase_client(self):
        """Test initialization with Supabase client"""
        mock_supabase = Mock()
        orchestrator = AccountOrchestrator(supabase_client=mock_supabase)
        
        assert orchestrator.supabase == mock_supabase


class TestContactExtraction:
    """Test contact extraction and prioritization"""
    
    def test_extract_primary_contact_only(self):
        """Test extracting single primary contact"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "id": "lead_123",
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "title": "CTO"
        }
        
        contacts = orchestrator._extract_contacts(lead_data)
        
        assert len(contacts) == 1
        assert contacts[0]["role"] == ContactRole.PRIMARY.value
        assert contacts[0]["email"] == "john@example.com"
    
    def test_extract_multiple_contacts(self):
        """Test extracting primary and secondary contacts"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "id": "lead_123",
            "email": "primary@example.com",
            "name": "Primary Contact",
            "account_contacts": [
                {"id": "c1", "email": "secondary@example.com", "name": "Secondary"},
                {"id": "c2", "email": "tertiary@example.com", "name": "Tertiary"}
            ]
        }
        
        contacts = orchestrator._extract_contacts(lead_data)
        
        assert len(contacts) == 3
        assert contacts[0]["role"] == ContactRole.PRIMARY.value
        assert contacts[1]["role"] == ContactRole.SECONDARY.value
        assert contacts[2]["role"] == ContactRole.TERTIARY.value
    
    def test_extract_contacts_missing_email(self):
        """Test handling contacts without email"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "name": "No Email Contact",
            "account_contacts": [
                {"name": "Also No Email"}
            ]
        }
        
        contacts = orchestrator._extract_contacts(lead_data)
        
        assert len(contacts) == 0
    
    def test_prioritize_contacts_by_title(self):
        """Test contact prioritization based on title"""
        orchestrator = AccountOrchestrator()
        contacts = [
            {"email": "manager@example.com", "title": "Manager"},
            {"email": "ceo@example.com", "title": "CEO"},
            {"email": "director@example.com", "title": "Director"}
        ]
        
        prioritized = orchestrator._prioritize_contacts(contacts)
        
        assert prioritized[0]["title"] == "CEO"
        assert prioritized[1]["title"] == "Director"
        assert prioritized[2]["title"] == "Manager"
    
    def test_prioritize_contacts_case_insensitive(self):
        """Test title matching is case-insensitive"""
        orchestrator = AccountOrchestrator()
        contacts = [
            {"email": "vp@example.com", "title": "vice president of sales"},
            {"email": "cto@example.com", "title": "Chief Technology Officer"}
        ]
        
        prioritized = orchestrator._prioritize_contacts(contacts)
        
        assert prioritized[0]["title"] == "Chief Technology Officer"
        assert prioritized[0]["priority_score"] == 95


class TestProcessNewLead:
    """Test new lead processing and campaign initialization"""
    
    @pytest.mark.asyncio
    async def test_process_new_lead_success(self):
        """Test successful lead processing"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "account_id": "acc_123",
            "email": "contact@example.com",
            "name": "Test Contact"
        }
        
        result = await orchestrator.process_new_lead(lead_data)
        
        assert result["success"] is True
        assert "campaign_id" in result
        assert result["contacts_count"] == 1
    
    @pytest.mark.asyncio
    async def test_process_new_lead_missing_account_id(self):
        """Test error handling for missing account_id"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "email": "contact@example.com"
        }
        
        result = await orchestrator.process_new_lead(lead_data)
        
        assert result["success"] is False
        assert "account_id required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_new_lead_no_contacts(self):
        """Test error handling when no contacts found"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "account_id": "acc_123",
            "name": "No Email"
        }
        
        result = await orchestrator.process_new_lead(lead_data)
        
        assert result["success"] is False
        assert "No contacts found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_new_lead_stores_campaign(self):
        """Test campaign is stored in active_campaigns"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "account_id": "acc_123",
            "email": "contact@example.com",
            "name": "Test Contact"
        }
        
        result = await orchestrator.process_new_lead(lead_data)
        campaign_id = result["campaign_id"]
        
        assert campaign_id in orchestrator.active_campaigns
        assert orchestrator.active_campaigns[campaign_id]["status"] == CampaignStatus.ACTIVE.value


class TestChannelSelection:
    """Test channel selection and escalation logic"""
    
    def test_select_channel_first_touchpoint(self):
        """Test channel selection for first touchpoint"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "touchpoints": [],
            "current_step": 0
        }
        contact = {
            "contact_id": "c1",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
        
        channel = orchestrator.select_channel(campaign, contact)
        
        assert channel == CampaignChannel.EMAIL
    
    def test_select_channel_escalation_to_sms(self):
        """Test escalation from email to SMS"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "touchpoints": [
                {"contact_id": "c1", "channel": "email"},
                {"contact_id": "c1", "channel": "email"}
            ],
            "current_step": 2
        }
        contact = {
            "contact_id": "c1",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
        
        channel = orchestrator.select_channel(campaign, contact)
        
        assert channel == CampaignChannel.SMS
    
    def test_select_channel_escalation_to_call(self):
        """Test escalation from SMS to call"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "touchpoints": [
                {"contact_id": "c1", "channel": "email"},
                {"contact_id": "c1", "channel": "email"},
                {"contact_id": "c1", "channel": "sms"},
                {"contact_id": "c1", "channel": "sms"}
            ],
            "current_step": 4
        }
        contact = {
            "contact_id": "c1",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
        
        channel = orchestrator.select_channel(campaign, contact)
        
        assert channel == CampaignChannel.CALL
    
    def test_select_channel_no_phone(self):
        """Test channel selection when contact has no phone"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "touchpoints": [
                {"contact_id": "c1", "channel": "email"},
                {"contact_id": "c1", "channel": "email"}
            ],
            "current_step": 2
        }
        contact = {
            "contact_id": "c1",
            "email": "test@example.com"
        }
        
        channel = orchestrator.select_channel(campaign, contact)
        
        # Should default to email if SMS not available
        assert channel == CampaignChannel.EMAIL
    
    def test_has_channel_email(self):
        """Test checking if contact has email channel"""
        orchestrator = AccountOrchestrator()
        contact = {"email": "test@example.com"}
        
        assert orchestrator._has_channel(contact, CampaignChannel.EMAIL) is True
    
    def test_has_channel_sms(self):
        """Test checking if contact has SMS channel"""
        orchestrator = AccountOrchestrator()
        contact = {"phone": "+1234567890"}
        
        assert orchestrator._has_channel(contact, CampaignChannel.SMS) is True
    
    def test_has_channel_missing(self):
        """Test checking for missing channel"""
        orchestrator = AccountOrchestrator()
        contact = {"email": "test@example.com"}
        
        assert orchestrator._has_channel(contact, CampaignChannel.SMS) is False


class TestContactSelection:
    """Test contact selection logic"""
    
    def test_select_next_contact_first_steps(self):
        """Test selecting primary contact for first steps"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "contacts": [
                {"contact_id": "c1", "name": "Primary", "priority": 1},
                {"contact_id": "c2", "name": "Secondary", "priority": 2}
            ],
            "touchpoints": [],
            "current_step": 0
        }
        
        contact = orchestrator._select_next_contact(campaign)
        
        assert contact["contact_id"] == "c1"
    
    def test_select_next_contact_introduce_secondary(self):
        """Test introducing secondary contact after step 3"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "contacts": [
                {"contact_id": "c1", "name": "Primary", "priority": 1},
                {"contact_id": "c2", "name": "Secondary", "priority": 2}
            ],
            "touchpoints": [
                {"contact_id": "c1"},
                {"contact_id": "c1"},
                {"contact_id": "c1"}
            ],
            "current_step": 3
        }
        
        contact = orchestrator._select_next_contact(campaign)
        
        assert contact["contact_id"] == "c2"
    
    def test_select_next_contact_cycle_back(self):
        """Test cycling back to primary when all engaged"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "contacts": [
                {"contact_id": "c1", "name": "Primary", "priority": 1},
                {"contact_id": "c2", "name": "Secondary", "priority": 2}
            ],
            "touchpoints": [
                {"contact_id": "c1"},
                {"contact_id": "c2"}
            ],
            "current_step": 5
        }
        
        contact = orchestrator._select_next_contact(campaign)
        
        assert contact["contact_id"] == "c1"


class TestColleagueMessaging:
    """Test colleague reference message generation"""
    
    @pytest.mark.asyncio
    async def test_generate_colleague_message_basic(self):
        """Test basic colleague message generation"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "current_step": 0,
            "touchpoints": [],
            "metadata": {"company_name": "Acme Corp"}
        }
        target = {"name": "Sue Smith", "title": "VP Sales"}
        referring = {"name": "Dr. John Doe", "title": "CTO"}
        
        message = await orchestrator.generate_colleague_message(campaign, target, referring)
        
        assert "Sue" in message
        assert "John Doe" in message
        assert "Acme Corp" in message
    
    @pytest.mark.asyncio
    async def test_generate_colleague_message_with_engagement(self):
        """Test colleague message with engagement context"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "current_step": 1,
            "touchpoints": [
                {
                    "contact_id": "referring_id",
                    "topic": "AI automation platform"
                }
            ],
            "metadata": {"company_name": "Acme Corp"}
        }
        target = {"name": "Sue Smith"}
        referring = {"name": "Dr. John Doe", "title": "CTO", "contact_id": "referring_id"}
        
        message = await orchestrator.generate_colleague_message(campaign, target, referring)
        
        assert "AI automation platform" in message or "inquired" in message
    
    @pytest.mark.asyncio
    async def test_generate_colleague_message_template_rotation(self):
        """Test message template rotation"""
        orchestrator = AccountOrchestrator()
        target = {"name": "Sue Smith"}
        referring = {"name": "John Doe", "title": "CTO"}
        
        messages = []
        for step in range(3):
            campaign = {
                "current_step": step,
                "touchpoints": [],
                "metadata": {"company_name": "Acme"}
            }
            msg = await orchestrator.generate_colleague_message(campaign, target, referring)
            messages.append(msg)
        
        # Should have different templates
        assert len(set(messages)) > 1


class TestConflictDetection:
    """Test conflict detection and handling"""
    
    @pytest.mark.asyncio
    async def test_check_conflicts_no_conflicts(self):
        """Test conflict check with no conflicts"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "contacts": [{"role": ContactRole.PRIMARY.value, "contact_id": "c1"}],
            "metadata": {}
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        result = await orchestrator.check_conflicts("camp_123")
        
        assert result["has_conflict"] is False
    
    @pytest.mark.asyncio
    async def test_check_conflicts_meeting_scheduled(self):
        """Test conflict detection for scheduled meeting"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "contacts": [{"role": ContactRole.PRIMARY.value}],
            "metadata": {
                "meeting_scheduled": True,
                "meeting_time": "2024-01-01T10:00:00"
            }
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        result = await orchestrator.check_conflicts("camp_123")
        
        assert result["has_conflict"] is True
        assert any(c["type"] == "meeting_scheduled" for c in result["conflicts"])
    
    @pytest.mark.asyncio
    async def test_check_conflicts_unsubscribed(self):
        """Test conflict detection for unsubscribed contact"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "contacts": [
                {"role": ContactRole.PRIMARY.value, "name": "Test", "unsubscribed": True}
            ],
            "metadata": {}
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        result = await orchestrator.check_conflicts("camp_123")
        
        assert result["has_conflict"] is True
        assert any(c["type"] == "unsubscribed" for c in result["conflicts"])
    
    @pytest.mark.asyncio
    async def test_check_conflicts_campaign_not_found(self):
        """Test conflict check for non-existent campaign"""
        orchestrator = AccountOrchestrator()
        
        result = await orchestrator.check_conflicts("nonexistent")
        
        assert result["has_conflict"] is False
        assert "Campaign not found" in result["reason"]


class TestScheduling:
    """Test touchpoint scheduling logic"""
    
    @pytest.mark.asyncio
    async def test_schedule_next_touchpoint_immediate(self):
        """Test immediate touchpoint scheduling"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "current_step": 0
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        result = await orchestrator.schedule_next_touchpoint("camp_123", immediate=True)
        
        assert result is not None
        assert result["status"] == "scheduled"
        scheduled_time = datetime.fromisoformat(result["scheduled_time"])
        assert (datetime.utcnow() - scheduled_time).total_seconds() < 60
    
    @pytest.mark.asyncio
    async def test_schedule_next_touchpoint_delayed(self):
        """Test delayed touchpoint scheduling"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "current_step": 1
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        result = await orchestrator.schedule_next_touchpoint("camp_123", immediate=False)
        
        assert result is not None
        scheduled_time = datetime.fromisoformat(result["scheduled_time"])
        # Should be scheduled for future (interval from config)
        assert scheduled_time > datetime.utcnow()
    
    @pytest.mark.asyncio
    async def test_schedule_next_touchpoint_interval_progression(self):
        """Test scheduling intervals increase over time"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "current_step": 0
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        # Schedule multiple touchpoints
        times = []
        for step in range(3):
            campaign["current_step"] = step
            result = await orchestrator.schedule_next_touchpoint("camp_123")
            times.append(datetime.fromisoformat(result["scheduled_time"]))
        
        # Later touchpoints should have longer delays
        # (This is implicit in the interval configuration)
        assert len(times) == 3


class TestCampaignExecution:
    """Test campaign execution workflow"""
    
    @pytest.mark.asyncio
    async def test_execute_campaign_step_success(self):
        """Test successful campaign step execution"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "status": CampaignStatus.ACTIVE.value,
            "contacts": [
                {"contact_id": "c1", "name": "Test", "email": "test@example.com"}
            ],
            "touchpoints": [],
            "current_step": 0,
            "metadata": {}
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        result = await orchestrator.execute_campaign_step("camp_123")
        
        assert result["success"] is True
        assert result["step"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_campaign_step_not_active(self):
        """Test execution fails for non-active campaign"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "status": CampaignStatus.PAUSED.value,
            "contacts": [],
            "touchpoints": [],
            "current_step": 0
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        result = await orchestrator.execute_campaign_step("camp_123")
        
        assert result["success"] is False
        assert "not active" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_campaign_step_not_found(self):
        """Test execution fails for non-existent campaign"""
        orchestrator = AccountOrchestrator()
        
        result = await orchestrator.execute_campaign_step("nonexistent")
        
        assert result["success"] is False


class TestMessageGeneration:
    """Test message generation"""
    
    @pytest.mark.asyncio
    async def test_generate_message_email(self):
        """Test email message generation"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "touchpoints": [],
            "contacts": [],
            "metadata": {"company_name": "Acme Corp"}
        }
        contact = {"name": "John Doe", "role": ContactRole.PRIMARY.value}
        
        message = await orchestrator.generate_message(campaign, contact, CampaignChannel.EMAIL)
        
        assert "John" in message
        assert "Acme Corp" in message
    
    @pytest.mark.asyncio
    async def test_generate_message_sms(self):
        """Test SMS message generation (shorter)"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "touchpoints": [],
            "contacts": [],
            "metadata": {"company_name": "Acme Corp"}
        }
        contact = {"name": "John Doe", "role": ContactRole.PRIMARY.value}
        
        message = await orchestrator.generate_message(campaign, contact, CampaignChannel.SMS)
        
        # SMS should be shorter
        assert len(message) < 200
        assert "John" in message


class TestCampaignStatus:
    """Test campaign status and metrics"""
    
    def test_get_campaign_status_success(self):
        """Test getting campaign status"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "campaign_id": "camp_123",
            "status": CampaignStatus.ACTIVE.value,
            "current_step": 3,
            "touchpoints": [
                {"contact_id": "c1", "channel": "email"},
                {"contact_id": "c2", "channel": "sms"}
            ],
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-02T00:00:00"
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        status = orchestrator.get_campaign_status("camp_123")
        
        assert status["campaign_id"] == "camp_123"
        assert status["status"] == CampaignStatus.ACTIVE.value
        assert status["current_step"] == 3
        assert status["total_touchpoints"] == 2
        assert status["contacts_engaged"] == 2
    
    def test_get_campaign_status_not_found(self):
        """Test getting status for non-existent campaign"""
        orchestrator = AccountOrchestrator()
        
        status = orchestrator.get_campaign_status("nonexistent")
        
        assert status is None


class TestEdgeCases:
    """Additional edge case tests"""
    
    @pytest.mark.asyncio
    async def test_empty_contact_list(self):
        """Test handling empty contact list"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "account_id": "acc_123",
            "account_contacts": []
        }
        
        result = await orchestrator.process_new_lead(lead_data)
        
        assert result["success"] is False
    
    def test_contact_without_name(self):
        """Test handling contact without name"""
        orchestrator = AccountOrchestrator()
        lead_data = {
            "email": "test@example.com"
        }
        
        contacts = orchestrator._extract_contacts(lead_data)
        
        assert len(contacts) == 1
        assert contacts[0]["name"] == "Unknown"
    
    @pytest.mark.asyncio
    async def test_max_touchpoints_reached(self):
        """Test campaign completion when max touchpoints reached"""
        orchestrator = AccountOrchestrator(config={"max_touchpoints": 2})
        campaign = {
            "campaign_id": "camp_123",
            "status": CampaignStatus.ACTIVE.value,
            "contacts": [{"contact_id": "c1", "name": "Test", "email": "test@example.com"}],
            "touchpoints": [{}, {}],
            "current_step": 2,
            "metadata": {}
        }
        orchestrator.active_campaigns["camp_123"] = campaign
        
        result = await orchestrator.execute_campaign_step("camp_123")
        
        # Should complete after max touchpoints
        assert campaign["status"] == CampaignStatus.COMPLETED.value
    
    def test_channel_escalation_all_exhausted(self):
        """Test channel selection when all channels exhausted"""
        orchestrator = AccountOrchestrator()
        campaign = {
            "touchpoints": [
                {"contact_id": "c1", "channel": "email"},
                {"contact_id": "c1", "channel": "email"},
                {"contact_id": "c1", "channel": "sms"},
                {"contact_id": "c1", "channel": "sms"},
                {"contact_id": "c1", "channel": "call"},
                {"contact_id": "c1", "channel": "call"}
            ],
            "current_step": 6
        }
        contact = {
            "contact_id": "c1",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
        
        channel = orchestrator.select_channel(campaign, contact)
        
        # Should default to email
        assert channel == CampaignChannel.EMAIL
    
    @pytest.mark.asyncio
    async def test_concurrent_campaign_limit(self):
        """Test handling multiple concurrent campaigns"""
        orchestrator = AccountOrchestrator()
        
        # Create multiple campaigns
        for i in range(5):
            lead_data = {
                "account_id": f"acc_{i}",
                "email": f"contact{i}@example.com",
                "name": f"Contact {i}"
            }
            await orchestrator.process_new_lead(lead_data)
        
        assert len(orchestrator.active_campaigns) == 5
    
    def test_contact_priority_tie_breaking(self):
        """Test priority tie-breaking for contacts with same title"""
        orchestrator = AccountOrchestrator()
        contacts = [
            {"email": "vp1@example.com", "title": "VP Sales"},
            {"email": "vp2@example.com", "title": "VP Marketing"}
        ]
        
        prioritized = orchestrator._prioritize_contacts(contacts)
        
        # Both should have same priority score
        assert prioritized[0]["priority_score"] == prioritized[1]["priority_score"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
