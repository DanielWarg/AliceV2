#!/usr/bin/env python3
"""
Generate 50 regression test scenarios for Alice v2 eval harness
"""

import os
from typing import Any, Dict

import yaml

# Test scenarios by category
EASY_SCENARIOS = [
    {
        "id": "001",
        "tags": ["EASY", "time"],
        "prompt_sv": "Vad är klockan?",
        "expected_intent": "time.now",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "002",
        "tags": ["EASY", "weather"],
        "prompt_sv": "Vad är vädret i Stockholm?",
        "expected_intent": "weather.lookup",
        "expected_tools": ["weather.lookup"],
        "max_latency_ms": 200,
    },
    {
        "id": "003",
        "tags": ["EASY", "time"],
        "prompt_sv": "Hur mycket är klockan?",
        "expected_intent": "time.now",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "004",
        "tags": ["EASY", "weather"],
        "prompt_sv": "Vädret i Göteborg?",
        "expected_intent": "weather.lookup",
        "expected_tools": ["weather.lookup"],
        "max_latency_ms": 200,
    },
    {
        "id": "005",
        "tags": ["EASY", "greeting"],
        "prompt_sv": "Hej!",
        "expected_intent": "greeting.hello",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "006",
        "tags": ["EASY", "greeting"],
        "prompt_sv": "God morgon",
        "expected_intent": "greeting.hello",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "007",
        "tags": ["EASY", "time"],
        "prompt_sv": "Klockan?",
        "expected_intent": "time.now",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "008",
        "tags": ["EASY", "weather"],
        "prompt_sv": "Temperatur i Malmö",
        "expected_intent": "weather.lookup",
        "expected_tools": ["weather.lookup"],
        "max_latency_ms": 200,
    },
    {
        "id": "009",
        "tags": ["EASY", "greeting"],
        "prompt_sv": "Tjena",
        "expected_intent": "greeting.hello",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "010",
        "tags": ["EASY", "time"],
        "prompt_sv": "Vilken tid är det?",
        "expected_intent": "time.now",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "011",
        "tags": ["EASY", "weather"],
        "prompt_sv": "Regnar det i Uppsala?",
        "expected_intent": "weather.lookup",
        "expected_tools": ["weather.lookup"],
        "max_latency_ms": 200,
    },
    {
        "id": "012",
        "tags": ["EASY", "greeting"],
        "prompt_sv": "Hallå",
        "expected_intent": "greeting.hello",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "013",
        "tags": ["EASY", "time"],
        "prompt_sv": "Tid nu",
        "expected_intent": "time.now",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "014",
        "tags": ["EASY", "weather"],
        "prompt_sv": "Vädret idag",
        "expected_intent": "weather.lookup",
        "expected_tools": ["weather.lookup"],
        "max_latency_ms": 200,
    },
    {
        "id": "015",
        "tags": ["EASY", "greeting"],
        "prompt_sv": "God kväll",
        "expected_intent": "greeting.hello",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "016",
        "tags": ["EASY", "time"],
        "prompt_sv": "Nuvarande tid",
        "expected_intent": "time.now",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "017",
        "tags": ["EASY", "weather"],
        "prompt_sv": "Vädret i Linköping",
        "expected_intent": "weather.lookup",
        "expected_tools": ["weather.lookup"],
        "max_latency_ms": 200,
    },
    {
        "id": "018",
        "tags": ["EASY", "greeting"],
        "prompt_sv": "Trevligt att träffas",
        "expected_intent": "greeting.hello",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "019",
        "tags": ["EASY", "time"],
        "prompt_sv": "Vad är tiden?",
        "expected_intent": "time.now",
        "expected_tools": [],
        "max_latency_ms": 200,
    },
    {
        "id": "020",
        "tags": ["EASY", "weather"],
        "prompt_sv": "Temperatur nu",
        "expected_intent": "weather.lookup",
        "expected_tools": ["weather.lookup"],
        "max_latency_ms": 200,
    },
]

MEDIUM_SCENARIOS = [
    {
        "id": "021",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Boka ett möte med Anna imorgon kl 14:00",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "022",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Skicka ett mail till chef@företag.se med ämnet 'Rapport klar'",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "023",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Schemalägg ett möte med teamet på fredag",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "024",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Maila kunden om projektstatus",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "025",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Boka konferensrum för nästa vecka",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "026",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Skriv ett mail till HR om semester",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "027",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Planera lunchmöte med kollegan",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "028",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Maila support om tekniskt problem",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "029",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Boka utvecklingssamtal med chefen",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "030",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Skicka rapport till projektledaren",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "031",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Schemalägg kundmöte nästa månad",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "032",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Maila teamet om veckans mål",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "033",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Boka retrospektiv för sprinten",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "034",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Skicka feedback till kollegan",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "035",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Planera workshop med extern konsult",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "036",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Maila leverantör om försening",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "037",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Boka demo för potentiell kund",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "038",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Skicka agenda för nästa möte",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "039",
        "tags": ["MEDIUM", "calendar"],
        "prompt_sv": "Schemalägg kodgranskning",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 500,
    },
    {
        "id": "040",
        "tags": ["MEDIUM", "email"],
        "prompt_sv": "Maila om säkerhetsuppdatering",
        "expected_intent": "email.create_draft",
        "expected_tools": ["email.create_draft"],
        "max_latency_ms": 500,
    },
]

