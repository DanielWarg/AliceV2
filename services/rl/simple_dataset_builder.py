#!/usr/bin/env python3
"""
🎯 Simplified Dataset Builder för Night Test Telemetri
Bygger träningsdata direkt från våra 240+ events för ToolSelector LoRA
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RL_DIR = DATA_DIR / "rl"
RL_DIR.mkdir(exist_ok=True, parents=True)


def extract_episodes_from_night_test() -> List[Dict[str, Any]]:
    """Extrahera träningsepisoder från nattestets telemetri"""
    
    telemetry_file = DATA_DIR / "telemetry" / "2025-09-07" / "events_2025-09-07.jsonl"
    
    if not telemetry_file.exists():
        print(f"❌ Telemetry file not found: {telemetry_file}")
        return []
    
    print(f"📊 Processing night test telemetry: {telemetry_file}")
    
    episodes = []
    
    with open(telemetry_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                event = json.loads(line.strip())
                
                # Varje rad är redan en komplett episode i detta format
                episode = create_episode_from_telemetry_event(event)
                if episode:
                    episodes.append(episode)
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON error line {line_num}: {e}")
                continue
    
    print(f"✅ Extracted {len(episodes)} episodes from telemetry")
    return episodes


def create_episode_from_telemetry_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Skapa en träningsepisod från en telemetri-event"""
    
    # Extrahera huvuddata
    session_id = event.get('session_id', '')
    input_text = event.get('input_text', '')
    output_text = event.get('output_text', '')
    
    if not input_text or not session_id:
        return None
    
    # Parse output för att få intent och tool info
    tool_used = "none"
    intent_detected = "unknown"
    success = True
    
    try:
        if output_text:
            output_data = json.loads(output_text)
            intent_detected = output_data.get('intent', 'unknown')
            tool_used = output_data.get('tool', 'none') or 'none'
            
            # Success baserat på om systemet förstod intentionen
            if intent_detected == "none" or "förstår inte" in output_data.get('render_instruction', {}).get('content', ''):
                success = False
    except:
        pass
    
    # Prestanda från telemetri
    latency_ms = event.get('e2e_full_ms', 0)
    route = event.get('route', 'micro')
    guardian_state = event.get('guardian_state', 'NORMAL')
    energy_used = event.get('energy_wh', 0.0)
    
    # Klassificera rätt intent från svenska text
    expected_intent = classify_swedish_intent(input_text)
    
    # Success = systemet identifierade rätt intent ELLER producerade användbar output
    actual_success = (
        intent_detected != "none" and 
        intent_detected != "unknown" and
        "förstår inte" not in output_text
    ) or expected_intent == intent_detected
    
    # Tool calls (ingen i dessa data, men kan extrapolera)
    tool_calls = 1 if tool_used != "none" and tool_used else 0
    
    # Reward
    reward = calculate_reward(expected_intent, latency_ms, actual_success, tool_calls)
    
    episode = {
        'episode_id': f"night_test_{session_id}",
        'session_id': session_id,
        'timestamp': event.get('ts', ''),
        'user_input': input_text,
        'output_text': output_text,
        'intent': expected_intent,
        'intent_detected': intent_detected,
        'lang': event.get('lang', 'sv'),
        'success': actual_success,
        'tool_used': tool_used,
        'tool_calls': tool_calls,
        'route': route,
        'total_latency_ms': latency_ms,
        'energy_wh': energy_used,
        'guardian_state': guardian_state,
        'reward': reward,
        'fibonacci_optimized': latency_ms < 250 and latency_ms > 0,
        'trace_id': event.get('trace_id', '')
    }
    
    return episode


