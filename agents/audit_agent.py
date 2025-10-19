"""Audit Agent - Actually pulls real data for audits.

This agent:
- Queries Supabase for lead data
- Pulls GMass campaign metrics via API
- Provides REAL data, never hallucinates
- Returns structured audit reports

NOT a conversational agent - it's a data retrieval agent.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class AuditAgent:
    """Agent that performs real data audits - no hallucinations, just facts."""
    
    def __init__(self):
        # Initialize Supabase
        self.supabase: Optional[Client] = None
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("✅ Audit Agent: Supabase connected")
            else:
                logger.warning("⚠️ Audit Agent: No Supabase credentials")
        except Exception as e:
            logger.error(f"❌ Audit Agent Supabase init failed: {e}")
        
        # Initialize GMass API
        self.gmass_api_key = os.getenv("GMASS_API_KEY")
        if self.gmass_api_key:
            logger.info("✅ Audit Agent: GMass API configured")
        else:
            logger.warning("⚠️ Audit Agent: No GMass API key")
    
    async def audit_lead_flow(
        self,
        timeframe_hours: int = 24
    ) -> Dict[str, Any]:
        """Perform full lead flow audit with REAL data.
        
        Returns actual data from:
        - Supabase (leads, qualification scores, timing)
        - GMass (email deliverability, opens, clicks, responses)
        
        Args:
            timeframe_hours: How many hours back to audit (default 24)
        
        Returns:
            Dictionary with audit results (REAL data only)
        """
        audit_results = {
            "timeframe": f"Last {timeframe_hours} hours",
            "timestamp": datetime.utcnow().isoformat(),
            "data_sources": [],
            "leads": {},
            "emails": {},
            "errors": []
        }
        
        # 1. Get lead data from Supabase
        if self.supabase:
            try:
                leads_data = await self._get_leads_from_supabase(timeframe_hours)
                audit_results["leads"] = leads_data
                audit_results["data_sources"].append("Supabase")
            except Exception as e:
                error_msg = f"Supabase query failed: {str(e)}"
                logger.error(error_msg)
                audit_results["errors"].append(error_msg)
        else:
            audit_results["errors"].append("Supabase not configured")
        
        # 2. Get email campaign data from GMass
        if self.gmass_api_key:
            try:
                email_data = await self._get_email_data_from_gmass(timeframe_hours)
                audit_results["emails"] = email_data
                audit_results["data_sources"].append("GMass")
            except Exception as e:
                error_msg = f"GMass API failed: {str(e)}"
                logger.error(error_msg)
                audit_results["errors"].append(error_msg)
        else:
            audit_results["errors"].append("GMass API not configured")
        
        return audit_results
    
    async def _get_leads_from_supabase(self, hours: int) -> Dict[str, Any]:
        """Query Supabase for lead data."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        try:
            # Query all leads in timeframe
            response = self.supabase.table('leads').select(
                'id, email, first_name, last_name, company, qualification_tier, qualification_score, '
                'status, created_at, submitted_at'
            ).gte('created_at', cutoff_time.isoformat()).execute()
            
            leads = response.data
            
            # Count by tier
            tier_counts = {}
            for lead in leads:
                tier = lead.get('qualification_tier', 'UNQUALIFIED')
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            # Calculate speed to lead (time from submission to creation in our system)
            speed_to_lead_times = []
            for lead in leads:
                if lead.get('submitted_at') and lead.get('created_at'):
                    submitted = datetime.fromisoformat(lead['submitted_at'].replace('Z', '+00:00'))
                    created = datetime.fromisoformat(lead['created_at'].replace('Z', '+00:00'))
                    diff_seconds = (created - submitted).total_seconds()
                    speed_to_lead_times.append(diff_seconds)
            
            avg_speed_to_lead = (
                sum(speed_to_lead_times) / len(speed_to_lead_times)
                if speed_to_lead_times else 0
            )
            
            return {
                "total_leads": len(leads),
                "tier_distribution": tier_counts,
                "average_speed_to_lead_seconds": round(avg_speed_to_lead, 2),
                "average_qualification_score": round(
                    sum(l.get('qualification_score', 0) for l in leads) / len(leads)
                    if leads else 0,
                    2
                ),
                "leads_detail": [
                    {
                        "name": f"{l.get('first_name', 'Unknown')} {l.get('last_name', '')}".strip(),
                        "email": l.get('email'),
                        "company": l.get('company'),
                        "tier": l.get('qualification_tier'),
                        "score": l.get('qualification_score'),
                        "status": l.get('status'),
                        "created_at": l.get('created_at')
                    }
                    for l in leads
                ]
            }
        
        except Exception as e:
            logger.error(f"Supabase lead query error: {e}")
            raise
    
    async def _get_email_data_from_gmass(self, hours: int) -> Dict[str, Any]:
        """Query GMass API for campaign data."""
        try:
            async with httpx.AsyncClient() as client:
                # Get recent campaigns
                response = await client.get(
                    "https://api.gmass.co/api/campaigns",
                    headers={"X-apikey": self.gmass_api_key},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"GMass API returned {response.status_code}: {response.text}")
                
                campaigns = response.json()
                
                # Filter to recent campaigns (within timeframe)
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                recent_campaigns = []
                
                for campaign in campaigns:
                    # GMass returns creationTime in format like "2019-08-24T14:15:22Z"
                    creation_time_str = campaign.get('creationTime', '')
                    if creation_time_str:
                        try:
                            creation_time = datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
                            if creation_time >= cutoff_time:
                                recent_campaigns.append(campaign)
                        except:
                            # If no valid creationTime, include campaign anyway (better to have data)
                            recent_campaigns.append(campaign)
                    else:
                        # If no creationTime field, include campaign (better to have data)
                        recent_campaigns.append(campaign)
                
                # Calculate aggregate metrics from statistics object
                # GMass nests stats in a 'statistics' object per campaign
                total_recipients = sum(c.get('statistics', {}).get('recipients', 0) for c in recent_campaigns)
                total_opens = sum(c.get('statistics', {}).get('opens', 0) for c in recent_campaigns)
                total_clicks = sum(c.get('statistics', {}).get('clicks', 0) for c in recent_campaigns)
                total_replies = sum(c.get('statistics', {}).get('replies', 0) for c in recent_campaigns)
                total_bounces = sum(c.get('statistics', {}).get('bounces', 0) for c in recent_campaigns)
                total_blocks = sum(c.get('statistics', {}).get('blocks', 0) for c in recent_campaigns)
                
                # Calculate delivered as recipients minus bounces and blocks
                total_delivered = total_recipients - total_bounces - total_blocks
                
                return {
                    "total_campaigns": len(recent_campaigns),
                    "total_emails_sent": total_recipients,
                    "deliverability_rate": round(
                        (total_delivered / total_recipients * 100) if total_recipients > 0 else 0,
                        2
                    ),
                    "open_rate": round(
                        (total_opens / total_delivered * 100) if total_delivered > 0 else 0,
                        2
                    ),
                    "click_rate": round(
                        (total_clicks / total_delivered * 100) if total_delivered > 0 else 0,
                        2
                    ),
                    "reply_rate": round(
                        (total_replies / total_delivered * 100) if total_delivered > 0 else 0,
                        2
                    ),
                    "bounce_rate": round(
                        (total_bounces / total_recipients * 100) if total_recipients > 0 else 0,
                        2
                    ),
                    "campaigns_detail": [
                        {
                            "campaign_id": c.get('campaignId'),
                            "name": c.get('friendlyName', c.get('subject')),
                            "sent": c.get('statistics', {}).get('recipients', 0),
                            "delivered": c.get('statistics', {}).get('recipients', 0) - c.get('statistics', {}).get('bounces', 0) - c.get('statistics', {}).get('blocks', 0),
                            "opens": c.get('statistics', {}).get('opens', 0),
                            "clicks": c.get('statistics', {}).get('clicks', 0),
                            "replies": c.get('statistics', {}).get('replies', 0),
                            "bounces": c.get('statistics', {}).get('bounces', 0),
                            "blocks": c.get('statistics', {}).get('blocks', 0),
                            "unsubscribes": c.get('statistics', {}).get('unsubscribes', 0),
                            "creation_time": c.get('creationTime'),
                            "status": c.get('status'),
                            "stage": c.get('stage')
                        }
                        for c in recent_campaigns
                    ]
                }
        
        except Exception as e:
            logger.error(f"GMass API query error: {e}")
            raise
    
    def format_audit_report(self, audit_data: Dict[str, Any]) -> str:
        """Format audit data into readable report.
        
        Args:
            audit_data: Raw audit data from audit_lead_flow()
        
        Returns:
            Formatted markdown report
        """
        report = f"""# 📊 Lead Flow Audit Report

**Timeframe**: {audit_data['timeframe']}
**Generated**: {audit_data['timestamp']}
**Data Sources**: {', '.join(audit_data['data_sources'])}

---

## 🎯 Lead Pipeline Metrics

"""
        
        # Leads section
        if audit_data.get('leads'):
            leads = audit_data['leads']
            report += f"""### Lead Volume & Quality
- **Total Leads**: {leads.get('total_leads', 0)}
- **Average Qualification Score**: {leads.get('average_qualification_score', 0)}/100
- **Speed to Lead**: {leads.get('average_speed_to_lead_seconds', 0)}s

### Tier Distribution
"""
            for tier, count in leads.get('tier_distribution', {}).items():
                report += f"- **{tier}**: {count} leads\n"
            
            report += "\n### Lead Details (Real Names)\n\n"
            for lead in leads.get('leads_detail', [])[:10]:  # Show first 10
                report += f"- **{lead['name']}** ({lead['email']})\n"
                report += f"  - Company: {lead.get('company', 'N/A')}\n"
                report += f"  - Tier: {lead.get('tier', 'N/A')} | Score: {lead.get('score', 'N/A')}\n"
                report += f"  - Status: {lead.get('status', 'N/A')}\n\n"
        
        # Emails section
        if audit_data.get('emails'):
            emails = audit_data['emails']
            report += f"""
---

## 📧 Email Campaign Performance

### Aggregate Metrics
- **Total Campaigns**: {emails.get('total_campaigns', 0)}
- **Total Emails Sent**: {emails.get('total_emails_sent', 0)}

### Deliverability
- **Delivery Rate**: {emails.get('deliverability_rate', 0)}%
- **Bounce Rate**: {emails.get('bounce_rate', 0)}%

### Engagement
- **Open Rate**: {emails.get('open_rate', 0)}%
- **Click Rate**: {emails.get('click_rate', 0)}%
- **Reply Rate**: {emails.get('reply_rate', 0)}%

### Recent Campaigns
"""
            for campaign in emails.get('campaigns_detail', [])[:5]:  # Show first 5
                report += f"\n**{campaign['name']}** (ID: {campaign['campaign_id']})\n"
                report += f"- Sent: {campaign['sent']} | Delivered: {campaign['delivered']}\n"
                report += f"- Opened: {campaign['opened']} | Clicked: {campaign['clicked']}\n"
                report += f"- Replied: {campaign['replied']} | Bounced: {campaign['bounced']}\n"
        
        # Errors section
        if audit_data.get('errors'):
            report += "\n---\n\n## ⚠️ Errors Encountered\n\n"
            for error in audit_data['errors']:
                report += f"- {error}\n"
        
        report += "\n---\n\n**Note**: This is REAL data pulled from live systems. No hallucinations."
        
        return report


# Singleton instance
_audit_agent = None

def get_audit_agent() -> AuditAgent:
    """Get or create the global AuditAgent instance."""
    global _audit_agent
    if _audit_agent is None:
        _audit_agent = AuditAgent()
    return _audit_agent
