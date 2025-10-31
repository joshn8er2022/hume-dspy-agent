"""Autonomous execution scheduler for lead follow-ups and monitoring."""
import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import httpx

logger = logging.getLogger(__name__)

# Initialize scheduler
# Lazy initialization - don't create during import (prevents blocking)
scheduler = None

def get_scheduler():
    """Get or create scheduler instance (lazy initialization)."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
        logger.info("✅ AsyncIOScheduler initialized (lazy)")
    return scheduler



async def check_leads_needing_followup():
    """Check for leads needing follow-up and trigger FollowUpAgent."""
    try:
        logger.info("🔄 Checking leads needing follow-up...")

        # Import here to avoid circular dependencies
        from config.settings import settings
        from supabase import create_client

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

        # Query leads needing follow-up:
        # - tier in [WARM, COOL, HOT, SCORCHING]
        # - last_follow_up_at is NULL OR > 24 hours ago
        # - follow_up_count < 3
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        result = supabase.table('leads').select('id, email, company, qualification_tier, follow_up_count, last_follow_up_at').in_(
            'qualification_tier', ['warm', 'cool', 'hot', 'scorching']
        ).lt('follow_up_count', 3).execute()

        leads_to_followup = [
            lead for lead in result.data
            if not lead.get('last_follow_up_at') or lead.get('last_follow_up_at') < cutoff_time
        ]

        logger.info(f"📊 Found {len(leads_to_followup)} leads needing follow-up")

        # Trigger FollowUpAgent for each lead (max 10 per run to avoid overload)
        for lead in leads_to_followup[:10]:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8000/agents/followup/a2a",
                        json={
                            "message": f"Autonomous follow-up for lead {lead['email']} (tier: {lead['qualification_tier']})"
                        },
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        logger.info(f"✅ Triggered follow-up for {lead['email']}")
                    else:
                        logger.error(f"❌ Follow-up trigger failed for {lead['email']}: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Failed to trigger follow-up for {lead['email']}: {e}")

        logger.info(f"✅ Follow-up check complete - triggered {min(len(leads_to_followup), 10)} follow-ups")

    except Exception as e:
        logger.error(f"❌ Follow-up check failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def autonomous_monitoring():
    """Monitor pipeline health and alert on anomalies."""
    try:
        logger.info("🔍 Running autonomous pipeline monitoring...")

        from config.settings import settings
        from supabase import create_client

        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

        # Get pipeline stats
        result = supabase.table('leads').select('qualification_tier').execute()

        total_leads = len(result.data)
        if total_leads == 0:
            logger.info("ℹ️ No leads to monitor")
            return

        # Count by tier
        tier_counts = {}
        for lead in result.data:
            tier = lead.get('qualification_tier', 'unknown')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        unqualified_count = tier_counts.get('unqualified', 0)
        unqualified_rate = unqualified_count / total_leads

        logger.info(f"📊 Pipeline stats: {total_leads} leads, {unqualified_rate:.1%} unqualified")

        # Detect anomalies
        if unqualified_rate > 0.9:
            # Send Slack alert
            alert_message = f"🚨 CRITICAL: {unqualified_rate:.1%} of leads are UNQUALIFIED ({unqualified_count}/{total_leads})"
            logger.warning(alert_message)

            # Send to Slack
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
                        json={
                            "channel": settings.SLACK_CHANNEL_INBOUND,
                            "text": alert_message
                        },
                        timeout=10.0
                    )
                logger.info("✅ Anomaly alert sent to Slack")
            except Exception as e:
                logger.error(f"❌ Failed to send Slack alert: {e}")

        logger.info("✅ Monitoring complete")

    except Exception as e:
        logger.error(f"❌ Monitoring failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


def start_scheduler():
    """Start the autonomous execution scheduler."""
    logger.info("🚀 Starting autonomous execution scheduler...")

    # Schedule follow-up checks every hour
    scheduler.add_job(
        check_leads_needing_followup,
        trigger=IntervalTrigger(hours=1),
        id='followup_check',
        name='Check leads needing follow-up',
        replace_existing=True
    )

    # Schedule monitoring every hour
    scheduler.add_job(
        autonomous_monitoring,
        trigger=IntervalTrigger(hours=1),
        id='pipeline_monitoring',
        name='Monitor pipeline health',
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Scheduler started - autonomous execution enabled")
    logger.info("   - Follow-up checks: Every 1 hour")
    logger.info("   - Pipeline monitoring: Every 1 hour")


def stop_scheduler():
    """Stop the autonomous execution scheduler."""
    logger.info("🛑 Stopping autonomous execution scheduler...")
    scheduler.shutdown()
    logger.info("✅ Scheduler stopped")

async def run_performance_monitoring():
    """Run PerformanceAgent to monitor system performance."""
    try:
        logger.info("🔄 Running PerformanceAgent monitoring...")
        
        from agents.performance_agent import PerformanceAgent
        
        # Initialize PerformanceAgent
        performance_agent = PerformanceAgent()
        
        # Run monitoring workflow
        result = await performance_agent.monitor_system()
        
        logger.info(f"✅ PerformanceAgent monitoring complete: {result.get('status')}")
        
    except Exception as e:
        logger.error(f"❌ PerformanceAgent monitoring failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