HARD_SCENARIOS = [
    {
        "id": "041",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Analysera mina senaste 10 mail och skapa en sammanfattning av de viktigaste punkterna, boka sedan ett möte med teamet för att diskutera resultaten",
        "expected_intent": "memory.query",
        "expected_tools": ["memory.query", "calendar.create_draft"],
        "max_latency_ms": 1500,
    },
    {
        "id": "042",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Gå igenom min kalender för denna vecka och identifiera konflikter, skicka sedan ett mail till berörda personer med förslag på alternativa tider",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft", "email.create_draft"],
        "max_latency_ms": 1500,
    },
    {
        "id": "043",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Skapa en rapport baserad på mina senaste projektmail, analysera trender och rekommendera förbättringar för nästa sprint",
        "expected_intent": "memory.query",
        "expected_tools": ["memory.query"],
        "max_latency_ms": 1500,
    },
    {
        "id": "044",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Planera en komplett projektkickoff med agenda, deltagarlista och uppföljningsmöte, skicka inbjudningar till alla berörda",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft", "email.create_draft"],
        "max_latency_ms": 1500,
    },
    {
        "id": "045",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Analysera min kommunikation med kunden under denna månad och föreslå förbättringar för framtida interaktioner",
        "expected_intent": "memory.query",
        "expected_tools": ["memory.query"],
        "max_latency_ms": 1500,
    },
    {
        "id": "046",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Skapa en veckoplanering baserad på mina deadlines och prioriteringar, inklusive buffertar för oväntade uppgifter",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 1500,
    },
    {
        "id": "047",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Gå igenom mina senaste kodgranskningar och identifiera vanliga mönster, skapa en guide för teamet",
        "expected_intent": "memory.query",
        "expected_tools": ["memory.query"],
        "max_latency_ms": 1500,
    },
    {
        "id": "048",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Planera en komplett konferensresa med transport, boende och möten, inklusive backup-planer",
        "expected_intent": "calendar.create_draft",
        "expected_tools": ["calendar.create_draft"],
        "max_latency_ms": 1500,
    },
    {
        "id": "049",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Analysera min produktivitet under de senaste veckorna och föreslå optimeringar för min arbetsdag",
        "expected_intent": "memory.query",
        "expected_tools": ["memory.query"],
        "max_latency_ms": 1500,
    },
    {
        "id": "050",
        "tags": ["HARD", "complex"],
        "prompt_sv": "Skapa en strategisk plan för nästa kvartal baserat på mina mål och tidigare prestationer",
        "expected_intent": "memory.query",
        "expected_tools": ["memory.query"],
        "max_latency_ms": 1500,
    },
]


def create_scenario(scenario_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a complete scenario with defaults"""
    return {
        "id": scenario_data["id"],
        "tags": scenario_data["tags"],
        "prompt_sv": scenario_data["prompt_sv"],
        "expected_intent": scenario_data["expected_intent"],
        "expected_tools": scenario_data["expected_tools"],
        "max_latency_ms": scenario_data["max_latency_ms"],
        "schema_ok_first": True if "EASY" in scenario_data["tags"] else False,
        "fallback_allowed": "HARD" in scenario_data["tags"],
    }


def generate_regression_tests():
    """Generate all 50 regression test files"""

    # Create eval/regression directory
    os.makedirs("eval/regression", exist_ok=True)

    # Combine all scenarios
    all_scenarios = EASY_SCENARIOS + MEDIUM_SCENARIOS + HARD_SCENARIOS

    print(f"Generating {len(all_scenarios)} regression test scenarios...")

    for scenario_data in all_scenarios:
        scenario = create_scenario(scenario_data)

        # Create filename
        filename = f"eval/regression/{scenario['id']}_{scenario['tags'][1].lower()}_{scenario['tags'][0].lower()}.yml"

        # Write YAML file
        with open(filename, "w", encoding="utf-8") as f:
            yaml.dump(
                scenario,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        print(f"✅ Created {filename}")

    print(f"\n🎉 Generated {len(all_scenarios)} regression test scenarios:")
    print(f"   - EASY: {len(EASY_SCENARIOS)} scenarios")
    print(f"   - MEDIUM: {len(MEDIUM_SCENARIOS)} scenarios")
    print(f"   - HARD: {len(HARD_SCENARIOS)} scenarios")


if __name__ == "__main__":
    generate_regression_tests()
