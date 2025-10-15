"""Slack client for thread-based updates."""

import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging

logger = logging.getLogger(__name__)


class SlackClient:
    """Client for posting updates to Slack threads."""

    def __init__(self):
        self.token = os.getenv("SLACK_BOT_TOKEN")
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.client = WebClient(token=self.token) if self.token else None
        self.default_channel = os.getenv("SLACK_CHANNEL", "inbound-leads")

    def post_initial_message(
        self,
        lead_name: str,
        lead_email: str,
        tier: str,
        score: int,
        summary: str,
        channel: str = None
    ) -> tuple[str, str]:
        """Post initial lead notification and return (channel, thread_ts).

        Args:
            lead_name: Lead's name
            lead_email: Lead's email
            tier: Qualification tier
            score: Qualification score
            summary: Lead summary/reasoning
            channel: Slack channel (optional)

        Returns:
            Tuple of (channel_id, thread_ts) for future thread replies
        """
        channel = channel or self.default_channel

        # Determine emoji based on tier
        emoji_map = {
            "HOT": "🔥",
            "WARM": "🌤️",
            "COLD": "❄️",
            "UNQUALIFIED": "⚠️"
        }
        emoji = emoji_map.get(tier.upper(), "📋")

        message = f"""
{emoji} **New {tier} Lead: {lead_name}**

**Email:** {lead_email}
**Score:** {score}/100
**Tier:** {tier}

**Summary:**
{summary}

_Autonomous agent will begin follow-up sequence..._
"""

        try:
            if self.client:
                response = self.client.chat_postMessage(
                    channel=channel,
                    text=message,
                    mrkdwn=True
                )
                return response['channel'], response['ts']
            else:
                logger.warning("No Slack client configured")
                return None, None

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return None, None

    def post_thread_reply(
        self,
        channel: str,
        thread_ts: str,
        text: str
    ) -> bool:
        """Post a reply to an existing Slack thread.

        Args:
            channel: Channel ID
            thread_ts: Thread timestamp
            text: Message text

        Returns:
            True if successful
        """
        if not self.client or not thread_ts:
            logger.warning("Cannot post thread reply: missing client or thread_ts")
            return False

        try:
            self.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=text,
                mrkdwn=True
            )
            return True

        except SlackApiError as e:
            logger.error(f"Slack thread reply error: {e.response['error']}")
            return False
