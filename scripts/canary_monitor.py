#!/usr/bin/env python3
"""
Canary Monitor - 24h supervision with automatic escalation and rollback
Runs in background monitoring shadow stats and managing canary percentage
"""

import asyncio
import aiohttp
import json
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

class CanaryMonitor:
    def __init__(self):
        self.base_url = "http://localhost:18000"
        self.session_id = f"canary-monitor-{int(time.time())}"
        self.start_time = datetime.now()
        self.current_canary_percent = 5.0
        self.escalation_history = []
        self.rollback_history = []
        
        # Quality gates (rolling 30 min)
        self.gates = {
            "schema_ok_first_v2": {"min": 0.975, "current": 0.0, "status": "unknown"},
            "intent_match": {"min": 0.95, "current": 0.0, "status": "unknown"},
            "tool_choice_same": {"min": 0.95, "current": 0.0, "status": "unknown"},
            "latency_delta_p95": {"max": 150.0, "current": 0.0, "status": "unknown"},
            "canary_routed_rate": {"target": 0.05, "current": 0.0, "status": "unknown"}
        }
        
        # Escalation schedule
        self.escalation_schedule = [
            {"time_hours": 3, "target_percent": 10.0},
            {"time_hours": 12, "target_percent": 15.0}
        ]
    
    async def fetch_shadow_stats(self) -> Dict:
        """Fetch current shadow statistics"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/shadow/stats") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"❌ Failed to fetch shadow stats: {response.status}")
                        return {}
        except Exception as e:
            print(f"❌ Error fetching shadow stats: {e}")
            return {}
    
    def update_gates(self, stats: Dict):
        """Update quality gates with current metrics"""
        self.gates["schema_ok_first_v2"]["current"] = stats.get("schema_ok_rate", 0.0)
        self.gates["intent_match"]["current"] = stats.get("intent_match_rate", 0.0)
        self.gates["tool_choice_same"]["current"] = stats.get("tool_choice_same_rate", 0.0)
        self.gates["latency_delta_p95"]["current"] = abs(stats.get("avg_latency_delta_ms", 0.0))
        self.gates["canary_routed_rate"]["current"] = stats.get("canary_routed", 0) / max(stats.get("total_requests", 1), 1)
        
        # Update status
        for gate_name, gate in self.gates.items():
            if "min" in gate:
                gate["status"] = "green" if gate["current"] >= gate["min"] else "red"
            elif "max" in gate:
                gate["status"] = "green" if gate["current"] <= gate["max"] else "red"
            elif "target" in gate:
                # Allow some tolerance around target
                tolerance = 0.02
                target = gate["target"]
                current = gate["current"]
                gate["status"] = "green" if abs(current - target) <= tolerance else "yellow"
    
    def check_escalation(self) -> Optional[float]:
        """Check if we should escalate canary percentage"""
        elapsed_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        for escalation in self.escalation_schedule:
            if elapsed_hours >= escalation["time_hours"] and self.current_canary_percent < escalation["target_percent"]:
                # Check if all gates are green
                all_green = all(gate["status"] == "green" for gate in self.gates.values())
                if all_green:
                    return escalation["target_percent"]
        
        return None
    
    def check_rollback(self) -> Optional[str]:
        """Check if we should rollback canary"""
        rollback_reasons = []
        
        if self.gates["schema_ok_first_v2"]["status"] == "red":
            rollback_reasons.append("schema_fail")
        if self.gates["intent_match"]["status"] == "red":
            rollback_reasons.append("intent_mismatch")
        if self.gates["latency_delta_p95"]["status"] == "red":
            rollback_reasons.append("latency_regress")
        
        if rollback_reasons:
            return "|".join(rollback_reasons)
        
        return None
    
    async def update_canary_percent(self, new_percent: float, reason: str):
        """Update canary percentage via environment variable"""
        try:
            # Update docker-compose environment variable
            os.environ["PLANNER_CANARY_PERCENT"] = str(new_percent)
            
            # Restart orchestrator to pick up new value
            import subprocess
            subprocess.run(["docker", "compose", "restart", "orchestrator"], check=True)
            
            self.current_canary_percent = new_percent
            
            if new_percent > 5.0:
                self.escalation_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "new_percent": new_percent,
                    "reason": reason
                })
                print(f"🚀 ESCALATED: Canary to {new_percent}% ({reason})")
            elif new_percent == 0.0:
                self.rollback_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "reason": reason
                })
                print(f"🛑 ROLLBACK: Canary to 0% ({reason})")
            
        except Exception as e:
            print(f"❌ Failed to update canary percent: {e}")
    
    def print_status(self):
        """Print current status"""
        elapsed = datetime.now() - self.start_time
        elapsed_str = f"{elapsed.total_seconds()/3600:.1f}h"
        
        print(f"\n🕐 Canary Monitor Status ({elapsed_str})")
        print(f"📊 Current Canary: {self.current_canary_percent}%")
        print("=" * 60)
        
        for gate_name, gate in self.gates.items():
            status_emoji = "🟢" if gate["status"] == "green" else "🔴" if gate["status"] == "red" else "🟡"
            current = gate["current"]
            
            if "min" in gate:
                print(f"{status_emoji} {gate_name}: {current:.3f} (min: {gate['min']:.3f})")
            elif "max" in gate:
                print(f"{status_emoji} {gate_name}: {current:.1f}ms (max: {gate['max']:.1f}ms)")
            elif "target" in gate:
                print(f"{status_emoji} {gate_name}: {current:.1%} (target: {gate['target']:.1%})")
        
        print("=" * 60)
        
        if self.escalation_history:
            print("🚀 Escalation History:")
            for esc in self.escalation_history[-3:]:
                print(f"  {esc['timestamp']}: {esc['new_percent']}% ({esc['reason']})")
        
        if self.rollback_history:
            print("🛑 Rollback History:")
            for roll in self.rollback_history[-3:]:
                print(f"  {roll['timestamp']}: 0% ({roll['reason']})")
    
    async def run_monitor(self):
        """Main monitoring loop"""
        print("🚀 Starting Canary Monitor (24h supervision)")
        print(f"📊 Initial canary: {self.current_canary_percent}%")
        print("⏰ Monitoring every 60 seconds")
        print("=" * 60)
        
        while True:
            try:
                # Fetch current stats
                stats = await self.fetch_shadow_stats()
                if not stats:
                    print("❌ No stats available, retrying...")
                    await asyncio.sleep(60)
                    continue
                
                # Update gates
                self.update_gates(stats)
                
                # Check for rollback first
                rollback_reason = self.check_rollback()
                if rollback_reason:
                    await self.update_canary_percent(0.0, f"auto_rollback_{rollback_reason}")
                    print(f"🛑 AUTO ROLLBACK: {rollback_reason}")
                
                # Check for escalation
                elif self.current_canary_percent < 15.0:
                    new_percent = self.check_escalation()
                    if new_percent:
                        await self.update_canary_percent(new_percent, "auto_escalation")
                
                # Print status
                self.print_status()
                
                # Save checkpoint
                self.save_checkpoint(stats)
                
                # Wait 60 seconds
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                print("\n🛑 Canary Monitor stopped by user")
                break
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                await asyncio.sleep(60)
    
    def save_checkpoint(self, stats: Dict):
        """Save monitoring checkpoint"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "canary_percent": self.current_canary_percent,
            "gates": self.gates,
            "stats": stats,
            "escalation_history": self.escalation_history,
            "rollback_history": self.rollback_history
        }
        
        filename = f"data/monitoring/canary_checkpoint_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"
        os.makedirs("data/monitoring", exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        # Keep only last 24 checkpoints
        import glob
        checkpoints = glob.glob("data/monitoring/canary_checkpoint_*.json")
        checkpoints.sort()
        if len(checkpoints) > 24:
            for old_checkpoint in checkpoints[:-24]:
                os.remove(old_checkpoint)

async def main():
    """Main function"""
    monitor = CanaryMonitor()
    await monitor.run_monitor()

if __name__ == "__main__":
    asyncio.run(main())
