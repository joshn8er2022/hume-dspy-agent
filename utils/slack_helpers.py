
"""Slack helper utilities."""
import httpx
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def get_channel_id(channel_name_or_id: str, slack_token: str) -> Optional[str]:
    """Convert channel name to ID, or return ID if already an ID.

    Args:
        channel_name_or_id: Channel name (e.g., 'ai-test') or ID (e.g., 'C09FZT6T1A5')
        slack_token: Slack bot token

    Returns:
        Channel ID or None if not found
    """
    # If it starts with C and is alphanumeric, it's already an ID
    if channel_name_or_id.startswith('C') and len(channel_name_or_id) == 11:
        return channel_name_or_id

    # Otherwise, look up the channel by name
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/conversations.list",
                headers={"Authorization": f"Bearer {slack_token}"},
                params={"types": "public_channel,private_channel"},
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    for channel in data.get('channels', []):
                        if channel.get('name') == channel_name_or_id:
                            logger.info(f"✅ Resolved channel '{channel_name_or_id}' to ID: {channel['id']}")
                            return channel['id']

                    logger.warning(f"⚠️ Channel '{channel_name_or_id}' not found")
                    return None
                else:
                    logger.error(f"❌ Slack API error: {data.get('error')}")
                    return None
    except Exception as e:
        logger.error(f"❌ Failed to resolve channel: {e}")
        return None
