#!/usr/bin/env python3
"""
Direct test script for planner v2 with strict assertions
"""

import sys
import os
sys.path.append('/app')

from src.llm.planner_v2 import get_planner_v2_driver
from src.planner.schema_v4 import IntentType, ToolType, RenderInstruction

# Test scenarios: 10 MEDIUM + 5 HARD
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
    {
        "id": "medium_6",
        "message": "Boka ett möte med Anna imorgon kl 14:00",
        "expected_intent": "calendar",
        "expected_tool": "calendar.create_draft",
        "complexity": "MEDIUM"
    },
    {
        "id": "medium_7",
        "message": "Skicka en email till chefen om projektstatus",
        "expected_intent": "email",
        "expected_tool": "email.create_draft",
        "complexity": "MEDIUM"
    },
    {
        "id": "medium_8",
        "message": "Vad blir vädret i Stockholm imorgon?",
        "expected_intent": "weather",
        "expected_tool": "weather.lookup",
        "complexity": "MEDIUM"
    },
    {
        "id": "medium_9",
        "message": "Kommer du ihåg vad vi sa om budgeten?",
        "expected_intent": "memory",
        "expected_tool": "memory.query",
        "complexity": "MEDIUM"
    },
    {
        "id": "medium_10",
        "message": "Hej, hur mår du?",
        "expected_intent": "none",
        "expected_tool": "none",
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

def test_planner_v2_direct():
    """Test planner v2 directly with strict assertions"""
    
    print("🧪 Testing Planner v2 directly with strict assertions...")
    print(f"📊 Total scenarios: {len(TEST_SCENARIOS)}")
    print("=" * 60)
    
    # Initialize planner v2
    planner_v2 = get_planner_v2_driver()
    
    results = []
    
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"\n🔍 Test {i}/{len(TEST_SCENARIOS)}: {scenario['id']}")
        print(f"📝 Message: {scenario['message'][:50]}...")
        print(f"🎯 Expected: intent={scenario['expected_intent']}, tool={scenario['expected_tool']}")
        
        try:
            # Generate response directly
            result = planner_v2.generate(scenario["message"])
            
            # Extract fields
            response_text = result.get("text", "")
            schema_ok = result.get("schema_ok", False)
            json_parsed = result.get("json_parsed", False)
            
            # Parse JSON response
            try:
                import json
                parsed_response = json.loads(response_text)
                intent = parsed_response.get("intent", "unknown")
                tool = parsed_response.get("tool", "unknown")
                render_instruction = parsed_response.get("render_instruction", "unknown")
                args = parsed_response.get("args", {})
                meta = parsed_response.get("meta", {})
                
                # Strict assertions
                assert intent in ["email", "calendar", "weather", "memory", "none"], f"Invalid intent: {intent}"
                assert tool in ["email.create_draft", "calendar.create_draft", "weather.lookup", "memory.query", "none"], f"Invalid tool: {tool}"
                assert render_instruction in ["chart", "map", "scene", "none"], f"Invalid render_instruction: {render_instruction}"
                assert isinstance(args, dict), f"Args must be dict, got: {type(args)}"
                assert isinstance(meta, dict), f"Meta must be dict, got: {type(meta)}"
                assert meta.get("version") == "4.0", f"Invalid version: {meta.get('version')}"
                assert meta.get("schema_version") == "v4", f"Invalid schema_version: {meta.get('schema_version')}"
                
                # Check results
                intent_match = intent == scenario["expected_intent"]
                tool_match = tool == scenario["expected_tool"]
                success = schema_ok and json_parsed and intent_match and tool_match
                
                print(f"📊 Result: intent='{intent}' (match={intent_match}), tool='{tool}' (match={tool_match})")
                print(f"🔍 Schema OK: {schema_ok}, JSON Parsed: {json_parsed}")
                print(f"🎨 Render: {render_instruction}, Args: {len(args)} keys")
                
                if success:
                    print("✅ PASS")
                else:
                    print("❌ FAIL")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
                success = False
                intent = "parse_error"
                tool = "parse_error"
            except AssertionError as e:
                print(f"❌ Assertion Error: {e}")
                success = False
                intent = "assertion_error"
                tool = "assertion_error"
            
            results.append({
                "scenario": scenario["id"],
                "success": success,
                "intent": intent,
                "tool": tool,
                "intent_match": intent_match if 'intent_match' in locals() else False,
                "tool_match": tool_match if 'tool_match' in locals() else False,
                "schema_ok": schema_ok,
                "json_parsed": json_parsed,
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
    json_parsed_tests = sum(1 for r in results if r.get("json_parsed", False))
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
    print(f"🔍 JSON Parsed Rate: {json_parsed_tests}/{total_tests} ({json_parsed_tests/total_tests*100:.1f}%)")
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
    success = test_planner_v2_direct()
    exit(0 if success else 1)
