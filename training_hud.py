#!/usr/bin/env python3
"""
🧮 Alice v2 Training HUD - Interactive Chat-like Training Monitor

En modern chat-liknande interface för att monitora alla träningsaktiviteter:
- Fibonacci optimization training
- Reinforcement Learning (RL) pipeline  
- Cache bandit optimization
- Real-time metrics och progress tracking

Usage:
    python training_hud.py
    python training_hud.py --auto-start fibonacci,rl,cache
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
import signal
import sys

# Rich for beautiful terminal UI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    from rich.prompt import Prompt
except ImportError:
    print("❌ Missing dependencies. Install with: pip install rich")
    sys.exit(1)

console = Console()

class TrainingSession:
    """Representerar en aktiv träningssession"""
    
    def __init__(self, name: str, script_path: str, session_type: str):
        self.name = name
        self.script_path = script_path  
        self.session_type = session_type
        self.start_time = datetime.now()
        self.status = "starting"
        self.metrics = {}
        self.process = None
        self.log_messages = []
        self.last_update = datetime.now()
        
    def add_message(self, message: str, level: str = "info"):
        """Lägg till ett meddelande i chatten"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_messages.append({
            "time": timestamp,
            "level": level, 
            "message": message,
            "session": self.name
        })
        self.last_update = datetime.now()
        
        # Behåll endast de senaste 50 meddelandena
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]

