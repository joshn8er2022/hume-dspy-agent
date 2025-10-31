"""Comprehensive tests for email reliability features."""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import sys
sys.path.insert(0, '/root/hume-dspy-agent')

from utils.email_client import EmailClient


class TestEmailReliability:
    """Test email reliability features: retry, fallback, notifications."""

    def setup_method(self):
        """Set up test environment."""
        # Mock environment variables
        os.environ["GMASS_API_KEY"] = "test_gmass_key"
        os.environ["FROM_EMAIL"] = "test@example.com"
        os.environ["SENDGRID_API_KEY"] = "test_sendgrid_key"
        os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/test"

        self.client = EmailClient()

    @patch('utils.email_client.requests.post')
    def test_gmass_success_first_attempt(self, mock_post):
        """Test GMass succeeds on first attempt."""
        # Mock successful GMass response
        mock_draft = Mock()
        mock_draft.status_code = 200
        mock_draft.json.return_value = {"campaignDraftId": "draft123"}

        mock_campaign = Mock()
        mock_campaign.status_code = 200
        mock_campaign.json.return_value = {"campaignId": "campaign123"}

        mock_post.side_effect = [mock_draft, mock_campaign]

        # Send email
        result = self.client.send_email(
            to_email="test@example.com",
            lead_id="lead123",
            template_type="initial_outreach",
            tier="HOT"
        )

        assert result == True
        assert mock_post.call_count == 2  # Draft + Campaign

    @patch('utils.email_client.requests.post')
    def test_gmass_retry_then_success(self, mock_post):
        """Test GMass fails twice, succeeds on third attempt."""
        # Mock GMass responses: fail, fail, success
        mock_fail = Mock()
        mock_fail.status_code = 500

        mock_success_draft = Mock()
        mock_success_draft.status_code = 200
        mock_success_draft.json.return_value = {"campaignDraftId": "draft123"}

        mock_success_campaign = Mock()
        mock_success_campaign.status_code = 200
        mock_success_campaign.json.return_value = {"campaignId": "campaign123"}

        mock_post.side_effect = [
            mock_fail,  # First attempt fails
            mock_fail,  # Second attempt fails
            mock_success_draft,  # Third attempt succeeds (draft)
            mock_success_campaign  # Campaign send
        ]

        result = self.client.send_email(
            to_email="test@example.com",
            lead_id="lead123",
            template_type="initial_outreach",
            tier="HOT"
        )

        assert result == True
        assert mock_post.call_count == 4  # 2 fails + draft + campaign

    @patch('utils.email_client.requests.post')
    def test_gmass_fails_sendgrid_succeeds(self, mock_post):
        """Test GMass fails completely, SendGrid succeeds."""
        # Mock GMass failure (all 3 attempts)
        mock_gmass_fail = Mock()
        mock_gmass_fail.status_code = 500

        # Mock SendGrid success
        mock_sendgrid_success = Mock()
        mock_sendgrid_success.status_code = 202

        mock_post.side_effect = [
            mock_gmass_fail,  # GMass attempt 1
            mock_gmass_fail,  # GMass attempt 2
            mock_gmass_fail,  # GMass attempt 3
            mock_sendgrid_success  # SendGrid fallback
        ]

        result = self.client.send_email(
            to_email="test@example.com",
            lead_id="lead123",
            template_type="initial_outreach",
            tier="HOT"
        )

        assert result == True
        assert mock_post.call_count == 4  # 3 GMass + 1 SendGrid

    @patch('utils.email_client.requests.post')
    def test_all_channels_fail_slack_notified(self, mock_post):
        """Test all channels fail, Slack notification sent."""
        # Mock all failures
        mock_fail = Mock()
        mock_fail.status_code = 500

        # Mock Slack success
        mock_slack_success = Mock()
        mock_slack_success.status_code = 200

        mock_post.side_effect = [
            mock_fail,  # GMass attempt 1
            mock_fail,  # GMass attempt 2
            mock_fail,  # GMass attempt 3
            mock_fail,  # SendGrid fallback
            mock_slack_success  # Slack notification
        ]

        result = self.client.send_email(
            to_email="test@example.com",
            lead_id="lead123",
            template_type="initial_outreach",
            tier="HOT"
        )

        assert result == False  # All email channels failed
        assert mock_post.call_count == 5  # 3 GMass + 1 SendGrid + 1 Slack


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
