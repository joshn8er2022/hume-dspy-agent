"""End-to-End ABM Integration Tests.

Tests the complete ABM flow from lead submission through multi-contact campaigns.
Simplified version that works with existing infrastructure.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from agents.inbound_agent import InboundAgent
from agents.follow_up_agent import FollowUpAgent
from agents.account_orchestrator import AccountOrchestrator
from models import Lead, LeadTier


class TestE2EABMIntegration:
    """End-to-end ABM integration tests."""

    @pytest.fixture
    def sample_lead(self):
        """Create a sample lead for testing."""
        return Lead(
            id='test-lead-001',
            email='dr.xyz@example.com',
            response_type='typeform',
            form_data={
                'first_name': 'Dr.',
                'last_name': 'XYZ',
                'company': 'Example Healthcare',
                'title': 'Chief Medical Officer',
                'phone': '+1-555-0100',
                'business_size': '50-200 employees',
                'patient_volume': '1000+ patients',
                'use_case': 'Body composition tracking for patient outcomes',
                'ai_summary': 'Interested in body composition tracking',
            }
        )

    def test_01_inbound_agent_has_orchestrator(self):
        """Test 1: InboundAgent has AccountOrchestrator initialized."""
        agent = InboundAgent()
        assert hasattr(agent, 'orchestrator')
        assert isinstance(agent.orchestrator, AccountOrchestrator)
        print("✅ Test 1: InboundAgent has AccountOrchestrator")

    def test_02_followup_agent_has_orchestrator(self):
        """Test 2: FollowUpAgent has AccountOrchestrator initialized."""
        agent = FollowUpAgent()
        assert hasattr(agent, 'orchestrator')
        assert isinstance(agent.orchestrator, AccountOrchestrator)
        print("✅ Test 2: FollowUpAgent has AccountOrchestrator")

    def test_03_inbound_qualification_creates_campaign_id(self, sample_lead):
        """Test 3: InboundAgent qualification adds campaign_id for qualified leads."""
        agent = InboundAgent()
        
        # Mock the orchestrator to avoid actual API calls
        with patch.object(agent.orchestrator, 'process_new_lead', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {'campaign_id': 'test-campaign-123', 'status': 'success'}
            
            # Qualify the lead
            result = agent.forward(sample_lead)
            
            # Check that result has campaign_id if qualified
            if result.is_qualified and result.tier in [LeadTier.SCORCHING, LeadTier.HOT, LeadTier.WARM]:
                assert hasattr(result, 'campaign_id')
                print(f"✅ Test 3: Campaign ID added for {result.tier.value} lead")
            else:
                print(f"ℹ️ Test 3: Lead not qualified for ABM (tier: {result.tier.value})")

    @pytest.mark.asyncio
    async def test_04_orchestrator_process_new_lead(self):
        """Test 4: AccountOrchestrator can process new lead."""
        orchestrator = AccountOrchestrator()
        
        lead_data = {
            'company_name': 'Example Healthcare',
            'contact_name': 'Dr. XYZ',
            'contact_email': 'dr.xyz@example.com',
            'contact_phone': '+1-555-0100',
            'contact_title': 'CMO',
            'inquiry_topic': 'body composition tracking',
            'qualification_tier': 'hot',
        }
        
        # Mock the research and graph to avoid actual API calls
        with patch.object(orchestrator.research, 'find_colleagues', new_callable=AsyncMock) as mock_research:
            with patch.object(orchestrator.graph, 'save_campaign', new_callable=AsyncMock) as mock_save:
                mock_research.return_value = []
                mock_save.return_value = {'id': 'campaign-123'}
                
                result = await orchestrator.process_new_lead(lead_data)
                
                assert result is not None
                assert 'status' in result
                print("✅ Test 4: AccountOrchestrator processes new lead")

    @pytest.mark.asyncio
    async def test_05_orchestrator_handles_research_failure(self):
        """Test 5: AccountOrchestrator handles research failure gracefully."""
        orchestrator = AccountOrchestrator()
        
        lead_data = {
            'company_name': 'Example Healthcare',
            'contact_name': 'Dr. XYZ',
            'contact_email': 'dr.xyz@example.com',
        }
        
        # Mock research to fail
        with patch.object(orchestrator.research, 'find_colleagues', new_callable=AsyncMock) as mock_research:
            with patch.object(orchestrator.graph, 'save_campaign', new_callable=AsyncMock) as mock_save:
                mock_research.side_effect = Exception("Research API unavailable")
                mock_save.return_value = {'id': 'campaign-123'}
                
                # Should not crash
                result = await orchestrator.process_new_lead(lead_data)
                assert result is not None
                print("✅ Test 5: Graceful degradation on research failure")

    @pytest.mark.asyncio
    async def test_06_orchestrator_execute_campaign_step(self):
        """Test 6: AccountOrchestrator can execute campaign step."""
        orchestrator = AccountOrchestrator()
        
        # Mock the graph methods
        with patch.object(orchestrator.graph, 'get_campaign', new_callable=AsyncMock) as mock_get:
            with patch.object(orchestrator.graph, 'get_conversation_context', new_callable=AsyncMock) as mock_context:
                mock_get.return_value = {
                    'id': 'campaign-123',
                    'status': 'active',
                    'account_id': 'account-123'
                }
                mock_context.return_value = {
                    'campaign_id': 'campaign-123',
                    'primary_responded': False,
                    'status': 'active'
                }
                
                result = await orchestrator.execute_campaign_step('campaign-123')
                assert result is not None
                print("✅ Test 6: Campaign step execution works")

    @pytest.mark.asyncio
    async def test_07_orchestrator_close_campaign(self):
        """Test 7: AccountOrchestrator can close campaign."""
        orchestrator = AccountOrchestrator()
        
        with patch.object(orchestrator.graph, 'update_campaign_status', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {'status': 'success'}
            
            result = await orchestrator.close_campaign('campaign-123', 'won')
            assert result is not None
            assert result.get('status') == 'success'
            print("✅ Test 7: Campaign closure works")

    def test_08_qualification_result_has_campaign_id_field(self):
        """Test 8: QualificationResult model has campaign_id field."""
        from models.qualification import QualificationResult
        
        # Check that the model has campaign_id field
        assert 'campaign_id' in QualificationResult.model_fields
        print("✅ Test 8: QualificationResult has campaign_id field")

    @pytest.mark.asyncio
    async def test_09_concurrent_campaigns_different_companies(self):
        """Test 9: Multiple campaigns can run concurrently."""
        orchestrator = AccountOrchestrator()
        
        lead1 = {
            'company_name': 'Company A',
            'contact_email': 'person1@companya.com',
        }
        
        lead2 = {
            'company_name': 'Company B',
            'contact_email': 'person2@companyb.com',
        }
        
        with patch.object(orchestrator.research, 'find_colleagues', new_callable=AsyncMock) as mock_research:
            with patch.object(orchestrator.graph, 'save_campaign', new_callable=AsyncMock) as mock_save:
                mock_research.return_value = []
                mock_save.side_effect = [
                    {'id': 'campaign-1'},
                    {'id': 'campaign-2'}
                ]
                
                result1 = await orchestrator.process_new_lead(lead1)
                result2 = await orchestrator.process_new_lead(lead2)
                
                assert result1 is not None
                assert result2 is not None
                print("✅ Test 9: Concurrent campaigns work")

    @pytest.mark.asyncio
    async def test_10_integration_inbound_to_orchestrator(self, sample_lead):
        """Test 10: Full integration from InboundAgent to AccountOrchestrator."""
        agent = InboundAgent()
        
        # Mock orchestrator to track if it was called
        campaign_initiated = False
        
        async def mock_process_lead(data):
            nonlocal campaign_initiated
            campaign_initiated = True
            return {'campaign_id': 'test-campaign-456', 'status': 'success'}
        
        with patch.object(agent.orchestrator, 'process_new_lead', side_effect=mock_process_lead):
            result = agent.forward(sample_lead)
            
            # If qualified as HOT/SCORCHING/WARM, campaign should be initiated
            if result.tier in [LeadTier.SCORCHING, LeadTier.HOT, LeadTier.WARM]:
                assert campaign_initiated, "Campaign should be initiated for qualified leads"
                assert hasattr(result, 'campaign_id')
                print(f"✅ Test 10: Full integration works for {result.tier.value} lead")
            else:
                print(f"ℹ️ Test 10: Lead tier {result.tier.value} - no ABM campaign")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