def create_episode_from_events_old(session_id: str, events: List[Dict]) -> Dict[str, Any]:
    """Skapa en träningsepisod från session-events"""
    
    if not events:
        return None
    
    # Hitta input och response
    input_event = None
    response_events = []
    
    for event in events:
        event_type = event.get('type', '').lower()
        
        if 'input' in event_type or 'message' in event.get('data', {}):
            input_event = event
        elif 'response' in event_type or 'completion' in event_type:
            response_events.append(event)
    
    if not input_event:
        return None
    
    # Extrahera svenska text från input
    user_input = ""
    if 'data' in input_event:
        user_input = input_event['data'].get('message', '')
    elif 'message' in input_event:
        user_input = input_event.get('message', '')
    
    if not user_input:
        return None
    
    # Klassificera intent baserat på svenska text
    intent = classify_swedish_intent(user_input)
    
    # Beräkna prestanda från events
    total_latency = 0
    success = True
    tool_calls = 0
    
    for event in events:
        if event.get('latency_ms'):
            total_latency += event.get('latency_ms', 0)
        if event.get('type') == 'tool_call':
            tool_calls += 1
        if event.get('error') or not event.get('success', True):
            success = False
    
    # Genomsnittlig latency från nattesten var 168ms
    if total_latency == 0:
        total_latency = 168  # Default från våra mätningar
    
    # Reward baserat på vår Fibonacci-optimering
    reward = calculate_reward(intent, total_latency, success, tool_calls)
    
    episode = {
        'episode_id': f"night_test_{session_id}_{len(events)}",
        'session_id': session_id,
        'timestamp': input_event.get('timestamp', datetime.now().isoformat()),
        'user_input': user_input,
        'intent': intent,
        'lang': 'sv',  # Alla våra test-queries är svenska
        'success': success,
        'tool_calls': tool_calls,
        'total_latency_ms': total_latency,
        'reward': reward,
        'fibonacci_optimized': total_latency < 250,  # Under vårt target
        'events_count': len(events)
    }
    
    return episode


def classify_swedish_intent(text: str) -> str:
    """Klassificera intent från svenska test-queries"""
    
    text_lower = text.lower()
    
    # Baserat på våra 10 test-queries från A-Z testet
    if any(word in text_lower for word in ['klockan', 'tid', 'datum', 'dag']):
        return 'time_info'
    elif any(word in text_lower for word in ['mail', 'meddelande', 'skicka']):
        return 'email'
    elif any(word in text_lower for word in ['plus', 'beräkna', 'räkna', '1234', '5678']):
        return 'calculation'
    elif any(word in text_lower for word in ['temperatur', 'väder', 'ute']):
        return 'weather'
    elif any(word in text_lower for word in ['schema', 'möte', 'påminnelse', 'lunch']):
        return 'calendar'
    elif any(word in text_lower for word in ['uppgifter', 'avslutade', 'lista']):
        return 'tasks'
    elif any(word in text_lower for word in ['lampa', 'stäng av', 'vardagsrum']):
        return 'smart_home'
    elif any(word in text_lower for word in ['historia', 'rolig', 'berätta']):
        return 'entertainment'
    elif any(word in text_lower for word in ['hjälp', 'kan du']):
        return 'help'
    else:
        return 'general'


def calculate_reward(intent: str, latency_ms: float, success: bool, tool_calls: int) -> float:
    """Beräkna reward för träning baserat på Fibonacci-principer"""
    
    reward = 0.0
    
    # Success reward (viktigast)
    if success:
        reward += 10.0
    else:
        reward -= 5.0
    
    # Latency penalty (Fibonacci-optimering)
    if latency_ms <= 168:  # Under vårt genomsnitt
        reward += 3.0
    elif latency_ms <= 250:  # Under vårt target
        reward += 1.0
    elif latency_ms > 500:  # Långsamt
        reward -= 2.0
    
    # Tool efficiency (Golden Ratio inspiration)
    if tool_calls == 1:
        reward += 2.0  # Perfekt effektivitet
    elif tool_calls == 2:
        reward += 1.0  # Bra effektivitet
    elif tool_calls == 0:
        reward -= 1.0  # Ingen action
    elif tool_calls > 3:
        reward -= 1.0  # Ineffektiv
    
    # Intent-specific bonuses
    intent_bonuses = {
        'time_info': 1.0,     # Enkla queries bör vara snabba
        'calculation': 1.5,   # Matematik är deterministisk
        'email': 0.5,        # Komplexa queries OK att ta tid
        'general': 0.0        # Neutral
    }
    
    reward += intent_bonuses.get(intent, 0.0)
    
    return round(reward, 2)


