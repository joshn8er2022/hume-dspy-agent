"""
Company Graph Module

Provides high-level queries for Account-Based Marketing:
- Account overview with all contacts and relationships
- Expansion target discovery (colleagues of engaged contacts)
- Conversation context aggregation for personalized messaging
- Relationship mapping and network analysis
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from core.abm_data import (
    CompanyRepository,
    ContactRepository,
    RelationshipRepository,
    ConversationRepository,
    TouchpointRepository,
    Company,
    Contact,
    Relationship,
    Conversation
)


class CompanyGraph:
    """High-level company graph queries for ABM"""

    def __init__(self):
        self.company_repo = CompanyRepository()
        self.contact_repo = ContactRepository()
        self.relationship_repo = RelationshipRepository()
        self.conversation_repo = ConversationRepository()
        self.touchpoint_repo = TouchpointRepository()

    async def get_account_overview(self, company_id: str) -> Dict[str, Any]:
        """
        Get complete account overview including:
        - Company information
        - All contacts with roles and engagement
        - Relationships between contacts
        - Active conversations
        - Recent touchpoints
        
        Returns comprehensive account data for ABM orchestration.
        """
        # Get company
        company = await self.company_repo.get_company_by_id(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Get all contacts
        contacts = await self.contact_repo.find_contacts_by_company(company_id)

        # Get relationships
        all_relationships = []
        for contact in contacts:
            rels = await self.relationship_repo.get_contact_relationships(contact.id)
            all_relationships.extend(rels)

        # Deduplicate relationships
        unique_relationships = {}
        for rel in all_relationships:
            key = tuple(sorted([rel.contact_id_1, rel.contact_id_2]))
            if key not in unique_relationships:
                unique_relationships[key] = rel

        # Get active conversations
        active_conversations = await self.conversation_repo.get_active_conversations(company_id)

        # Get all conversations for context
        all_conversations = await self.conversation_repo.get_conversations_by_company(company_id)

        # Build contact map with engagement data
        contact_map = {}
        for contact in contacts:
            contact_convs = [c for c in all_conversations if c.contact_id == contact.id]
            
            contact_map[contact.id] = {
                'contact': contact,
                'conversations': contact_convs,
                'total_conversations': len(contact_convs),
                'active_conversations': len([c for c in contact_convs if c.status == 'active']),
                'engagement_score': contact.engagement_score,
                'last_engaged_at': contact.last_engaged_at
            }

        # Build relationship network
        relationship_network = []
        for rel in unique_relationships.values():
            contact1 = contact_map.get(rel.contact_id_1, {}).get('contact')
            contact2 = contact_map.get(rel.contact_id_2, {}).get('contact')
            
            if contact1 and contact2:
                relationship_network.append({
                    'relationship': rel,
                    'contact1': {
                        'id': contact1.id,
                        'name': contact1.full_name,
                        'title': contact1.title,
                        'role': contact1.role
                    },
                    'contact2': {
                        'id': contact2.id,
                        'name': contact2.full_name,
                        'title': contact2.title,
                        'role': contact2.role
                    },
                    'type': rel.relationship_type,
                    'strength': rel.strength
                })

        return {
            'company': {
                'id': company.id,
                'name': company.name,
                'domain': company.domain,
                'industry': company.industry,
                'size': company.size,
                'account_tier': company.account_tier,
                'account_status': company.account_status,
                'research_data': company.research_data
            },
            'contacts': contact_map,
            'relationships': relationship_network,
            'active_conversations': active_conversations,
            'summary': {
                'total_contacts': len(contacts),
                'decision_makers': len([c for c in contacts if c.is_decision_maker]),
                'primary_contacts': len([c for c in contacts if c.is_primary_contact]),
                'total_relationships': len(unique_relationships),
                'active_conversations': len(active_conversations),
                'total_conversations': len(all_conversations)
            }
        }

    async def find_expansion_targets(
        self,
        primary_contact_id: str,
        min_relationship_strength: str = 'medium'
    ) -> List[Dict[str, Any]]:
        """
        Find expansion targets (colleagues) of a primary contact.
        
        Use case: "Sue, your colleague Dr. XYZ inquired about..."
        
        Returns list of contacts who are colleagues of the primary contact,
        prioritized by relationship strength and engagement potential.
        """
        # Get primary contact
        primary_contact = await self.contact_repo.get_contact_by_id(primary_contact_id)
        if not primary_contact:
            raise ValueError(f"Contact {primary_contact_id} not found")

        # Get colleagues using database function
        colleagues_data = await self.relationship_repo.get_colleagues(primary_contact_id)

        # Enrich with full contact data
        expansion_targets = []
        for colleague_data in colleagues_data:
            colleague = await self.contact_repo.get_contact_by_id(colleague_data['colleague_id'])
            if not colleague:
                continue

            # Filter by relationship strength
            strength_order = {'weak': 1, 'medium': 2, 'strong': 3}
            min_strength = strength_order.get(min_relationship_strength, 2)
            current_strength = strength_order.get(colleague_data['relationship_strength'], 2)
            
            if current_strength < min_strength:
                continue

            # Get conversation status
            conversations = await self.conversation_repo.get_conversations_by_contact(
                colleague.id,
                status='active'
            )

            expansion_targets.append({
                'contact': colleague,
                'relationship_to_primary': {
                    'primary_contact': {
                        'id': primary_contact.id,
                        'name': primary_contact.full_name,
                        'title': primary_contact.title
                    },
                    'strength': colleague_data['relationship_strength']
                },
                'engagement_status': {
                    'has_active_conversation': len(conversations) > 0,
                    'engagement_score': colleague.engagement_score,
                    'last_engaged_at': colleague.last_engaged_at
                },
                'priority_score': self._calculate_expansion_priority(
                    colleague,
                    colleague_data['relationship_strength'],
                    len(conversations) > 0
                )
            })

        # Sort by priority score
        expansion_targets.sort(key=lambda x: x['priority_score'], reverse=True)

        return expansion_targets

    def _calculate_expansion_priority(
        self,
        contact: Contact,
        relationship_strength: str,
        has_active_conversation: bool
    ) -> float:
        """Calculate priority score for expansion target"""
        score = 0.0

        # Relationship strength (0-30 points)
        strength_scores = {'weak': 10, 'medium': 20, 'strong': 30}
        score += strength_scores.get(relationship_strength, 20)

        # Decision maker status (0-25 points)
        if contact.is_decision_maker:
            score += 25
        elif contact.is_champion:
            score += 20

        # Seniority level (0-20 points)
        seniority_scores = {
            'c-level': 20,
            'vp': 15,
            'director': 12,
            'manager': 8,
            'individual_contributor': 5
        }
        score += seniority_scores.get(contact.seniority_level, 5)

        # Engagement score (0-15 points)
        score += (contact.engagement_score / 100) * 15

        # Penalize if already in active conversation (reduce by 50%)
        if has_active_conversation:
            score *= 0.5

        # Bonus for no previous engagement (fresh target)
        if contact.total_touchpoints == 0:
            score += 10

        return score

    async def get_conversation_context(
        self,
        contact_id: str,
        include_company_context: bool = True,
        include_relationship_context: bool = True
    ) -> Dict[str, Any]:
        """
        Get all context needed for personalized messaging to a contact.
        
        Returns:
        - Contact information and preferences
        - Company context and research
        - Conversation history and context
        - Relationship context (colleagues, etc.)
        - Recent touchpoints and engagement
        """
        # Get contact
        contact = await self.contact_repo.get_contact_by_id(contact_id)
        if not contact:
            raise ValueError(f"Contact {contact_id} not found")

        context = {
            'contact': {
                'id': contact.id,
                'name': contact.full_name,
                'email': contact.email,
                'title': contact.title,
                'role': contact.role,
                'interests': contact.interests,
                'communication_preferences': contact.communication_preferences,
                'research_data': contact.research_data
            }
        }

        # Company context
        if include_company_context and contact.company_id:
            company = await self.company_repo.get_company_by_id(contact.company_id)
            if company:
                context['company'] = {
                    'id': company.id,
                    'name': company.name,
                    'domain': company.domain,
                    'industry': company.industry,
                    'research_data': company.research_data
                }

        # Conversation context
        conversations = await self.conversation_repo.get_conversations_by_contact(contact_id)
        active_conversations = [c for c in conversations if c.status == 'active']
        
        context['conversations'] = {
            'active': active_conversations,
            'total': len(conversations),
            'latest_context': active_conversations[0].context if active_conversations else {}
        }

        # Touchpoint history
        if active_conversations:
            latest_conv = active_conversations[0]
            touchpoints = await self.touchpoint_repo.get_touchpoints(latest_conv.id, limit=10)
            engagement_metrics = await self.touchpoint_repo.get_engagement_metrics(latest_conv.id)
            
            context['engagement'] = {
                'recent_touchpoints': touchpoints,
                'metrics': engagement_metrics,
                'last_touchpoint_at': latest_conv.last_touchpoint_at,
                'last_response_at': latest_conv.last_response_at
            }

        # Relationship context
        if include_relationship_context:
            relationships = await self.relationship_repo.get_contact_relationships(contact_id)
            colleagues = await self.relationship_repo.get_colleagues(contact_id)
            
            context['relationships'] = {
                'total': len(relationships),
                'colleagues': colleagues,
                'network': relationships
            }

        return context

    async def get_account_health_score(self, company_id: str) -> Dict[str, Any]:
        """
        Calculate account health score based on engagement metrics.
        
        Returns score (0-100) and breakdown by category.
        """
        overview = await self.get_account_overview(company_id)
        
        # Engagement score (0-40 points)
        engagement_score = 0
        total_engagement = sum(
            c['engagement_score'] for c in overview['contacts'].values()
        )
        avg_engagement = total_engagement / len(overview['contacts']) if overview['contacts'] else 0
        engagement_score = (avg_engagement / 100) * 40

        # Conversation activity (0-30 points)
        conversation_score = 0
        active_ratio = (
            overview['summary']['active_conversations'] / 
            max(overview['summary']['total_contacts'], 1)
        )
        conversation_score = min(active_ratio * 30, 30)

        # Relationship depth (0-20 points)
        relationship_score = 0
        relationship_ratio = (
            overview['summary']['total_relationships'] / 
            max(overview['summary']['total_contacts'], 1)
        )
        relationship_score = min(relationship_ratio * 20, 20)

        # Decision maker engagement (0-10 points)
        decision_maker_score = 0
        if overview['summary']['decision_makers'] > 0:
            decision_maker_score = 10

        total_score = (
            engagement_score +
            conversation_score +
            relationship_score +
            decision_maker_score
        )

        return {
            'total_score': round(total_score, 2),
            'breakdown': {
                'engagement': round(engagement_score, 2),
                'conversations': round(conversation_score, 2),
                'relationships': round(relationship_score, 2),
                'decision_makers': round(decision_maker_score, 2)
            },
            'health_status': self._get_health_status(total_score),
            'recommendations': self._get_health_recommendations(total_score, overview)
        }

    def _get_health_status(self, score: float) -> str:
        """Get health status label from score"""
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'fair'
        elif score >= 20:
            return 'poor'
        else:
            return 'critical'

    def _get_health_recommendations(
        self,
        score: float,
        overview: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on health score"""
        recommendations = []

        if overview['summary']['decision_makers'] == 0:
            recommendations.append(
                "Identify and engage decision makers within the account"
            )

        if overview['summary']['active_conversations'] == 0:
            recommendations.append(
                "Initiate conversations with key contacts"
            )

        if overview['summary']['total_relationships'] < overview['summary']['total_contacts']:
            recommendations.append(
                "Map relationships between contacts for multi-touch coordination"
            )

        avg_engagement = sum(
            c['engagement_score'] for c in overview['contacts'].values()
        ) / max(len(overview['contacts']), 1)
        
        if avg_engagement < 30:
            recommendations.append(
                "Increase engagement through personalized multi-channel outreach"
            )

        return recommendations


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ['CompanyGraph']
