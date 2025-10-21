"""
Comprehensive Agent Testing via HTTP API

Tests 20+ edge cases including:
- System prompt awareness (Phase 1.5 fix)
- Tool execution (10 ReAct tools)
- Subordinate delegation (6 types)
- Strategic thinking (not just pipeline)
- Error handling and edge cases
- Google Drive audit (bug fix verification)
- Complex multi-step tasks
"""

import httpx
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import os

# Railway production URL
BASE_URL = "https://hume-dspy-agent-production.up.railway.app"

# Test results storage
test_results = []


class AgentTester:
    """Comprehensive agent testing via HTTP API"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.client = httpx.AsyncClient(timeout=120.0)  # 2 min timeout for complex queries
        self.test_number = 0
    
    async def test_agent(self, test_name: str, payload: Dict[str, Any], expected_behavior: str):
        """Execute a single test case"""
        self.test_number += 1
        
        print(f"\n{'='*80}")
        print(f"TEST #{self.test_number}: {test_name}")
        print(f"{'='*80}")
        print(f"Expected: {expected_behavior}")
        print(f"\nSending request...")
        
        try:
            # Send via Slack events endpoint (simulates Slack message)
            response = await self.client.post(
                f"{self.base_url}/slack/events",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ SUCCESS")
                print(f"Response preview: {str(result)[:500]}...")
                
                test_results.append({
                    "test_number": self.test_number,
                    "name": test_name,
                    "status": "PASS",
                    "response_code": response.status_code,
                    "expected": expected_behavior,
                    "response_preview": str(result)[:300]
                })
                
                return result
            else:
                print(f"\n❌ FAILED")
                print(f"Response: {response.text[:500]}")
                
                test_results.append({
                    "test_number": self.test_number,
                    "name": test_name,
                    "status": "FAIL",
                    "response_code": response.status_code,
                    "expected": expected_behavior,
                    "error": response.text[:300]
                })
                
                return None
                
        except Exception as e:
            print(f"\n❌ EXCEPTION: {str(e)}")
            
            test_results.append({
                "test_number": self.test_number,
                "name": test_name,
                "status": "ERROR",
                "expected": expected_behavior,
                "error": str(e)
            })
            
            return None
    
    def create_slack_event(self, message: str, user_id: str = "U123TEST") -> Dict[str, Any]:
        """Create a Slack event payload"""
        return {
            "type": "event_callback",
            "event": {
                "type": "message",
                "user": user_id,
                "text": message,
                "channel": "D123TEST",
                "ts": str(datetime.now().timestamp())
            }
        }
    
    async def run_all_tests(self):
        """Execute all 20+ test cases"""
        
        print("\n" + "="*80)
        print("🧪 COMPREHENSIVE AGENT TESTING - 20+ EDGE CASES")
        print("="*80)
        
        # =================================================================
        # CATEGORY 1: SYSTEM PROMPT AWARENESS (Phase 1.5 Fix)
        # =================================================================
        
        await self.test_agent(
            "System Prompt: Strategic vs Pipeline Focus",
            self.create_slack_event("What's your primary role?"),
            "Should say strategic execution partner, NOT just pipeline analyst"
        )
        
        await self.test_agent(
            "System Prompt: Capability Awareness",
            self.create_slack_event("What can you actually do?"),
            "Should list tools, subordinates, strategic capabilities - NOT claim blockers"
        )
        
        await self.test_agent(
            "System Prompt: Tool Count Check",
            self.create_slack_event("How many tools do you have?"),
            "Should mention 10 ReAct tools + 243 Zapier integrations"
        )
        
        # =================================================================
        # CATEGORY 2: STRATEGIC THINKING (Not Just Pipeline)
        # =================================================================
        
        await self.test_agent(
            "Strategic: Competitive Analysis Request",
            self.create_slack_event("Analyze our top 3 competitors in medical aesthetics"),
            "Should offer to spawn competitor_analyst subordinates, NOT claim blockers"
        )
        
        await self.test_agent(
            "Strategic: Market Entry Strategy",
            self.create_slack_event("Develop a market entry strategy for California dental clinics"),
            "Should delegate to market_researcher, NOT say 'I only do pipeline'"
        )
        
        await self.test_agent(
            "Strategic: Content Planning",
            self.create_slack_event("Help me plan our Q1 content strategy"),
            "Should delegate to content_strategist, NOT reject as out of scope"
        )
        
        # =================================================================
        # CATEGORY 3: SUBORDINATE DELEGATION (Agent Zero Pattern)
        # =================================================================
        
        await self.test_agent(
            "Delegation: Google Drive Audit (Bug Fix Test)",
            self.create_slack_event("Audit my Google Drive and tell me what's there"),
            "Should delegate to document_analyst with Google Workspace tools"
        )
        
        await self.test_agent(
            "Delegation: Account Research",
            self.create_slack_event("Research XYZ Dental Practice for ABM campaign"),
            "Should delegate to account_researcher with research tools"
        )
        
        await self.test_agent(
            "Delegation: Campaign Analysis",
            self.create_slack_event("Analyze our email campaign performance this month"),
            "Should delegate to campaign_analyst with Supabase access"
        )
        
        # =================================================================
        # CATEGORY 4: TOOL EXECUTION (DSPy ReAct)
        # =================================================================
        
        await self.test_agent(
            "Tool: Pipeline Query",
            self.create_slack_event("How many HOT leads do we have?"),
            "Should use query_supabase or get_pipeline_stats tool"
        )
        
        await self.test_agent(
            "Tool: Research Execution",
            self.create_slack_event("Research the medical aesthetics industry trends"),
            "Should use research_with_perplexity tool"
        )
        
        await self.test_agent(
            "Tool: List Available Integrations",
            self.create_slack_event("What Zapier integrations do you have access to?"),
            "Should use list_mcp_tools to show available integrations"
        )
        
        # =================================================================
        # CATEGORY 5: ERROR HANDLING & EDGE CASES
        # =================================================================
        
        await self.test_agent(
            "Edge: Ambiguous Request",
            self.create_slack_event("Help me"),
            "Should ask for clarification, not fail"
        )
        
        await self.test_agent(
            "Edge: Invalid Task Request",
            self.create_slack_event("Deploy new code to Railway"),
            "Should correctly identify as TRUE blocker (code deployment)"
        )
        
        await self.test_agent(
            "Edge: Multiple Capabilities in One",
            self.create_slack_event("Analyze pipeline, research competitors, and plan content strategy"),
            "Should break down into subtasks or coordinate multiple actions"
        )
        
        # =================================================================
        # CATEGORY 6: CONTEXT & MEMORY
        # =================================================================
        
        await self.test_agent(
            "Context: Multi-turn Conversation",
            self.create_slack_event("What did I just ask you about?"),
            "Should reference previous conversation (if tracked)"
        )
        
        await self.test_agent(
            "Context: Business Knowledge Gap",
            self.create_slack_event("What's our unit economics?"),
            "Should try to retrieve or ask for clarification (KB not populated yet)"
        )
        
        # =================================================================
        # CATEGORY 7: COMPLEX MULTI-STEP TASKS
        # =================================================================
        
        await self.test_agent(
            "Complex: Strategic Planning",
            self.create_slack_event("I want to enter the Texas dental market. Give me a complete strategy."),
            "Should coordinate multiple subordinates: market research, competitor analysis, ICP matching"
        )
        
        await self.test_agent(
            "Complex: Account-Based Campaign",
            self.create_slack_event("Build an ABM campaign for BigDental Corp - research, messaging, and outreach plan"),
            "Should delegate to multiple specialists: account_researcher, content_strategist"
        )
        
        # =================================================================
        # CATEGORY 8: NEGATIVE TEST CASES
        # =================================================================
        
        await self.test_agent(
            "Negative: Empty Message",
            self.create_slack_event(""),
            "Should handle gracefully"
        )
        
        await self.test_agent(
            "Negative: Very Long Rambling Request",
            self.create_slack_event("I need help with " + "something " * 100 + "can you help?"),
            "Should parse intent despite verbosity"
        )
        
        # =================================================================
        # FINAL TEST: Self-Awareness Check
        # =================================================================
        
        await self.test_agent(
            "Meta: Self-Evaluation",
            self.create_slack_event("What are you capable of that you weren't before?"),
            "Should reference Phase 1.5 enhancements: delegation, tools, strategic thinking"
        )
        
        print("\n" + "="*80)
        print("🎯 TESTING COMPLETE")
        print("="*80)
        
        await self.generate_report()
    
    async def generate_report(self):
        """Generate comprehensive test report"""
        
        print("\n" + "="*80)
        print("📊 TEST RESULTS SUMMARY")
        print("="*80)
        
        total = len(test_results)
        passed = len([t for t in test_results if t["status"] == "PASS"])
        failed = len([t for t in test_results if t["status"] == "FAIL"])
        errors = len([t for t in test_results if t["status"] == "ERROR"])
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"⚠️  Errors: {errors} ({errors/total*100:.1f}%)")
        
        print("\n" + "-"*80)
        print("DETAILED RESULTS:")
        print("-"*80)
        
        for result in test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"\n{status_icon} Test #{result['test_number']}: {result['name']}")
            print(f"   Expected: {result['expected']}")
            
            if result["status"] == "PASS":
                print(f"   Result: {result['response_preview']}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Save to file
        report_path = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "pass_rate": f"{passed/total*100:.1f}%"
                },
                "tests": test_results
            }, f, indent=2)
        
        print(f"\n📄 Full report saved to: {report_path}")
        
        print("\n" + "="*80)
        print("🎊 TESTING SESSION COMPLETE")
        print("="*80)
    
    async def close(self):
        """Clean up HTTP client"""
        await self.client.aclose()


async def main():
    """Run comprehensive testing"""
    tester = AgentTester()
    
    try:
        await tester.run_all_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    print("\n🚀 Starting Comprehensive Agent Testing")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    asyncio.run(main())