def create_training_splits(episodes: List[Dict]) -> tuple:
    """Skapa train/eval splits för träning"""
    
    # Sortera på kvalitet (reward) för bästa träningsordning  
    episodes.sort(key=lambda x: x.get('reward', 0), reverse=True)
    
    # 80/20 split
    split_idx = int(len(episodes) * 0.8)
    
    train_episodes = episodes[:split_idx]
    eval_episodes = episodes[split_idx:]
    
    return train_episodes, eval_episodes


def main():
    """Bygg förenklat dataset från nattestets telemetri"""
    
    print("🎯 Building RL Dataset från Night Test Telemetri")
    
    # Extrahera episodes från nattesten
    episodes = extract_episodes_from_night_test()
    
    if not episodes:
        print("❌ No episodes extracted!")
        return
    
    print(f"📊 Total episodes: {len(episodes)}")
    
    # Statistik
    successful_episodes = sum(1 for ep in episodes if ep.get('success', False))
    avg_reward = sum(ep.get('reward', 0) for ep in episodes) / len(episodes) if episodes else 0
    fibonacci_optimized = sum(1 for ep in episodes if ep.get('fibonacci_optimized', False))
    
    print(f"✅ Successful episodes: {successful_episodes}/{len(episodes)} ({successful_episodes/len(episodes)*100:.1f}%)")
    print(f"📈 Average reward: {avg_reward:.2f}")
    print(f"🎯 Fibonacci optimized: {fibonacci_optimized}/{len(episodes)} ({fibonacci_optimized/len(episodes)*100:.1f}%)")
    
    # Skapa splits
    train_episodes, eval_episodes = create_training_splits(episodes)
    
    # Spara dataset
    output_dir = RL_DIR / "v1"
    output_dir.mkdir(exist_ok=True)
    
    # Train set
    train_file = output_dir / "night_test_episodes_train.jsonl"
    with open(train_file, 'w', encoding='utf-8') as f:
        for episode in train_episodes:
            f.write(json.dumps(episode, ensure_ascii=False) + '\n')
    
    # Eval set  
    eval_file = output_dir / "night_test_episodes_eval.jsonl"
    with open(eval_file, 'w', encoding='utf-8') as f:
        for episode in eval_episodes:
            f.write(json.dumps(episode, ensure_ascii=False) + '\n')
    
    # Metadata
    metadata = {
        'dataset_name': 'alice_night_test_v1',
        'created': datetime.now().isoformat(),
        'source': 'night_test_telemetry_2025-09-07',
        'total_episodes': len(episodes),
        'train_episodes': len(train_episodes),
        'eval_episodes': len(eval_episodes),
        'successful_episodes': successful_episodes,
        'success_rate': successful_episodes / len(episodes),
        'avg_reward': avg_reward,
        'fibonacci_optimized_rate': fibonacci_optimized / len(episodes),
        'data_quality': 'high' if avg_reward > 5.0 else 'medium',
        'ready_for_training': len(episodes) >= 10
    }
    
    metadata_file = output_dir / "night_test_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Dataset saved:")
    print(f"  Train: {train_file} ({len(train_episodes)} episodes)")  
    print(f"  Eval:  {eval_file} ({len(eval_episodes)} episodes)")
    print(f"  Meta:  {metadata_file}")
    
    if metadata['ready_for_training']:
        print(f"\n🚀 Dataset ready for ToolSelector LoRA training!")
        print(f"Run: python3 services/toolselector/train_lora.py")
    else:
        print(f"\n⚠️ Dataset too small for reliable training (need >10 episodes)")
    
    return len(episodes)


if __name__ == "__main__":
    main()