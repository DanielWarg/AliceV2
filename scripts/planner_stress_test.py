#!/usr/bin/env python3
"""
Planner Stress Test - 30 scenarios to validate robustness
Tests various complexity levels and edge cases for Step 7 validation.
"""

import asyncio
import aiohttp
import json
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TestScenario:
    name: str
    message: str
    expected_tool: str
    complexity: str  # easy, medium, hard
    description: str

@dataclass
class TestResult:
    scenario: TestScenario
    latency_ms: float
    model_used: str
    tool: str
    schema_ok: bool
    fallback_used: bool
    response: str
    success: bool

class PlannerStressTest:
    def __init__(self, base_url: str = "http://localhost:18000"):
        self.base_url = base_url
        self.session_id = f"stress-test-{int(time.time())}"
        self.results: List[TestResult] = []
        
        # 50 test scenarios with varying complexity
        self.scenarios = [
            # EASY (15 scenarios) - Simple, direct requests
            TestScenario("simple_calendar", "Boka möte med Anna imorgon kl 14:00", "calendar.create_draft", "easy", "Basic calendar booking"),
            TestScenario("simple_email", "Skicka email till kund@firma.se", "email.create_draft", "easy", "Basic email draft"),
            TestScenario("simple_weather", "Vad är vädret i Stockholm?", "weather.lookup", "easy", "Basic weather query"),
            TestScenario("simple_memory", "Vad sa vi om projektet igår?", "memory.query", "easy", "Basic memory query"),
            TestScenario("simple_none", "Hej, hur mår du?", "none", "easy", "Simple greeting"),
            TestScenario("simple_time", "Vad är klockan?", "none", "easy", "Time query"),
            TestScenario("simple_help", "Kan du hjälpa mig?", "none", "easy", "Help request"),
            TestScenario("simple_thanks", "Tack för hjälpen!", "none", "easy", "Thank you"),
            TestScenario("simple_yes", "Ja, det låter bra", "none", "easy", "Simple yes"),
            TestScenario("simple_no", "Nej, inte idag", "none", "easy", "Simple no"),
            TestScenario("simple_calendar_2", "Skapa möte med teamet på fredag", "calendar.create_draft", "easy", "Calendar creation"),
            TestScenario("simple_email_2", "Maila till boss@company.com", "email.create_draft", "easy", "Email to specific address"),
            TestScenario("simple_weather_2", "Hur blir vädret imorgon?", "weather.lookup", "easy", "Weather tomorrow"),
            TestScenario("simple_memory_2", "Kommer du ihåg vad vi pratade om?", "memory.query", "easy", "Memory recall"),
            TestScenario("simple_none_2", "Bra jobbat!", "none", "easy", "Praise"),
            
            # MEDIUM (20 scenarios) - More complex, ambiguous requests
            TestScenario("medium_calendar_ambiguous", "Jag vill träffa någon från teamet nästa vecka", "calendar.create_draft", "medium", "Ambiguous calendar request"),
            TestScenario("medium_email_context", "Skriv ett mail om det nya kontraktet vi diskuterade", "email.create_draft", "medium", "Email with context"),
            TestScenario("medium_weather_travel", "Vad blir vädret i Göteborg på fredag? Jag ska resa dit", "weather.lookup", "medium", "Weather for travel"),
            TestScenario("medium_memory_specific", "Kommer du ihåg vad vi sa om budgeten förra veckan?", "memory.query", "medium", "Specific memory query"),
            TestScenario("medium_mixed", "Kan du både kolla vädret och skicka en påminnelse?", "none", "medium", "Mixed request"),
            TestScenario("medium_conditional", "Om det regnar imorgon, boka mötet på torsdag istället", "calendar.create_draft", "medium", "Conditional request"),
            TestScenario("medium_priority", "Detta är viktigt - skicka en akut email till chefen", "email.create_draft", "medium", "Priority request"),
            TestScenario("medium_schedule", "Planera min dag imorgon", "calendar.create_draft", "medium", "Day planning"),
            TestScenario("medium_followup", "Följ upp på det mail jag skickade igår", "email.create_draft", "medium", "Follow-up request"),
            TestScenario("medium_reminder", "Påminn mig om mötet om 2 timmar", "calendar.create_draft", "medium", "Reminder request"),
            TestScenario("medium_calendar_3", "Jag behöver boka tid med utvecklarna", "calendar.create_draft", "medium", "Developer meeting"),
            TestScenario("medium_email_3", "Skicka en rapport till alla i teamet", "email.create_draft", "medium", "Team report"),
            TestScenario("medium_weather_3", "Vad blir vädret i helgen? Vi ska ha grillfest", "weather.lookup", "medium", "Weekend weather"),
            TestScenario("medium_memory_3", "Vad sa vi om den nya funktionen?", "memory.query", "medium", "Feature discussion"),
            TestScenario("medium_none_3", "Jag förstår, tack för förklaringen", "none", "medium", "Understanding response"),
            TestScenario("medium_calendar_4", "Boka konferensrum för presentationen", "calendar.create_draft", "medium", "Conference room booking"),
            TestScenario("medium_email_4", "Skicka en sammanfattning av mötet", "email.create_draft", "medium", "Meeting summary"),
            TestScenario("medium_weather_4", "Vad blir vädret i Malmö nästa vecka?", "weather.lookup", "medium", "Next week weather"),
            TestScenario("medium_memory_4", "Vad sa vi om kundmötet?", "memory.query", "medium", "Customer meeting memory"),
            TestScenario("medium_none_4", "Det låter som en bra plan", "none", "medium", "Plan approval"),
            
            # HARD (15 scenarios) - Complex, edge cases, multiple intents
            TestScenario("hard_multistep", "Boka möte med Anna, skicka agenda till henne, och påminn mig 1 timme innan", "calendar.create_draft", "hard", "Multi-step request"),
            TestScenario("hard_conditional_complex", "Om Anna är ledig imorgon kl 14, boka möte. Annars kolla hennes kalender och föreslå alternativ", "calendar.create_draft", "hard", "Complex conditional"),
            TestScenario("hard_context_heavy", "Baserat på vårt samtal igår om Q1-budgeten och det nya kontraktet med TechCorp, skriv ett sammanfattningsmail till teamet", "email.create_draft", "hard", "Heavy context"),
            TestScenario("hard_weather_planning", "Kolla vädret för hela veckan i Stockholm, Göteborg och Malmö. Om det blir bra väder, planera en team-aktivitet", "weather.lookup", "hard", "Weather-based planning"),
            TestScenario("hard_memory_analysis", "Analysera alla våra möten med TechCorp de senaste 3 månaderna och skapa en rapport", "memory.query", "hard", "Memory analysis"),
            TestScenario("hard_priority_matrix", "Prioritera mina uppgifter baserat på deadline och viktighet. Skicka en lista till chefen", "email.create_draft", "hard", "Priority matrix"),
            TestScenario("hard_schedule_optimization", "Optimera min schema för nästa vecka med hänsyn till deadlines, team-möten och min produktivitetstid", "calendar.create_draft", "hard", "Schedule optimization"),
            TestScenario("hard_communication_strategy", "Utveckla en kommunikationsstrategi för det nya projektet och dela den med stakeholders", "email.create_draft", "hard", "Communication strategy"),
            TestScenario("hard_risk_assessment", "Utvärdera riskerna med det nya kontraktet och skapa en risk-matrix", "email.create_draft", "hard", "Risk assessment"),
            TestScenario("hard_performance_review", "Förbered mig för min årsutvärdering genom att sammanställa mina prestationer och mål", "memory.query", "hard", "Performance review"),
            TestScenario("hard_calendar_complex", "Boka möte med alla utvecklare och projektledare för sprint-planering nästa vecka", "calendar.create_draft", "hard", "Complex calendar booking"),
            TestScenario("hard_email_complex", "Skicka en detaljerad rapport om projektstatus till alla stakeholders med specifika rekommendationer", "email.create_draft", "hard", "Complex email"),
            TestScenario("hard_weather_complex", "Analysera vädret för hela månaden och planera bästa tid för team-retreat", "weather.lookup", "hard", "Complex weather analysis"),
            TestScenario("hard_memory_complex", "Sök igenom alla våra diskussioner om AI-integration och sammanfatta viktiga beslut", "memory.query", "hard", "Complex memory search"),
            TestScenario("hard_none_complex", "Jag är inte säker på vad jag vill göra, kan du hjälpa mig tänka igenom detta?", "none", "hard", "Complex uncertainty"),
        ]
    
    async def run_single_test(self, scenario: TestScenario) -> TestResult:
        """Run a single test scenario"""
        start_time = time.perf_counter()
        
        payload = {
            "v": "1",
            "session_id": f"{self.session_id}-{scenario.name}",
            "lang": "sv",
            "message": scenario.message,
            "force_route": "planner"  # Force planner route for all tests
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",  # Use working chat endpoint
                    headers={"Content-Type": "application/json", "Authorization": "Bearer test-key-123"},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data = await response.json()
                    
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Parse response to extract tool
                    tool = "none"
                    schema_ok = False
                    try:
                        if data.get("response"):
                            response_data = json.loads(data["response"])
                            tool = response_data.get("tool", "none")
                            schema_ok = True
                    except (json.JSONDecodeError, KeyError):
                        pass
                    
                    return TestResult(
                        scenario=scenario,
                        latency_ms=latency_ms,
                        model_used=data.get("model_used", "unknown"),
                        tool=tool,
                        schema_ok=schema_ok,
                        fallback_used=data.get("model_used") == "fallback",
                        response=data.get("response", ""),
                        success=tool == scenario.expected_tool
                    )
                    
        except Exception as e:
            return TestResult(
                scenario=scenario,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                model_used="error",
                tool="error",
                schema_ok=False,
                fallback_used=True,
                response=str(e),
                success=False
            )
    
    async def run_all_tests(self) -> None:
        """Run all 50 test scenarios"""
        print(f"🚀 Starting Planner Stress Test - {len(self.scenarios)} scenarios")
        print(f"Session ID: {self.session_id}")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)
        
        # Run tests with small delay between them
        for i, scenario in enumerate(self.scenarios, 1):
            print(f"[{i:2d}/50] {scenario.complexity.upper():5s} | {scenario.name:<25s} | {scenario.message[:40]}...")
            
            result = await self.run_single_test(scenario)
            self.results.append(result)
            
            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.1)
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("📊 PLANNER STRESS TEST SUMMARY")
        print("=" * 60)
        
        # Overall stats
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        schema_ok_tests = sum(1 for r in self.results if r.schema_ok)
        fallback_tests = sum(1 for r in self.results if r.fallback_used)
        
        latencies = [r.latency_ms for r in self.results if r.latency_ms > 0]
        
        print(f"📈 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Success Rate: {successful_tests/total_tests*100:.1f}% ({successful_tests}/{total_tests})")
        print(f"   Schema OK Rate: {schema_ok_tests/total_tests*100:.1f}% ({schema_ok_tests}/{total_tests})")
        print(f"   Fallback Rate: {fallback_tests/total_tests*100:.1f}% ({fallback_tests}/{total_tests})")
        
        if latencies:
            print(f"   Latency P50: {statistics.median(latencies):.0f}ms")
            print(f"   Latency P95: {statistics.quantiles(latencies, n=20)[18]:.0f}ms")
            print(f"   Latency P99: {statistics.quantiles(latencies, n=100)[98]:.0f}ms")
            print(f"   Latency Min: {min(latencies):.0f}ms")
            print(f"   Latency Max: {max(latencies):.0f}ms")
        
        # By complexity
        print(f"\n📊 By Complexity:")
        for complexity in ["easy", "medium", "hard"]:
            complexity_results = [r for r in self.results if r.scenario.complexity == complexity]
            if complexity_results:
                success_rate = sum(1 for r in complexity_results if r.success) / len(complexity_results) * 100
                schema_rate = sum(1 for r in complexity_results if r.schema_ok) / len(complexity_results) * 100
                avg_latency = statistics.mean([r.latency_ms for r in complexity_results if r.latency_ms > 0])
                print(f"   {complexity.upper():5s}: {success_rate:5.1f}% success, {schema_rate:5.1f}% schema_ok, {avg_latency:5.0f}ms avg")
        
        # Tool distribution
        print(f"\n🔧 Tool Distribution:")
        tool_counts = {}
        for result in self.results:
            tool = result.tool
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        for tool, count in sorted(tool_counts.items()):
            percentage = count / total_tests * 100
            print(f"   {tool:<20s}: {count:2d} ({percentage:5.1f}%)")
        
        # Failed tests
        failed_tests = [r for r in self.results if not r.success]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for result in failed_tests:
                print(f"   {result.scenario.name}: expected '{result.scenario.expected_tool}', got '{result.tool}'")
        
        # SLO Compliance
        print(f"\n🎯 SLO Compliance:")
        schema_ok_rate = schema_ok_tests / total_tests * 100
        fallback_rate = fallback_tests / total_tests * 100
        p95_latency = statistics.quantiles(latencies, n=20)[18] if latencies else 0
        
        print(f"   Schema OK ≥99%: {'✅' if schema_ok_rate >= 99 else '❌'} ({schema_ok_rate:.1f}%)")
        print(f"   Fallback ≤1%: {'✅' if fallback_rate <= 1 else '❌'} ({fallback_rate:.1f}%)")
        print(f"   P95 Latency <900ms: {'✅' if p95_latency < 900 else '❌'} ({p95_latency:.0f}ms)")
        
        # Overall verdict
        all_slo_met = schema_ok_rate >= 99 and fallback_rate <= 1 and p95_latency < 900
        print(f"\n🏆 Overall Verdict: {'✅ PASS' if all_slo_met else '❌ FAIL'}")
        
        # Save results
        self.save_results()
    
    def save_results(self) -> None:
        """Save detailed results to file"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"data/tests/planner_stress_test_{timestamp}.json"
        
        # Ensure directory exists
        import os
        os.makedirs("data/tests", exist_ok=True)
        
        # Prepare data for JSON
        results_data = []
        for result in self.results:
            results_data.append({
                "scenario_name": result.scenario.name,
                "scenario_message": result.scenario.message,
                "scenario_complexity": result.scenario.complexity,
                "expected_tool": result.scenario.expected_tool,
                "actual_tool": result.tool,
                "latency_ms": result.latency_ms,
                "model_used": result.model_used,
                "schema_ok": result.schema_ok,
                "fallback_used": result.fallback_used,
                "success": result.success,
                "response": result.response,
                "timestamp": datetime.now().isoformat()
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "test_session": self.session_id,
                "total_tests": len(self.results),
                "timestamp": datetime.now().isoformat(),
                "results": results_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")

async def main():
    """Main function"""
    import sys
    
    base_url = "http://localhost:18000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    tester = PlannerStressTest(base_url)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
