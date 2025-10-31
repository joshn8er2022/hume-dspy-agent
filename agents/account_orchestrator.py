"""
AccountOrchestrator Agent - Multi-Contact ABM Campaign Management

Handles autonomous multi-contact campaigns with:
- Colleague messaging ("Sue, your colleague Dr. XYZ inquired...")
- Conflict detection (prevent messaging if primary responded)
- Channel escalation (Email → SMS → Call)
- Autonomous scheduling and trigger logic
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from agents.base_agent import SelfOptimizingAgent, AgentRules
from enum import Enum
import json

logger = logging.getLogger(__name__)


class CampaignChannel(Enum):
    """Communication channels for campaign touchpoints"""
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    LINKEDIN = "linkedin"


class CampaignStatus(Enum):
    """Campaign execution status"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ContactRole(Enum):
    """Contact role in account"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


class AccountOrchestrator(SelfOptimizingAgent):
    """
    Orchestrates multi-contact ABM campaigns with autonomous decision-making.
    
    Key Features:
    - Multi-contact coordination across account
    - Conflict detection and prevention
    - Channel escalation logic
    - Autonomous scheduling
    - Colleague reference messaging
    """
    
    def __init__(self, supabase_client=None, config: Optional[Dict] = None):
        # Define agent rules for SelfOptimizingAgent
        rules = AgentRules(
            allowed_models=["llama-3.1-70b", "mixtral-8x7b"],
            default_model="llama-3.1-70b",
            allowed_tools=["supabase", "email", "orchestration"],
            requires_approval=False,  # Auto-approve (low cost)
            max_cost_per_request=0.10,
            optimizer="bootstrap",  # BootstrapFewShot
            auto_optimize_threshold=0.80,
            department="Sales"
        )
        
        # Initialize base class
        super().__init__(agent_name="AccountOrchestrator", rules=rules)
        
        """
        Initialize AccountOrchestrator.
        
        Args:
            supabase_client: Supabase client for data persistence
            config: Configuration dictionary with campaign parameters
        """
        self.supabase = supabase_client
        self.config = config or self._default_config()
        self.active_campaigns: Dict[str, Dict] = {}
        
        logger.info("AccountOrchestrator initialized")
    
    def _default_config(self) -> Dict:
        """Default campaign configuration"""
        return {
            "max_touchpoints": 7,
            "touchpoint_intervals": [2, 3, 5, 7, 10, 14],  # Days between touchpoints
            "channel_escalation": [CampaignChannel.EMAIL, CampaignChannel.SMS, CampaignChannel.CALL],
            "colleague_message_delay": 3,  # Days after primary contact
            "response_timeout": 48,  # Hours to wait for response
            "max_concurrent_contacts": 3,  # Max contacts to engage simultaneously
            "conflict_check_enabled": True,
            "auto_pause_on_response": True,
        }
    
    async def process_new_lead(self, lead_data: Dict) -> Dict:
        """
        Initiate ABM campaign for new lead/account.
        
        Args:
            lead_data: Lead information including account contacts
            
        Returns:
            Campaign initialization result
        """
        try:
            account_id = lead_data.get("account_id")
            if not account_id:
                raise ValueError("account_id required in lead_data")
            
            # Extract contacts from account
            contacts = self._extract_contacts(lead_data)
            if not contacts:
                raise ValueError("No contacts found in lead_data")
            
            # Prioritize contacts
            prioritized_contacts = self._prioritize_contacts(contacts)
            
            # Create campaign structure
            campaign = {
                "campaign_id": f"camp_{account_id}_{datetime.utcnow().timestamp()}",
                "account_id": account_id,
                "status": CampaignStatus.ACTIVE.value,
                "contacts": prioritized_contacts,
                "current_step": 0,
                "touchpoints": [],
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
                "metadata": lead_data.get("metadata", {})
            }
            
            # Store campaign
            self.active_campaigns[campaign["campaign_id"]] = campaign
            
            # Persist to database
            if self.supabase:
                await self._persist_campaign(campaign)
            
            # Schedule first touchpoint
            first_touchpoint = await self.schedule_next_touchpoint(
                campaign["campaign_id"],
                immediate=True
            )
            
            logger.info(f"Campaign initiated: {campaign['campaign_id']} with {len(contacts)} contacts")
            
            return {
                "success": True,
                "campaign_id": campaign["campaign_id"],
                "contacts_count": len(contacts),
                "first_touchpoint": first_touchpoint
            }
            
        except Exception as e:
            logger.error(f"Error processing new lead: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_contacts(self, lead_data: Dict) -> List[Dict]:
        """Extract and validate contacts from lead data"""
        contacts = []
        
        # Primary contact
        if lead_data.get("email"):
            contacts.append({
                "contact_id": lead_data.get("id") or f"contact_{len(contacts)}",
                "name": lead_data.get("name", "Unknown"),
                "email": lead_data["email"],
                "phone": lead_data.get("phone"),
                "title": lead_data.get("title"),
                "role": ContactRole.PRIMARY.value,
                "priority": 1
            })
        
        # Additional contacts from account
        additional = lead_data.get("account_contacts", [])
        for idx, contact in enumerate(additional):
            if contact.get("email"):
                contacts.append({
                    "contact_id": contact.get("id") or f"contact_{len(contacts)}",
                    "name": contact.get("name", "Unknown"),
                    "email": contact["email"],
                    "phone": contact.get("phone"),
                    "title": contact.get("title"),
                    "role": ContactRole.SECONDARY.value if idx == 0 else ContactRole.TERTIARY.value,
                    "priority": idx + 2
                })
        
        return contacts
    
    def _prioritize_contacts(self, contacts: List[Dict]) -> List[Dict]:
        """
        Prioritize contacts based on title, role, and engagement potential.
        
        Priority factors:
        - Decision-making authority (C-level, VP, Director)
        - Role relevance to product
        - Previous engagement history
        """
        # Title scoring
        title_scores = {
            "ceo": 100, "chief executive": 100,
            "cto": 95, "chief technology": 95,
            "cio": 95, "chief information": 95,
            "vp": 80, "vice president": 80,
            "director": 70,
            "manager": 50,
            "lead": 40,
        }
        
        for contact in contacts:
            title = (contact.get("title") or "").lower()
            score = 0
            
            for keyword, points in title_scores.items():
                if keyword in title:
                    score = max(score, points)
            
            contact["priority_score"] = score
        
        # Sort by priority score (descending)
        return sorted(contacts, key=lambda x: x.get("priority_score", 0), reverse=True)
    
    async def execute_campaign_step(self, campaign_id: str) -> Dict:
        """
        Execute next step in campaign workflow.
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            Execution result with next actions
        """
        try:
            campaign = self.active_campaigns.get(campaign_id)
            if not campaign:
                # Try loading from database
                campaign = await self._load_campaign(campaign_id)
                if not campaign:
                    raise ValueError(f"Campaign not found: {campaign_id}")
            
            # Check if campaign is active
            if campaign["status"] != CampaignStatus.ACTIVE.value:
                return {
                    "success": False,
                    "error": f"Campaign not active: {campaign['status']}"
                }
            
            # Check for conflicts (primary responded)
            if self.config["conflict_check_enabled"]:
                conflict = await self.check_conflicts(campaign_id)
                if conflict["has_conflict"]:
                    return await self._handle_conflict(campaign_id, conflict)
            
            # Determine next contact and channel
            next_contact = self._select_next_contact(campaign)
            channel = self.select_channel(campaign, next_contact)
            
            # Generate message
            message = await self.generate_message(
                campaign,
                next_contact,
                channel
            )
            
            # Execute touchpoint
            result = await self._execute_touchpoint(
                campaign_id,
                next_contact,
                channel,
                message
            )
            
            # Update campaign state
            campaign["current_step"] += 1
            campaign["last_updated"] = datetime.utcnow().isoformat()
            
            # Schedule next touchpoint
            if campaign["current_step"] < self.config["max_touchpoints"]:
                next_touchpoint = await self.schedule_next_touchpoint(campaign_id)
            else:
                campaign["status"] = CampaignStatus.COMPLETED.value
                next_touchpoint = None
            
            # Persist updates
            if self.supabase:
                await self._persist_campaign(campaign)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "step": campaign["current_step"],
                "contact": next_contact["name"],
                "channel": channel.value,
                "next_touchpoint": next_touchpoint
            }
            
        except Exception as e:
            logger.error(f"Error executing campaign step: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _select_next_contact(self, campaign: Dict) -> Dict:
        """
        Select next contact to engage based on campaign state.
        
        Logic:
        - Start with highest priority contact
        - Move to secondary contacts after primary engagement
        - Respect max_concurrent_contacts limit
        """
        contacts = campaign["contacts"]
        touchpoints = campaign.get("touchpoints", [])
        current_step = campaign["current_step"]
        
        # Get contacts already engaged
        engaged_contacts = set(tp["contact_id"] for tp in touchpoints)
        
        # Primary contact for first few touchpoints
        if current_step < 3:
            return contacts[0]  # Highest priority
        
        # Introduce secondary contacts
        for contact in contacts:
            if contact["contact_id"] not in engaged_contacts:
                return contact
        
        # Cycle back to primary if all engaged
        return contacts[0]
    
    def select_channel(self, campaign: Dict, contact: Dict) -> CampaignChannel:
        """
        Select communication channel based on escalation logic.
        
        Escalation path: Email → SMS → Call
        
        Args:
            campaign: Campaign data
            contact: Contact to reach
            
        Returns:
            Selected channel
        """
        touchpoints = campaign.get("touchpoints", [])
        contact_touchpoints = [
            tp for tp in touchpoints 
            if tp["contact_id"] == contact["contact_id"]
        ]
        
        # Count attempts per channel
        channel_attempts = {}
        for tp in contact_touchpoints:
            channel = tp.get("channel")
            channel_attempts[channel] = channel_attempts.get(channel, 0) + 1
        
        # Escalation logic
        escalation_path = self.config["channel_escalation"]
        
        for channel in escalation_path:
            attempts = channel_attempts.get(channel.value, 0)
            
            # Try each channel up to 2 times before escalating
            if attempts < 2:
                # Verify contact has this channel available
                if self._has_channel(contact, channel):
                    return channel
        
        # Default to email if all channels exhausted
        return CampaignChannel.EMAIL
    
    def _has_channel(self, contact: Dict, channel: CampaignChannel) -> bool:
        """Check if contact has the specified channel available"""
        if channel == CampaignChannel.EMAIL:
            return bool(contact.get("email"))
        elif channel == CampaignChannel.SMS or channel == CampaignChannel.CALL:
            return bool(contact.get("phone"))
        elif channel == CampaignChannel.LINKEDIN:
            return bool(contact.get("linkedin_url"))
        return False
    
    async def generate_colleague_message(self, 
                                        campaign: Dict,
                                        target_contact: Dict,
                                        referring_contact: Dict) -> str:
        """
        Generate "Sue, your colleague Dr. XYZ inquired..." style message.
        
        Args:
            campaign: Campaign data
            target_contact: Contact receiving the message
            referring_contact: Contact who previously engaged
            
        Returns:
            Personalized colleague reference message
        """
        try:
            # Extract names
            target_name = target_contact.get("name", "there").split()[0]
            referring_name = referring_contact.get("name", "your colleague")
            referring_title = referring_contact.get("title", "")
            
            # Get account context
            account_name = campaign.get("metadata", {}).get("company_name", "your organization")
            
            # Find what the referring contact engaged with
            touchpoints = campaign.get("touchpoints", [])
            referring_touchpoints = [
                tp for tp in touchpoints
                if tp["contact_id"] == referring_contact["contact_id"]
            ]
            
            engagement_context = ""
            if referring_touchpoints:
                last_tp = referring_touchpoints[-1]
                engagement_context = f"recently inquired about {last_tp.get('topic', 'our solution')}"
            else:
                engagement_context = "expressed interest in our solution"
            
            # Generate message variants
            templates = [
                f"Hi {target_name},\n\nI noticed {referring_name} ({referring_title}) {engagement_context}. Given your role at {account_name}, I thought you might also find this relevant.\n\n",
                f"{target_name},\n\nYour colleague {referring_name} {engagement_context}. I wanted to reach out to you as well since this could benefit your team at {account_name}.\n\n",
                f"Hello {target_name},\n\n{referring_name} from your team {engagement_context}. I'm following up to see if this might be valuable for your work at {account_name} as well.\n\n"
            ]
            
            # Select template based on campaign step
            template_idx = campaign["current_step"] % len(templates)
            message = templates[template_idx]
            
            logger.info(f"Generated colleague message for {target_name} referencing {referring_name}")
            
            return message
            
        except Exception as e:
            logger.error(f"Error generating colleague message: {str(e)}")
            return f"Hi {target_contact.get('name', 'there')},\n\n"
    
    async def generate_message(self,
                              campaign: Dict,
                              contact: Dict,
                              channel: CampaignChannel) -> str:
        """
        Generate personalized message for contact.
        
        Args:
            campaign: Campaign data
            contact: Target contact
            channel: Communication channel
            
        Returns:
            Personalized message content
        """
        # Check if this is a colleague reference scenario
        touchpoints = campaign.get("touchpoints", [])
        if len(touchpoints) > 0 and contact["role"] != ContactRole.PRIMARY.value:
            # Find primary contact
            primary = next(
                (c for c in campaign["contacts"] if c["role"] == ContactRole.PRIMARY.value),
                None
            )
            if primary:
                return await self.generate_colleague_message(campaign, contact, primary)
        
        # Standard message generation
        name = contact.get("name", "there").split()[0]
        company = campaign.get("metadata", {}).get("company_name", "your organization")
        
        # Channel-specific formatting
        if channel == CampaignChannel.SMS:
            return f"Hi {name}, following up on our solution for {company}. Quick question - would you be open to a brief call this week?"
        elif channel == CampaignChannel.EMAIL:
            return f"Hi {name},\n\nI wanted to reach out regarding how we can help {company} with [specific value proposition].\n\nWould you be available for a brief conversation this week?\n\nBest regards"
        else:
            return f"Hi {name}, reaching out about {company}."
    
    async def check_conflicts(self, campaign_id: str) -> Dict:
        """
        Check for conflicts that should pause campaign.
        
        Conflicts:
        - Primary contact responded
        - Meeting scheduled
        - Unsubscribe request
        - Negative sentiment detected
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            Conflict detection result
        """
        try:
            campaign = self.active_campaigns.get(campaign_id)
            if not campaign:
                return {"has_conflict": False, "reason": "Campaign not found"}
            
            conflicts = []
            
            # Check for primary contact response
            primary_contact = next(
                (c for c in campaign["contacts"] if c["role"] == ContactRole.PRIMARY.value),
                None
            )
            
            if primary_contact and self.supabase:
                # Query for responses from primary contact
                response = await self._check_contact_response(primary_contact["contact_id"])
                if response:
                    conflicts.append({
                        "type": "primary_responded",
                        "contact": primary_contact["name"],
                        "timestamp": response.get("timestamp")
                    })
            
            # Check for meeting scheduled
            if campaign.get("metadata", {}).get("meeting_scheduled"):
                conflicts.append({
                    "type": "meeting_scheduled",
                    "timestamp": campaign["metadata"].get("meeting_time")
                })
            
            # Check for unsubscribe
            for contact in campaign["contacts"]:
                if contact.get("unsubscribed"):
                    conflicts.append({
                        "type": "unsubscribed",
                        "contact": contact["name"]
                    })
            
            return {
                "has_conflict": len(conflicts) > 0,
                "conflicts": conflicts,
                "should_pause": len(conflicts) > 0 and self.config["auto_pause_on_response"]
            }
            
        except Exception as e:
            logger.error(f"Error checking conflicts: {str(e)}")
            return {
                "has_conflict": False,
                "error": str(e)
            }
    
    async def _handle_conflict(self, campaign_id: str, conflict: Dict) -> Dict:
        """Handle detected conflict by pausing or adjusting campaign"""
        campaign = self.active_campaigns.get(campaign_id)
        
        if conflict.get("should_pause"):
            campaign["status"] = CampaignStatus.PAUSED.value
            campaign["pause_reason"] = conflict["conflicts"][0]["type"]
            
            if self.supabase:
                await self._persist_campaign(campaign)
            
            logger.info(f"Campaign {campaign_id} paused due to: {campaign['pause_reason']}")
        
        return {
            "success": True,
            "action": "paused",
            "reason": conflict["conflicts"][0]["type"],
            "conflicts": conflict["conflicts"]
        }
    
    async def schedule_next_touchpoint(self, 
                                      campaign_id: str,
                                      immediate: bool = False) -> Optional[Dict]:
        """
        Schedule next touchpoint with autonomous trigger logic.
        
        Args:
            campaign_id: Campaign identifier
            immediate: Execute immediately vs scheduled
            
        Returns:
            Scheduled touchpoint details
        """
        try:
            campaign = self.active_campaigns.get(campaign_id)
            if not campaign:
                return None
            
            current_step = campaign["current_step"]
            
            # Determine delay
            if immediate:
                delay_days = 0
            else:
                intervals = self.config["touchpoint_intervals"]
                delay_days = intervals[min(current_step, len(intervals) - 1)]
            
            scheduled_time = datetime.utcnow() + timedelta(days=delay_days)
            
            touchpoint = {
                "touchpoint_id": f"tp_{campaign_id}_{current_step}",
                "campaign_id": campaign_id,
                "scheduled_time": scheduled_time.isoformat(),
                "step": current_step,
                "status": "scheduled"
            }
            
            # Store in campaign
            if "scheduled_touchpoints" not in campaign:
                campaign["scheduled_touchpoints"] = []
            campaign["scheduled_touchpoints"].append(touchpoint)
            
            # Persist
            if self.supabase:
                await self._persist_touchpoint(touchpoint)
            
            logger.info(f"Scheduled touchpoint {touchpoint['touchpoint_id']} for {scheduled_time}")
            
            return touchpoint
            
        except Exception as e:
            logger.error(f"Error scheduling touchpoint: {str(e)}")
            return None
    
    async def _execute_touchpoint(self,
                                 campaign_id: str,
                                 contact: Dict,
                                 channel: CampaignChannel,
                                 message: str) -> Dict:
        """Execute actual touchpoint (send message)"""
        touchpoint = {
            "touchpoint_id": f"tp_{campaign_id}_{datetime.utcnow().timestamp()}",
            "campaign_id": campaign_id,
            "contact_id": contact["contact_id"],
            "contact_name": contact["name"],
            "channel": channel.value,
            "message": message,
            "executed_at": datetime.utcnow().isoformat(),
            "status": "sent"
        }
        
        # Add to campaign touchpoints
        campaign = self.active_campaigns[campaign_id]
        if "touchpoints" not in campaign:
            campaign["touchpoints"] = []
        campaign["touchpoints"].append(touchpoint)
        
        # Persist
        if self.supabase:
            await self._persist_touchpoint(touchpoint)
        
        logger.info(f"Executed touchpoint: {touchpoint['touchpoint_id']} via {channel.value}")
        
        return touchpoint
    
    async def _persist_campaign(self, campaign: Dict):
        """Persist campaign to database"""
        if not self.supabase:
            return
        
        try:
            # Upsert campaign
            self.supabase.table("campaigns").upsert(campaign).execute()
        except Exception as e:
            logger.error(f"Error persisting campaign: {str(e)}")
    
    async def _persist_touchpoint(self, touchpoint: Dict):
        """Persist touchpoint to database"""
        if not self.supabase:
            return
        
        try:
            self.supabase.table("touchpoints").insert(touchpoint).execute()
        except Exception as e:
            logger.error(f"Error persisting touchpoint: {str(e)}")
    
    async def _load_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Load campaign from database"""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table("campaigns").select("*").eq("campaign_id", campaign_id).execute()
            if result.data:
                campaign = result.data[0]
                self.active_campaigns[campaign_id] = campaign
                return campaign
        except Exception as e:
            logger.error(f"Error loading campaign: {str(e)}")
        
        return None
    
    async def _check_contact_response(self, contact_id: str) -> Optional[Dict]:
        """Check if contact has responded"""
        if not self.supabase:
            return None
        
        try:
            # Query responses table
            result = self.supabase.table("responses").select("*").eq("contact_id", contact_id).order("timestamp", desc=True).limit(1).execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.error(f"Error checking contact response: {str(e)}")
        
        return None
    
    def get_campaign_status(self, campaign_id: str) -> Optional[Dict]:
        """Get current campaign status and metrics"""
        campaign = self.active_campaigns.get(campaign_id)
        if not campaign:
            return None
        
        touchpoints = campaign.get("touchpoints", [])
        
        return {
            "campaign_id": campaign_id,
            "status": campaign["status"],
            "current_step": campaign["current_step"],
            "total_touchpoints": len(touchpoints),
            "contacts_engaged": len(set(tp["contact_id"] for tp in touchpoints)),
            "channels_used": list(set(tp["channel"] for tp in touchpoints)),
            "created_at": campaign["created_at"],
            "last_updated": campaign["last_updated"]
        }
