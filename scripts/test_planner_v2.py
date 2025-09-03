#!/usr/bin/env python3
"""
Test script for planner v2 with sharp scenarios
"""

import httpx
import json
import time
from typing import List, Dict, Any

# Test scenarios: 5 MEDIUM, 5 HARD
TEST_SCENARIOS = [
    # MEDIUM scenarios
    {
        "id": "medium_1",
        "message": "Skapa en presentation om projektstatus",
        "expected_intent": "none",
        "expected_tool": "none",
        "complexity": "MEDIUM"
    },
    {
        "id": "medium_2", 
        "message": "Organisera min kalender för nästa vecka",
        "expected_intent": "calendar",
        "expected_tool": "calendar.create_draft",
        "complexity": "MEDIUM"
    },
    {
        "id": "medium_3",
        "message": "Skicka en sammanfattning till teamet",
        "expected_intent": "email",
        "expected_tool": "email.create_draft", 
        "complexity": "MEDIUM"
    },
    {
        "id": "medium_4",
        "message": "Kolla vädret för helgen",
        "expected_intent": "weather",
        "expected_tool": "weather.lookup",
        "complexity": "MEDIUM"
    },
    {
        "id": "medium_5",
        "message": "Kommer du ihåg vad vi diskuterade igår?",
        "expected_intent": "memory",
        "expected_tool": "memory.query",
        "complexity": "MEDIUM"
    },
    
    # HARD scenarios
    {
        "id": "hard_1",
        "message": "Analysera min produktivitet under de senaste veckorna och föreslå strategier för att optimera min arbetsdag med hänsyn till mina deadlines och energinivåer",
        "expected_intent": "none",
        "expected_tool": "none",
        "complexity": "HARD"
    },
    {
        "id": "hard_2",
        "message": "Utvärdera alternativ för att förbättra teamets kommunikation och koordinera en workshop för att implementera de bästa lösningarna",
        "expected_intent": "calendar",
        "expected_tool": "calendar.create_draft",
        "complexity": "HARD"
    },
    {
        "id": "hard_3", 
        "message": "Sammanfatta projektets framsteg och skicka en detaljerad rapport till stakeholders med rekommendationer för nästa fas",
        "expected_intent": "email",
        "expected_tool": "email.create_draft",
        "complexity": "HARD"
    },
    {
        "id": "hard_4",
        "message": "Jämför väderprognoser från olika källor för att planera den optimala tiden för vårt utomhusevent nästa månad",
        "expected_intent": "weather",
        "expected_tool": "weather.lookup",
        "complexity": "HARD"
    },
    {
        "id": "hard_5",
        "message": "Sök i våra tidigare diskussioner och sammanfatta de viktigaste besluten vi tog angående produktstrategin under de senaste tre månaderna",
        "expected_intent": "memory",
        "expected_tool": "memory.query",
        "complexity": "HARD"
    }
]

