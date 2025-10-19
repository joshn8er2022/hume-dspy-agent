#!/usr/bin/env python3
"""
Comprehensive Test Suite for Hume DSPy Agent
Tests all interfaces with varying complexity levels
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "https://hume-dspy-agent-production.up.railway.app"

class TestRunner:
    def __init__(self):
        self.results = []
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def close(self):
        await self.client.aclose()
    
    def log_result(self, test_type: str, complexity: str, test_name: str, 
                   status: str, duration: float, response_data: Any = None, error: str = None):
        """Log test result"""
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "test_type": test_type,
            "complexity": complexity,
            "test_name": test_name,
            "status": status,
            "duration_seconds": duration,
            "response_data": response_data,
            "error": error
        }
        self.results.append(result)
        
        # Print real-time feedback
        emoji = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⏳"
        print(f"{emoji} [{test_type}] [{complexity}] {test_name} - {duration:.2f}s")
        if error:
            print(f"   Error: {error}")
    
    # ===== WEBHOOK TESTS =====
    
    async def test_webhook_typeform(self, complexity: str, data: Dict):
        """Test Typeform webhook"""
        start = time.time()
        try:
            response = await self.client.post(
                f"{BASE_URL}/webhooks/typeform",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                self.log_result("WEBHOOK", complexity, "Typeform", "SUCCESS", duration, response.json())
            else:
                self.log_result("WEBHOOK", complexity, "Typeform", "FAILED", duration, 
                              error=f"Status {response.status_code}: {response.text}")
        except Exception as e:
            duration = time.time() - start
            self.log_result("WEBHOOK", complexity, "Typeform", "ERROR", duration, error=str(e))
    
    # ===== A2A TESTS =====
    
    async def test_a2a_introspect(self, complexity: str, query: str):
        """Test A2A introspection endpoint"""
        start = time.time()
        try:
            response = await self.client.post(
                f"{BASE_URL}/a2a/introspect",
                json={
                    "agent": "strategy",
                    "query": query,
                    "context": {}
                },
                headers={"Content-Type": "application/json"}
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                self.log_result("A2A", complexity, f"Introspect: {query[:30]}...", "SUCCESS", duration, response.json())
            else:
                self.log_result("A2A", complexity, f"Introspect: {query[:30]}...", "FAILED", duration,
                              error=f"Status {response.status_code}")
        except Exception as e:
            duration = time.time() - start
            self.log_result("A2A", complexity, f"Introspect: {query[:30]}...", "ERROR", duration, error=str(e))
    
    # ===== STRATEGY AGENT DIRECT TESTS =====
    
    async def test_strategy_query(self, complexity: str, query: str):
        """Test Strategy Agent via health check extended endpoint"""
        start = time.time()
        try:
            # Use health endpoint first to verify service
            response = await self.client.get(f"{BASE_URL}/health")
            duration = time.time() - start
            
            if response.status_code == 200:
                health_data = response.json()
                self.log_result("DIRECT", complexity, f"Health check", "SUCCESS", duration, health_data)
            else:
                self.log_result("DIRECT", complexity, f"Health check", "FAILED", duration,
                              error=f"Status {response.status_code}")
        except Exception as e:
            duration = time.time() - start
            self.log_result("DIRECT", complexity, f"Health check", "ERROR", duration, error=str(e))


async def run_comprehensive_tests():
    """Run all tests with varying complexity"""
    runner = TestRunner()
    
    print("=" * 80)
    print("🧪 COMPREHENSIVE AGENT TEST SUITE")
    print("=" * 80)
    print()
    
    # ===== SIMPLE TESTS (Level 1) =====
    print("\n📝 SIMPLE TESTS (Fast responses, minimal reasoning)")
    print("-" * 80)
    
    # Simple A2A
    await runner.test_a2a_introspect("SIMPLE", "hey")
    await asyncio.sleep(2)
    
    await runner.test_a2a_introspect("SIMPLE", "status")
    await asyncio.sleep(2)
    
    await runner.test_a2a_introspect("SIMPLE", "ping")
    await asyncio.sleep(2)
    
    # Simple webhook - minimal data
    await runner.test_webhook_typeform("SIMPLE", {
        "event_type": "form_response",
        "form_response": {
            "form_id": "test123",
            "answers": [
                {"field": {"id": "name"}, "text": "Test User"},
                {"field": {"id": "email"}, "email": "test@example.com"}
            ]
        }
    })
    await asyncio.sleep(2)
    
    # Health check
    await runner.test_strategy_query("SIMPLE", "health")
    await asyncio.sleep(2)
    
    # ===== COMPLEX TESTS (Level 2) =====
    print("\n🧠 COMPLEX TESTS (Reasoning required, multi-step)")
    print("-" * 80)
    
    # Complex A2A - requires reasoning
    await runner.test_a2a_introspect("COMPLEX", "explain why our conversion rate dropped last week")
    await asyncio.sleep(3)
    
    await runner.test_a2a_introspect("COMPLEX", "analyze the pipeline and recommend improvements")
    await asyncio.sleep(3)
    
    await runner.test_a2a_introspect("COMPLEX", "what's the best strategy for nurturing WARM leads?")
    await asyncio.sleep(3)
    
    # Complex webhook - full lead data
    await runner.test_webhook_typeform("COMPLEX", {
        "event_type": "form_response",
        "form_response": {
            "form_id": "wellness_clinic_form",
            "token": "test_complex_" + str(int(time.time())),
            "landed_at": datetime.utcnow().isoformat(),
            "submitted_at": datetime.utcnow().isoformat(),
            "answers": [
                {
                    "field": {"id": "first_name", "type": "short_text"},
                    "type": "text",
                    "text": "Dr. Sarah"
                },
                {
                    "field": {"id": "last_name", "type": "short_text"},
                    "type": "text",
                    "text": "Johnson"
                },
                {
                    "field": {"id": "email", "type": "email"},
                    "type": "email",
                    "email": "sarah.johnson@complexclinic.com"
                },
                {
                    "field": {"id": "company", "type": "short_text"},
                    "type": "text",
                    "text": "Complex Wellness Clinic"
                },
                {
                    "field": {"id": "use_case", "type": "long_text"},
                    "type": "text",
                    "text": "We're a 500+ patient telehealth clinic specializing in metabolic health. Need body composition tracking that integrates with our EMR, supports remote monitoring, and provides detailed analytics for patient progress tracking."
                },
                {
                    "field": {"id": "patient_volume", "type": "multiple_choice"},
                    "type": "choice",
                    "choice": {"label": "500+ patients"}
                },
                {
                    "field": {"id": "specialty", "type": "short_text"},
                    "type": "text",
                    "text": "Metabolic health and weight management"
                }
            ]
        }
    })
    await asyncio.sleep(3)
    
    # ===== ACTION TESTS (Level 3 - ReAct) =====
    print("\n🔧 ACTION TESTS (Tool calling, data retrieval)")
    print("-" * 80)
    
    # Action A2A - should trigger ReAct
    await runner.test_a2a_introspect("ACTION", "audit our lead flow")
    await asyncio.sleep(5)
    
    await runner.test_a2a_introspect("ACTION", "query the database for all HOT leads")
    await asyncio.sleep(5)
    
    await runner.test_a2a_introspect("ACTION", "show me pipeline stats for the last 24 hours")
    await asyncio.sleep(5)
    
    await runner.test_a2a_introspect("ACTION", "get data on email deliverability and opens")
    await asyncio.sleep(5)
    
    await runner.test_a2a_introspect("ACTION", "pull real metrics from GMass and Supabase")
    await asyncio.sleep(5)
    
    # ===== EDGE CASES =====
    print("\n⚠️ EDGE CASE TESTS (Malformed, empty, special)")
    print("-" * 80)
    
    # Empty query
    await runner.test_a2a_introspect("EDGE", "")
    await asyncio.sleep(2)
    
    # Very long query
    long_query = "Can you " + "please " * 100 + "tell me about the system?"
    await runner.test_a2a_introspect("EDGE", long_query)
    await asyncio.sleep(2)
    
    # Special characters
    await runner.test_a2a_introspect("EDGE", "What's the <script>alert('test')</script> status?")
    await asyncio.sleep(2)
    
    # Malformed webhook
    await runner.test_webhook_typeform("EDGE", {
        "event_type": "form_response",
        # Missing form_response field
    })
    await asyncio.sleep(2)
    
    # ===== GENERATE REPORT =====
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    total = len(runner.results)
    success = len([r for r in runner.results if r["status"] == "SUCCESS"])
    failed = len([r for r in runner.results if r["status"] == "FAILED"])
    error = len([r for r in runner.results if r["status"] == "ERROR"])
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Success: {success} ({success/total*100:.1f}%)")
    print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"🔴 Errors: {error} ({error/total*100:.1f}%)")
    
    # Breakdown by type
    print("\n📦 By Test Type:")
    for test_type in ["WEBHOOK", "A2A", "DIRECT"]:
        type_results = [r for r in runner.results if r["test_type"] == test_type]
        if type_results:
            type_success = len([r for r in type_results if r["status"] == "SUCCESS"])
            print(f"  {test_type}: {type_success}/{len(type_results)} passed")
    
    # Breakdown by complexity
    print("\n🎯 By Complexity:")
    for complexity in ["SIMPLE", "COMPLEX", "ACTION", "EDGE"]:
        comp_results = [r for r in runner.results if r["complexity"] == complexity]
        if comp_results:
            comp_success = len([r for r in comp_results if r["status"] == "SUCCESS"])
            avg_duration = sum(r["duration_seconds"] for r in comp_results) / len(comp_results)
            print(f"  {complexity}: {comp_success}/{len(comp_results)} passed (avg {avg_duration:.2f}s)")
    
    # Performance stats
    print("\n⚡ Performance:")
    durations = [r["duration_seconds"] for r in runner.results if r["status"] == "SUCCESS"]
    if durations:
        print(f"  Fastest: {min(durations):.2f}s")
        print(f"  Slowest: {max(durations):.2f}s")
        print(f"  Average: {sum(durations)/len(durations):.2f}s")
    
    # Save detailed results
    output_file = f"test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(runner.results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    print()
    
    await runner.close()
    
    return runner.results


if __name__ == "__main__":
    print("Starting comprehensive test suite...")
    print("This will take ~3-5 minutes to complete.\n")
    
    results = asyncio.run(run_comprehensive_tests())
    
    print("\n✨ Test suite complete!")