class TrainingHUD:
    """Main HUD class för träningsmonitoring"""
    
    def __init__(self):
        self.console = Console()
        self.sessions: Dict[str, TrainingSession] = {}
        self.is_running = True
        self.refresh_interval = 1.0  # Uppdatera varje sekund
        
        # Träningstyper och deras script-paths
        self.training_types = {
            "fibonacci": {
                "name": "🧮 Fibonacci Optimization", 
                "script": "scripts/fibonacci_simple_training.py",
                "description": "Golden ratio performance optimization (φ=1.618)"
            },
            "fibonacci_loop": {
                "name": "🔄 Fibonacci Training Loop",
                "script": "scripts/fibonacci_training_loop.py", 
                "description": "Multi-phase Fibonacci training pipeline"
            },
            "rl_pipeline": {
                "name": "🤖 RL Pipeline", 
                "script": "services/rl/automate_rl_pipeline.py",
                "description": "Reinforcement learning automation"
            },
            "cache_bandit": {
                "name": "💾 Cache Bandit RL",
                "script": "services/rl/bandits/cache_bandit.py", 
                "description": "Cache optimization reinforcement learning"
            }
        }
        
        # Signal handlers för clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.is_running = False
        self.stop_all_training()
        
    def create_chat_layout(self) -> Layout:
        """Skapa chat-liknande layout"""
        layout = Layout(name="root")
        
        # Dela upp i header, main och footer
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=8)
        )
        
        # Main dela mellan sessions och chat
        layout["main"].split_row(
            Layout(name="sessions", ratio=1),
            Layout(name="chat", ratio=2)  
        )
        
        return layout
        
    def render_header(self) -> Panel:
        """Render header med overall stats"""
        active_count = len([s for s in self.sessions.values() if s.status in ["running", "starting"]])
        total_sessions = len(self.sessions)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        header_text = Text()
        header_text.append("🧮 Alice v2 Training HUD", style="bold magenta")
        header_text.append(f"  •  {active_count} aktiva / {total_sessions} totalt", style="green")  
        header_text.append(f"  •  {current_time}", style="dim")
        
        return Panel(header_text, style="blue")
        
    def render_sessions(self) -> Panel:
        """Render aktiva sessions"""
        if not self.sessions:
            return Panel("[dim]Inga aktiva träningssessions[/dim]", title="📊 Sessions", style="cyan")
            
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Status", style="green") 
        table.add_column("Uptime", style="blue")
        table.add_column("Type", style="magenta")
        
        for session in self.sessions.values():
            uptime = datetime.now() - session.start_time
            uptime_str = f"{int(uptime.total_seconds()//60)}:{int(uptime.total_seconds()%60):02d}"
            
            # Status med färgkodning
            status_style = {
                "running": "[green]●[/green] Running",
                "starting": "[yellow]●[/yellow] Starting", 
                "completed": "[blue]●[/blue] Done",
                "failed": "[red]●[/red] Failed"
            }.get(session.status, f"[dim]{session.status}[/dim]")
            
            table.add_row(
                session.name,
                status_style,
                uptime_str,
                session.session_type
            )
            
        return Panel(table, title="📊 Aktiva Sessions", style="cyan")
        
    def render_chat(self) -> Panel:
        """Render chat-feed med meddelanden från alla sessions"""
        if not any(s.log_messages for s in self.sessions.values()):
            welcome_text = Text()
            welcome_text.append("🎯 Välkommen till Alice Training HUD!\n\n", style="bold green")
            welcome_text.append("Tillgängliga kommandon:\n", style="bold")
            welcome_text.append("• start <type>  - Starta träning (fibonacci, rl_pipeline, cache_bandit)\n", style="cyan")
            welcome_text.append("• stop <name>   - Stoppa specifik session\n", style="cyan") 
            welcome_text.append("• stop-all     - Stoppa alla sessions\n", style="cyan")
            welcome_text.append("• status       - Visa detaljerad status\n", style="cyan")
            welcome_text.append("• help         - Visa hjälp\n", style="cyan")
            welcome_text.append("• quit         - Avsluta HUD\n\n", style="cyan")
            welcome_text.append("Starta din första träning med: start fibonacci", style="dim")
            
            return Panel(welcome_text, title="💬 Training Chat", style="green")
        
        # Samla alla meddelanden och sortera efter tid
        all_messages = []
        for session in self.sessions.values():
            for msg in session.log_messages[-20:]:  # Senaste 20 per session
                all_messages.append(msg)
                
        # Sortera efter tiden (senaste först för chat-känsla)
        all_messages.sort(key=lambda m: m["time"], reverse=True)
        all_messages = all_messages[:30]  # Max 30 meddelanden totalt
        
        chat_text = Text()
        
        for msg in reversed(all_messages):  # Visa äldsta först
            # Färgkoda efter level
            level_colors = {
                "info": "white",
                "success": "green", 
                "warning": "yellow",
                "error": "red",
                "debug": "dim"
            }
            color = level_colors.get(msg["level"], "white")
            
            # Session badge
            session_badge = f"[{msg['session']}]"
            chat_text.append(f"{msg['time']} ", style="dim")
            chat_text.append(f"{session_badge:12} ", style="bold cyan")
            chat_text.append(f"{msg['message']}\n", style=color)
            
        return Panel(chat_text, title="💬 Training Chat", style="green")
        
    def render_controls(self) -> Panel:
        """Render kontroll-panel"""
        help_text = Text()
        help_text.append("🎮 Kontroller: ", style="bold yellow")
        help_text.append("start <type> | stop <name> | stop-all | status | metrics | quit", style="cyan")
        help_text.append("\n📈 Metriks: ", style="bold yellow")
        
        # Visa några key metrics
        if self.sessions:
            total_runtime = sum((datetime.now() - s.start_time).total_seconds() for s in self.sessions.values())
            avg_runtime = total_runtime / len(self.sessions) / 60  # minuter
            help_text.append(f"Avg Session: {avg_runtime:.1f}min", style="green")
            
        return Panel(help_text, style="yellow")
        
    async def start_training_session(self, training_type: str, session_name: Optional[str] = None) -> bool:
        """Starta en ny träningssession"""
        if training_type not in self.training_types:
            return False
            
        config = self.training_types[training_type]
        if not session_name:
            timestamp = datetime.now().strftime("%H%M%S")
            session_name = f"{training_type}_{timestamp}"
            
        # Kontrollera att script existerar
        script_path = config["script"]
        if not Path(script_path).exists():
            return False
            
        # Skapa session
        session = TrainingSession(session_name, script_path, config["name"])
        self.sessions[session_name] = session
        
        session.add_message(f"🚀 Startar {config['name']}", "info")
        session.add_message(f"📄 Script: {script_path}", "debug")
        
        # Starta process i bakgrunden
        try:
            # Aktivera virtual environment och kör script
            cmd = f"source .venv/bin/activate && python {script_path}"
            session.process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            session.status = "running"
            session.add_message("✅ Träning startad", "success")
            
            # Starta monitoring i separat thread
            monitor_thread = threading.Thread(
                target=self._monitor_session,
                args=(session,),
                daemon=True
            )
            monitor_thread.start()
            
            return True
            
        except Exception as e:
            session.status = "failed"
            session.add_message(f"❌ Fel vid start: {str(e)}", "error")
            return False
            
    def _monitor_session(self, session: TrainingSession):
        """Monitora en träningssession i bakgrunden"""
        try:
            while session.process and session.process.poll() is None:
                # Läs output från processen
                if session.process.stdout:
                    line = session.process.stdout.readline()
                    if line:
                        clean_line = line.strip()
                        if clean_line:
                            # Parsea för att hitta intressant data
                            if "error" in clean_line.lower() or "fail" in clean_line.lower():
                                session.add_message(clean_line, "error")
                            elif "success" in clean_line.lower() or "✅" in clean_line:
                                session.add_message(clean_line, "success") 
                            elif "warning" in clean_line.lower() or "⚠️" in clean_line:
                                session.add_message(clean_line, "warning")
                            else:
                                session.add_message(clean_line, "info")
                                
                time.sleep(0.1)  # Kort paus för att inte spamma
                
            # Process har slutat
            if session.process:
                return_code = session.process.poll()
                if return_code == 0:
                    session.status = "completed"
                    session.add_message("🎉 Träning slutförd", "success")
                else:
                    session.status = "failed"
                    session.add_message(f"❌ Träning misslyckades (kod: {return_code})", "error")
                    
        except Exception as e:
            session.status = "failed"
            session.add_message(f"❌ Monitor fel: {str(e)}", "error")
            
    def stop_training_session(self, session_name: str) -> bool:
        """Stoppa en specifik träningssession"""
        if session_name not in self.sessions:
            return False
            
        session = self.sessions[session_name]
        if session.process and session.process.poll() is None:
            try:
                session.process.terminate()
                session.status = "stopped"
                session.add_message("⏹️ Träning stoppad av användare", "warning")
                return True
            except Exception as e:
                session.add_message(f"❌ Kunde inte stoppa: {str(e)}", "error")
                
        return False
        
    def stop_all_training(self):
        """Stoppa alla aktiva träningssessions"""
        stopped_count = 0
        for session_name in list(self.sessions.keys()):
            if self.stop_training_session(session_name):
                stopped_count += 1
                
        if stopped_count > 0:
            console.print(f"⏹️ Stoppade {stopped_count} träningssessions")
            
    def process_command(self, command: str) -> bool:
        """Processera användarkommandon"""
        parts = command.strip().lower().split()
        if not parts:
            return True
            
        cmd = parts[0]
        
        if cmd in ["quit", "exit", "q"]:
            return False
            
        elif cmd == "help":
            console.print(Panel("""
🎯 Tillgängliga kommandon:

start <type>     - Starta träning
                  Typer: fibonacci, fibonacci_loop, rl_pipeline, cache_bandit
                  
stop <name>      - Stoppa specifik session
stop-all         - Stoppa alla sessions  
status           - Visa detaljerad sessioninfo
metrics          - Exportera metrics till filer
clear            - Rensa chat-historik
help             - Visa denna hjälp
quit             - Avsluta HUD

Exempel:
  start fibonacci
  stop fibonacci_123456
  status
""", title="💡 Hjälp", style="cyan"))
            
        elif cmd == "start":
            if len(parts) < 2:
                console.print("❌ Ange träningstyp. Tillgängliga: " + ", ".join(self.training_types.keys()))
                return True
                
            training_type = parts[1] 
            if training_type not in self.training_types:
                console.print("❌ Okänd träningstyp. Tillgängliga: " + ", ".join(self.training_types.keys()))
                return True
                
            # Starta asynkront
            asyncio.create_task(self.start_training_session(training_type))
            console.print(f"🚀 Startar {self.training_types[training_type]['name']}...")
            
        elif cmd == "stop":
            if len(parts) < 2:
                console.print("❌ Ange session-namn att stoppa")
                return True
                
            session_name = parts[1]
            if self.stop_training_session(session_name):
                console.print(f"⏹️ Stoppar {session_name}")
            else:
                console.print(f"❌ Kunde inte stoppa {session_name}")
                
        elif cmd == "stop-all":
            self.stop_all_training()
            
        elif cmd == "status":
            self.show_detailed_status()
            
        elif cmd == "metrics":
            self.export_metrics()
            
        elif cmd == "clear":
            for session in self.sessions.values():
                session.log_messages = []
            console.print("🧹 Chat-historik rensad")
            
        else:
            console.print(f"❌ Okänt kommando: {cmd}. Skriv 'help' för hjälp.")
            
        return True
        
    def show_detailed_status(self):
        """Visa detaljerad status för alla sessions"""
        if not self.sessions:
            console.print("📊 Inga aktiva sessions")
            return
            
        for session_name, session in self.sessions.items():
            uptime = datetime.now() - session.start_time
            
            status_panel = Panel(f"""
Namn: {session.name}
Typ: {session.session_type}
Status: {session.status}
Starttid: {session.start_time.strftime('%H:%M:%S')}
Uptime: {int(uptime.total_seconds()//60)}:{int(uptime.total_seconds()%60):02d}
Script: {session.script_path}
Meddelanden: {len(session.log_messages)}
Senaste update: {session.last_update.strftime('%H:%M:%S')}
""", title=f"📊 {session_name}", style="blue")
            
            console.print(status_panel)
            
    def export_metrics(self):
        """Exportera metrics till JSON-fil"""
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "sessions": {}
        }
        
        for session_name, session in self.sessions.items():
            uptime = datetime.now() - session.start_time
            metrics_data["sessions"][session_name] = {
                "name": session.name,
                "type": session.session_type,
                "status": session.status, 
                "start_time": session.start_time.isoformat(),
                "uptime_seconds": uptime.total_seconds(),
                "message_count": len(session.log_messages),
                "last_update": session.last_update.isoformat()
            }
            
        # Spara till fil
        metrics_file = f"training_hud_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
            
        console.print(f"📊 Metrics exporterade till {metrics_file}")
        
    async def run_hud(self):
        """Main HUD loop"""
        layout = self.create_chat_layout()
        
        with Live(layout, refresh_per_second=1, console=self.console) as live:
            try:
                while self.is_running:
                    # Uppdatera layout-komponenter
                    layout["header"].update(self.render_header())
                    layout["sessions"].update(self.render_sessions()) 
                    layout["chat"].update(self.render_chat())
                    layout["footer"].update(self.render_controls())
                    
                    # Kort paus
                    await asyncio.sleep(self.refresh_interval)
                    
            except KeyboardInterrupt:
                pass
            finally:
                self.stop_all_training()
                
    async def run_interactive(self):
        """Kör HUD med interaktiv input"""
        # Starta HUD i bakgrunden
        hud_task = asyncio.create_task(self.run_hud())
        
        try:
            while self.is_running:
                # Vänta på användarinput
                await asyncio.sleep(0.1)  
                
                # I en riktig implementation skulle vi använda async input
                # För nu använder vi en enkel loop som låter HUD köra
                
        except KeyboardInterrupt:
            self.is_running = False
            
        await hud_task

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="🧮 Alice v2 Training HUD")
    parser.add_argument("--auto-start", help="Starta träningar automatiskt (comma-separated)")
    parser.add_argument("--refresh-rate", type=float, default=1.0, help="HUD refresh rate (seconds)")
    
    args = parser.parse_args()
    
    hud = TrainingHUD()
    hud.refresh_interval = args.refresh_rate
    
    # Auto-start träningar om angivet
    if args.auto_start:
        types_to_start = [t.strip() for t in args.auto_start.split(",")]
        for training_type in types_to_start:
            if training_type in hud.training_types:
                await hud.start_training_session(training_type)
                console.print(f"🚀 Auto-startade {training_type}")
                await asyncio.sleep(1)  # Liten paus mellan starts
    
    # Visa välkomstmeddelande
    console.print(Panel("""
🧮 [bold magenta]Alice v2 Training HUD[/bold magenta] 

Välkommen till den interaktiva träningsmonitorn!

Tryck Ctrl+C för att avsluta och få en kommandoprompt.
""", style="green"))
    
    try:
        # Starta HUD
        await hud.run_hud()
        
    except KeyboardInterrupt:
        console.print("\n🎮 Växlar till interaktiv kommandoläge...")
        
        # Interaktiv kommandoloop
        while True:
            try:
                command = Prompt.ask("\n[bold cyan]training-hud>[/bold cyan]", default="help")
                if not hud.process_command(command):
                    break
            except (KeyboardInterrupt, EOFError):
                break
                
        console.print("👋 Hej då!")

if __name__ == "__main__":
    asyncio.run(main())