def test_planner_v2():
    """Test planner v2 with scenarios"""
    
    base_url = "http://localhost:18000"
    results = []
    
    print("🧪 Testing Planner v2 with sharp scenarios...")
    print(f"📊 Total scenarios: {len(TEST_SCENARIOS)}")
    print("=" * 60)
    
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"\n🔍 Test {i}/{len(TEST_SCENARIOS)}: {scenario['id']}")
        print(f"📝 Message: {scenario['message'][:50]}...")
        print(f"🎯 Expected: intent={scenario['expected_intent']}, tool={scenario['expected_tool']}")
        
        try:
            # Send request
            payload = {
                "v": "1",
                "session_id": f"test_v2_{scenario['id']}",
                "message": scenario["message"],
                "force_route": "planner"
            }
            
            start_time = time.time()
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{base_url}/api/chat", json=payload)
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                results.append({
                    "scenario": scenario["id"],
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "latency_ms": latency_ms
                })
                continue
            
            # Parse response
            response_data = response.json()
            response_text = response_data.get("response", "")
            
            # Extract metadata
            metadata = response_data.get("metadata", {})
            shadow_metadata = metadata.get("shadow", {})
            
            # Parse JSON response
            try:
                parsed_response = json.loads(response_text)
                intent = parsed_response.get("intent", "unknown")
                tool = parsed_response.get("tool", "unknown")
                schema_ok = True
            except json.JSONDecodeError:
                # Try to extract from old format for backward compatibility
                try:
                    if '"version":1' in response_text and '"tool":' in response_text:
                        # Old format: {"version":1,"tool":"...","reason":"..."}
                        intent = "unknown"  # Old format doesn't have intent
                        tool = parsed_response.get("tool", "unknown") if 'parsed_response' in locals() else "parse_error"
                        schema_ok = False  # Old format
                    else:
                        intent = "parse_error"
                        tool = "parse_error"
                        schema_ok = False
                except:
                    intent = "parse_error"
                    tool = "parse_error"
                    schema_ok = False
            
            # Check results
            intent_match = intent == scenario["expected_intent"]
            tool_match = tool == scenario["expected_tool"]
            shadow_enabled = shadow_metadata.get("enabled", False)
            shadow_schema_ok = shadow_metadata.get("intent_match", False)
            
            # Determine success
            success = schema_ok and intent_match and tool_match
            
            print(f"📊 Result: intent='{intent}' (match={intent_match}), tool='{tool}' (match={tool_match})")
            print(f"⚡ Latency: {latency_ms:.1f}ms")
            print(f"🔍 Schema OK: {schema_ok}")
            print(f"👥 Shadow: {shadow_enabled}, Schema OK: {shadow_schema_ok}")
            
            if success:
                print("✅ PASS")
            else:
                print("❌ FAIL")
            
            results.append({
                "scenario": scenario["id"],
                "success": success,
                "intent": intent,
                "tool": tool,
                "intent_match": intent_match,
                "tool_match": tool_match,
                "schema_ok": schema_ok,
                "latency_ms": latency_ms,
                "shadow_enabled": shadow_enabled,
                "shadow_schema_ok": shadow_schema_ok,
                "complexity": scenario["complexity"]
            })
            
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            results.append({
                "scenario": scenario["id"],
                "success": False,
                "error": str(e),
                "complexity": scenario["complexity"]
            })
    
    # Calculate statistics
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r.get("success", False))
    schema_ok_tests = sum(1 for r in results if r.get("schema_ok", False))
    intent_match_tests = sum(1 for r in results if r.get("intent_match", False))
    tool_match_tests = sum(1 for r in results if r.get("tool_match", False))
    
    # By complexity
    medium_tests = [r for r in results if r.get("complexity") == "MEDIUM"]
    hard_tests = [r for r in results if r.get("complexity") == "HARD"]
    
    medium_success = sum(1 for r in medium_tests if r.get("success", False))
    hard_success = sum(1 for r in hard_tests if r.get("success", False))
    
    print("\n" + "=" * 60)
    print("📈 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"🎯 Overall Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
    print(f"📋 Schema OK Rate: {schema_ok_tests}/{total_tests} ({schema_ok_tests/total_tests*100:.1f}%)")
    print(f"🎯 Intent Match Rate: {intent_match_tests}/{total_tests} ({intent_match_tests/total_tests*100:.1f}%)")
    print(f"🔧 Tool Match Rate: {tool_match_tests}/{total_tests} ({tool_match_tests/total_tests*100:.1f}%)")
    print(f"📊 MEDIUM Success: {medium_success}/{len(medium_tests)} ({medium_success/len(medium_tests)*100:.1f}%)")
    print(f"📊 HARD Success: {hard_success}/{len(hard_tests)} ({hard_success/len(hard_tests)*100:.1f}%)")
    
    # Check success criteria
    print("\n🎯 SUCCESS CRITERIA CHECK")
    print("=" * 60)
    
    criteria_met = True
    
    # Schema OK @ first ≥ 98% on EASY+MEDIUM
    easy_medium_schema_ok = sum(1 for r in medium_tests if r.get("schema_ok", False))
    schema_ok_rate = easy_medium_schema_ok / len(medium_tests) if medium_tests else 0
    schema_ok_pass = schema_ok_rate >= 0.98
    print(f"📋 Schema OK @ first ≥ 98% (EASY+MEDIUM): {schema_ok_rate:.1%} {'✅' if schema_ok_pass else '❌'}")
    criteria_met = criteria_met and schema_ok_pass
    
    # Intent match ≥ 95%
    intent_match_rate = intent_match_tests / total_tests if total_tests > 0 else 0
    intent_match_pass = intent_match_rate >= 0.95
    print(f"🎯 Intent match ≥ 95%: {intent_match_rate:.1%} {'✅' if intent_match_pass else '❌'}")
    criteria_met = criteria_met and intent_match_pass
    
    print(f"\n🎉 OVERALL RESULT: {'✅ PASS' if criteria_met else '❌ FAIL'}")
    
    return criteria_met

if __name__ == "__main__":
    success = test_planner_v2()
    exit(0 if success else 1)
