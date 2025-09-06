#!/usr/bin/env python3
"""
🌐 Simple Training Web HUD - Enkel localhost interface

En förenklad men stabil web-baserad träningsmonitor utan komplexa async threading.

Usage:
    python simple_training_hud.py                 # Start på localhost:3001
    python simple_training_hud.py --port 3000     # Custom port
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
import sys
import webbrowser

# Web server dependencies
try:
    from fastapi import FastAPI, Request, BackgroundTasks
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
except ImportError:
    print("❌ Missing web dependencies. Install with:")
    print("pip install fastapi 'uvicorn[standard]'")
    sys.exit(1)

class SimpleTrainingSession:
    """Förenklad träningssession med performance tracking"""
    
    def __init__(self, name: str, script_path: str, session_type: str):
        self.name = name
        self.script_path = script_path  
        self.session_type = session_type
        self.start_time = datetime.now()
        self.status = "starting"
        self.process = None
        self.log_messages = []
        self.last_update = datetime.now()
        
        # Performance metrics tracking
        self.performance_stats = {
            "avg_response_time_ms": 0,
            "cache_hit_rate_percent": 0,
            "success_rate_percent": 0,
            "improvement_percent": 0,
            "target_progress_percent": 0,
            "total_requests": 0,
            "fibonacci_efficiency": 0
        }
        
    def add_message(self, message: str, level: str = "info"):
        """Lägg till meddelande"""
        timestamp = datetime.now()
        log_entry = {
            "time": timestamp.strftime("%H:%M:%S"),
            "timestamp": timestamp.isoformat(),
            "level": level, 
            "message": message,
            "session": self.name
        }
        self.log_messages.append(log_entry)
        self.last_update = timestamp
        
        # Ring buffer - behåll bara senaste 50 meddelanden
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
            
        return log_entry
        
    def parse_metrics_from_message(self, message: str):
        """Parse performance metrics från träningsmeddelanden"""
        import re
        
        # Parse olika metrics från meddelanden
        patterns = {
            "avg_response_time": r"(\d+\.?\d*)ms avg",
            "cache_hit_rate": r"Cache.*?(\d+\.?\d*)%",
            "success_rate": r"Success.*?(\d+\.?\d*)%",
            "improvement": r"Improvement.*?(\d+\.?\d*)%",
            "target_progress": r"Progress.*?(\d+\.?\d*)%",
            "total_requests": r"(\d+)/(\d+) requests",
            "fibonacci_efficiency": r"φ.*?(\d+\.?\d*)"
        }
        
        for metric, pattern in patterns.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    if metric == "avg_response_time":
                        self.performance_stats["avg_response_time_ms"] = value
                    elif metric == "cache_hit_rate":
                        self.performance_stats["cache_hit_rate_percent"] = value
                    elif metric == "success_rate":
                        self.performance_stats["success_rate_percent"] = value
                    elif metric == "improvement":
                        self.performance_stats["improvement_percent"] = value
                    elif metric == "target_progress":
                        self.performance_stats["target_progress_percent"] = value
                    elif metric == "total_requests":
                        self.performance_stats["total_requests"] = int(value)
                    elif metric == "fibonacci_efficiency":
                        self.performance_stats["fibonacci_efficiency"] = value
                except (ValueError, IndexError):
                    pass
    
    def to_dict(self):
        """Serialisera för JSON API med performance stats"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            "name": self.name,
            "script_path": self.script_path,
            "session_type": self.session_type,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": uptime,
            "uptime_display": f"{int(uptime//60)}:{int(uptime%60):02d}",
            "message_count": len(self.log_messages),
            "last_update": self.last_update.isoformat(),
            "performance_stats": self.performance_stats
        }

class SimpleTrainingHUD:
    """Förenklad web HUD med historical stats"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.app = FastAPI(title="🧮 Simple Training HUD")
        self.sessions: Dict[str, SimpleTrainingSession] = {}
        self.all_messages: List[Dict] = []  # Global meddelandelista
        
        # Historical stats tracking
        self.history_file = "training_history_stats.json"
        self.historical_stats = self.load_historical_stats()
        self.session_counter = 0
        
        # Träningstyper
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
            }
        }
        
        self.setup_routes()
        self.create_html_interface()
        
    def load_historical_stats(self):
        """Ladda historisk träningsdata"""
        try:
            if Path(self.history_file).exists():
                with open(self.history_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Varning: Kunde inte ladda historical stats: {e}")
        
        return {
            "fibonacci": {"runs": [], "best_avg_ms": 999, "best_cache_rate": 0, "best_improvement": 0},
            "fibonacci_loop": {"runs": [], "best_avg_ms": 999, "best_cache_rate": 0, "best_improvement": 0}
        }
        
    def save_historical_stats(self):
        """Spara historisk träningsdata"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.historical_stats, f, indent=2)
        except Exception as e:
            print(f"Varning: Kunde inte spara historical stats: {e}")
            
    def add_training_to_history(self, training_type: str, session_data: dict):
        """Lägg till träning i historiska data"""
        if training_type not in self.historical_stats:
            self.historical_stats[training_type] = {"runs": [], "best_avg_ms": 999, "best_cache_rate": 0, "best_improvement": 0}
            
        stats = session_data["performance_stats"]
        run_data = {
            "timestamp": session_data["start_time"],
            "duration_seconds": session_data["uptime_seconds"],
            "avg_response_time_ms": stats["avg_response_time_ms"],
            "cache_hit_rate_percent": stats["cache_hit_rate_percent"],
            "success_rate_percent": stats["success_rate_percent"],
            "improvement_percent": stats["improvement_percent"],
            "target_progress_percent": stats["target_progress_percent"]
        }
        
        # Lägg till run
        self.historical_stats[training_type]["runs"].append(run_data)
        
        # Uppdatera bästa resultat
        if stats["avg_response_time_ms"] > 0 and stats["avg_response_time_ms"] < self.historical_stats[training_type]["best_avg_ms"]:
            self.historical_stats[training_type]["best_avg_ms"] = stats["avg_response_time_ms"]
            
        if stats["cache_hit_rate_percent"] > self.historical_stats[training_type]["best_cache_rate"]:
            self.historical_stats[training_type]["best_cache_rate"] = stats["cache_hit_rate_percent"]
            
        if stats["improvement_percent"] > self.historical_stats[training_type]["best_improvement"]:
            self.historical_stats[training_type]["best_improvement"] = stats["improvement_percent"]
            
        # Behåll bara senaste 20 runs
        if len(self.historical_stats[training_type]["runs"]) > 20:
            self.historical_stats[training_type]["runs"] = self.historical_stats[training_type]["runs"][-20:]
            
        self.save_historical_stats()
        
    def get_improvement_vs_previous(self, training_type: str, current_stats: dict):
        """Beräkna förbättring jämfört med föregående körning"""
        if training_type not in self.historical_stats or not self.historical_stats[training_type]["runs"]:
            return {"response_time": 0, "cache_rate": 0, "is_first_run": True}
            
        previous_run = self.historical_stats[training_type]["runs"][-1]
        improvements = {}
        
        # Response time improvement (negativ = bättre)
        if previous_run["avg_response_time_ms"] > 0 and current_stats["avg_response_time_ms"] > 0:
            improvements["response_time"] = ((current_stats["avg_response_time_ms"] - previous_run["avg_response_time_ms"]) / previous_run["avg_response_time_ms"]) * 100
        else:
            improvements["response_time"] = 0
            
        # Cache rate improvement (positiv = bättre)  
        improvements["cache_rate"] = current_stats["cache_hit_rate_percent"] - previous_run["cache_hit_rate_percent"]
        
        improvements["is_first_run"] = False
        return improvements
        
    def create_html_interface(self):
        """Skapa HTML interface utan WebSocket"""
        html_content = '''<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧮 Alice Training HUD</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: white; padding: 20px;
        }
        .header {
            text-align: center; margin-bottom: 30px;
            background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .stats { display: flex; justify-content: center; gap: 30px; margin-top: 15px; }
        .stat-item { text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #00ff88; }
        .main-content { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .progress-section { grid-column: 1 / -1; margin-bottom: 20px; }
        @media (max-width: 768px) { .main-content { grid-template-columns: 1fr; } }
        .panel {
            background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px;
            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);
        }
        .panel h2 { margin-bottom: 15px; color: #00ff88; }
        .session-card {
            background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px;
            border-left: 4px solid #00ff88; margin-bottom: 15px;
        }
        .session-card.running { border-left-color: #00ff88; }
        .session-card.starting { border-left-color: #ffaa00; }
        .session-card.completed { border-left-color: #0088ff; }
        .session-card.failed { border-left-color: #ff4444; }
        .session-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .session-name { font-weight: bold; font-size: 1.1em; }
        .session-status { padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; }
        .status-running { background: #00ff88; color: black; }
        .status-starting { background: #ffaa00; color: black; }
        .status-completed { background: #0088ff; color: white; }
        .status-failed { background: #ff4444; color: white; }
        .chat-panel { height: 400px; overflow-y: auto; font-family: Monaco, monospace; font-size: 0.85em; }
        .chat-message { padding: 8px 12px; border-radius: 8px; margin-bottom: 5px; line-height: 1.4; }
        .chat-message.info { background: rgba(255,255,255,0.1); }
        .chat-message.success { background: rgba(0,255,136,0.2); }
        .chat-message.warning { background: rgba(255,170,0,0.2); }
        .chat-message.error { background: rgba(255,68,68,0.2); }
        .controls { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; }
        .btn { padding: 10px 20px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; margin: 5px; }
        .btn-primary { background: #00ff88; color: black; }
        .btn-danger { background: #ff4444; color: white; }
        .btn-secondary { background: #0088ff; color: white; }
        .auto-refresh { position: fixed; top: 20px; right: 20px; background: #00ff88; color: black; padding: 10px; border-radius: 8px; }
        .progress-chart { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; }
        .chart-container { position: relative; height: 200px; margin-top: 15px; }
        .chart-svg { width: 100%; height: 100%; }
        .chart-line { fill: none; stroke: #00ff88; stroke-width: 2; }
        .chart-area { fill: rgba(0,255,136,0.1); }
        .chart-dot { fill: #00ff88; stroke: #fff; stroke-width: 2; r: 4; }
        .chart-axis { stroke: rgba(255,255,255,0.3); stroke-width: 1; }
        .chart-text { fill: rgba(255,255,255,0.7); font-size: 12px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px; }
        .metric-card { background: rgba(0,0,0,0.3); padding: 15px; border-radius: 10px; text-align: center; }
        .metric-value { font-size: 1.8em; font-weight: bold; color: #00ff88; }
        .metric-label { font-size: 0.9em; opacity: 0.8; }
        .metric-change { font-size: 0.8em; margin-top: 5px; }
        .metric-up { color: #00ff88; }
        .metric-down { color: #ff6b6b; }
        .metric-neutral { color: #ffd93d; }
    </style>
</head>
<body>
    <div class="auto-refresh" id="refreshStatus">🔄 Auto-refresh: ON</div>
    
    <div class="header">
        <h1>🧮 Alice Training HUD</h1>
        <p>Enkel real-time träningsmonitoring</p>
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number" id="activeSessions">0</div>
                <div>Aktiva</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="totalSessions">0</div>
                <div>Totalt</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="totalMessages">0</div>
                <div>Meddelanden</div>
            </div>
        </div>
    </div>
    
    <div class="progress-section">
        <div class="progress-chart">
            <h2>📈 Träningsprogress</h2>
            <div class="chart-container">
                <svg class="chart-svg" id="progressChart">
                    <!-- Progress chart will be drawn here -->
                </svg>
            </div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" id="avgResponseTime">0ms</div>
                    <div class="metric-label">Genomsnittlig svarstid</div>
                    <div class="metric-change" id="responseTimeChange"></div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="cacheHitRate">0%</div>
                    <div class="metric-label">Cache träffar</div>
                    <div class="metric-change" id="cacheHitChange"></div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="successRate">0%</div>
                    <div class="metric-label">Framgång</div>
                    <div class="metric-change" id="successRateChange"></div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="fibonacciEfficiency">φ 0.00</div>
                    <div class="metric-label">Fibonacci-effektivitet</div>
                    <div class="metric-change" id="fibonacciChange"></div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="main-content">
        <div class="panel">
            <h2>📊 Aktiva Träningar</h2>
            <div id="sessionsContainer">
                <div style="text-align: center; opacity: 0.5; padding: 40px;">
                    Inga träningar igång. Starta en nedan! 👇
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>💬 Live Chat</h2>
            <div id="chatContainer" class="chat-panel">
                <div class="chat-message info">
                    <strong>SYSTEM:</strong> 🎯 Välkommen! Starta träning för att se live-uppdateringar.
                </div>
            </div>
        </div>
    </div>
    
    <div class="controls">
        <h2>🎮 Kontroller</h2>
        <button class="btn btn-primary" onclick="startTraining('fibonacci')">🧮 Starta Fibonacci</button>
        <button class="btn btn-primary" onclick="startTraining('fibonacci_loop')">🔄 Starta Loop</button>
        <button class="btn btn-secondary" onclick="runSystemCheck()">🔍 Systemkontroll</button>
        <button class="btn btn-danger" onclick="stopAllTraining()">⏹️ Stoppa Alla</button>
        <button class="btn btn-secondary" onclick="clearChat()">🧹 Rensa Chat</button>
        <button class="btn btn-secondary" onclick="cleanupFailedSessions()">🗑️ Rensa Failed</button>
        <button class="btn btn-secondary" onclick="toggleAutoRefresh()">⏸️ Pausa Refresh</button>
    </div>

    <script>
        let sessions = {};
        let autoRefresh = true;
        let refreshInterval;
        
        async function startTraining(trainingType) {
            try {
                const response = await fetch('/api/start-training', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ training_type: trainingType })
                });
                const result = await response.json();
                if (!result.success) {
                    alert('Fel vid start: ' + result.error);
                }
            } catch (error) {
                alert('Fel: ' + error.message);
            }
        }
        
        async function stopAllTraining() {
            if (!confirm('Stoppa alla träningar?')) return;
            try {
                const response = await fetch('/api/stop-all', { method: 'POST' });
                const result = await response.json();
                alert(`Stoppade ${result.stopped_count} träningar`);
            } catch (error) {
                alert('Fel: ' + error.message);
            }
        }
        
        function clearChat() {
            document.getElementById('chatContainer').innerHTML = `
                <div class="chat-message info">
                    <strong>SYSTEM:</strong> Chat rensad.
                </div>
            `;
        }
        
        async function cleanupFailedSessions() {
            if (!confirm('Rensa alla failed sessions från minnet?')) return;
            try {
                const response = await fetch('/api/cleanup-failed', { method: 'POST' });
                const result = await response.json();
                alert(`Rensade ${result.cleaned_count} failed sessions`);
                updateData(); // Uppdatera vyn
            } catch (error) {
                alert('Fel vid rensning: ' + error.message);
            }
        }
        
        async function runSystemCheck() {
            try {
                // Visa att kontroll pågår
                const chatContainer = document.getElementById('chatContainer');
                chatContainer.innerHTML += `
                    <div class="chat-message info">
                        <strong>SYSTEM:</strong> 🔍 Kör omfattande systemkontroll...
                    </div>
                `;
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
                const response = await fetch('/api/system-status');
                const status = await response.json();
                
                // Visa resultatet i chatten
                let healthIcon = '✅';
                let healthColor = 'success';
                
                if (status.overall_health === 'critical') {
                    healthIcon = '🔴';
                    healthColor = 'error';
                } else if (status.overall_health === 'warning') {
                    healthIcon = '⚠️';
                    healthColor = 'warning';
                }
                
                chatContainer.innerHTML += `
                    <div class="chat-message ${healthColor}">
                        <strong>SYSTEMSTATUS:</strong> ${healthIcon} ${status.overall_health.toUpperCase()}
                    </div>
                `;
                
                // Visa kritiska problem
                if (status.summary.critical_issues > 0) {
                    chatContainer.innerHTML += `
                        <div class="chat-message error">
                            <strong>KRITISKA PROBLEM:</strong> ${status.summary.critical_issues} st
                        </div>
                    `;
                }
                
                // Visa alerts
                status.alerts.slice(0, 5).forEach(alert => {
                    let alertColor = 'error';
                    if (alert.includes('VARNING')) alertColor = 'warning';
                    if (alert.includes('PROBLEM')) alertColor = 'warning';
                    
                    chatContainer.innerHTML += `
                        <div class="chat-message ${alertColor}">
                            <strong>ALERT:</strong> ${alert}
                        </div>
                    `;
                });
                
                // Visa rekommendationer
                if (status.recommendations.length > 0) {
                    chatContainer.innerHTML += `
                        <div class="chat-message info">
                            <strong>REKOMMENDATIONER:</strong>
                        </div>
                    `;
                    status.recommendations.slice(0, 3).forEach(rec => {
                        chatContainer.innerHTML += `
                            <div class="chat-message info">
                                <strong>→</strong> ${rec}
                            </div>
                        `;
                    });
                }
                
                if (status.overall_health === 'healthy') {
                    chatContainer.innerHTML += `
                        <div class="chat-message success">
                            <strong>RESULTAT:</strong> ✅ Alla system fungerar korrekt!
                        </div>
                    `;
                }
                
                chatContainer.scrollTop = chatContainer.scrollHeight;
                
            } catch (error) {
                const chatContainer = document.getElementById('chatContainer');
                chatContainer.innerHTML += `
                    <div class="chat-message error">
                        <strong>FEL:</strong> Kunde inte köra systemkontroll - ${error.message}
                    </div>
                `;
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }
        
        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const btn = event.target;
            const status = document.getElementById('refreshStatus');
            
            if (autoRefresh) {
                btn.textContent = '⏸️ Pausa Refresh';
                status.textContent = '🔄 Auto-refresh: ON';
                status.style.background = '#00ff88';
                startAutoRefresh();
            } else {
                btn.textContent = '▶️ Starta Refresh';
                status.textContent = '⏸️ Auto-refresh: OFF';
                status.style.background = '#ff4444';
                clearInterval(refreshInterval);
            }
        }
        
        async function updateData() {
            try {
                // Uppdatera sessions
                const sessionsResponse = await fetch('/api/sessions');
                const sessionsData = await sessionsResponse.json();
                
                // Uppdatera meddelanden
                const messagesResponse = await fetch('/api/messages');
                const messagesData = await messagesResponse.json();
                
                renderSessions(sessionsData);
                renderMessages(messagesData);
                updateStats(sessionsData, messagesData);
                
            } catch (error) {
                console.error('Fel vid uppdatering:', error);
            }
        }
        
        function renderSessions(sessionsData) {
            const container = document.getElementById('sessionsContainer');
            
            // Filtrera bort failed sessions - visa bara running, starting, completed
            const activeSessions = sessionsData.filter(s => 
                s.status === 'running' || s.status === 'starting' || s.status === 'completed'
            );
            
            if (activeSessions.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; opacity: 0.5; padding: 40px;">
                        Inga aktiva träningar. Starta en nedan! 👇
                    </div>
                `;
                return;
            }
            
            container.innerHTML = activeSessions.map(session => `
                <div class="session-card ${session.status}">
                    <div class="session-header">
                        <div class="session-name">${session.name}</div>
                        <div class="session-status status-${session.status}">
                            ${session.status === 'running' ? '●' : 
                              session.status === 'starting' ? '◐' : 
                              session.status === 'completed' ? '✓' : '✗'} 
                            ${session.status.toUpperCase()}
                        </div>
                    </div>
                    <div style="font-size: 0.9em; opacity: 0.8; margin-bottom: 5px;">
                        ${session.session_type}
                    </div>
                    <div style="font-size: 0.9em; opacity: 0.8; margin-bottom: 5px;">
                        ⏱️ Uptime: ${session.uptime_display}
                    </div>
                    <div style="font-size: 0.9em; opacity: 0.8;">
                        💬 Meddelanden: ${session.message_count}
                    </div>
                </div>
            `).join('');
        }
        
        function renderMessages(messagesData) {
            const container = document.getElementById('chatContainer');
            
            if (messagesData.length === 0) return;
            
            const messagesHtml = messagesData.slice(-20).map(msg => `
                <div class="chat-message ${msg.level}">
                    <strong>${msg.time} [${msg.session}]:</strong> ${msg.message}
                </div>
            `).join('');
            
            container.innerHTML = messagesHtml;
            container.scrollTop = container.scrollHeight;
        }
        
        function updateStats(sessionsData, messagesData) {
            const activeCount = sessionsData.filter(s => 
                s.status === 'running' || s.status === 'starting'
            ).length;
            
            document.getElementById('activeSessions').textContent = activeCount;
            document.getElementById('totalSessions').textContent = sessionsData.length;
            document.getElementById('totalMessages').textContent = messagesData.length;
            
            // Uppdatera progress metrics
            updateProgressMetrics(sessionsData);
        }
        
        let progressHistory = [];
        
        function updateProgressMetrics(sessionsData) {
            // Hitta den mest aktiva/senaste träningen
            const activeSessions = sessionsData.filter(s => s.status === 'running' || s.status === 'completed');
            
            if (activeSessions.length === 0) {
                // Nollställ metrics om ingen aktiv träning
                document.getElementById('avgResponseTime').textContent = '0ms';
                document.getElementById('cacheHitRate').textContent = '0%';
                document.getElementById('successRate').textContent = '0%';
                document.getElementById('fibonacciEfficiency').textContent = 'φ 0.00';
                clearChart();
                return;
            }
            
            // Ta den senaste aktiva sessionen
            const session = activeSessions.sort((a, b) => 
                new Date(b.start_time) - new Date(a.start_time)
            )[0];
            
            const stats = session.performance_stats;
            
            // Uppdatera metric cards
            document.getElementById('avgResponseTime').textContent = 
                stats.avg_response_time_ms ? `${Math.round(stats.avg_response_time_ms)}ms` : '0ms';
            document.getElementById('cacheHitRate').textContent = 
                `${stats.cache_hit_rate_percent.toFixed(1)}%`;
            document.getElementById('successRate').textContent = 
                `${stats.success_rate_percent.toFixed(1)}%`;
            document.getElementById('fibonacciEfficiency').textContent = 
                `φ ${stats.fibonacci_efficiency.toFixed(3)}`;
            
            // Lägg till i historik för graf
            const now = new Date();
            progressHistory.push({
                timestamp: now,
                cacheHitRate: stats.cache_hit_rate_percent,
                successRate: stats.success_rate_percent,
                responseTime: stats.avg_response_time_ms || 0,
                requests: stats.total_requests || 0
            });
            
            // Behåll bara senaste 50 punkter
            if (progressHistory.length > 50) {
                progressHistory = progressHistory.slice(-50);
            }
            
            // Rita graf
            drawProgressChart();
            
            // Beräkna förändringar (jämfört med föregående)
            if (progressHistory.length > 1) {
                const prev = progressHistory[progressHistory.length - 2];
                const curr = progressHistory[progressHistory.length - 1];
                
                updateMetricChange('responseTimeChange', prev.responseTime, curr.responseTime, true); // true = lower is better
                updateMetricChange('cacheHitChange', prev.cacheHitRate, curr.cacheHitRate);
                updateMetricChange('successRateChange', prev.successRate, curr.successRate);
                
                // Fibonacci efficiency change
                const prevFib = 1.618033988749; // default
                const currFib = stats.fibonacci_efficiency;
                updateMetricChange('fibonacciChange', prevFib, currFib);
            }
        }
        
        function updateMetricChange(elementId, prevValue, currValue, lowerIsBetter = false) {
            const element = document.getElementById(elementId);
            const diff = currValue - prevValue;
            
            if (Math.abs(diff) < 0.01) {
                element.textContent = '→ Stabil';
                element.className = 'metric-change metric-neutral';
                return;
            }
            
            const isImprovement = lowerIsBetter ? diff < 0 : diff > 0;
            const arrow = isImprovement ? '↗' : '↘';
            const className = isImprovement ? 'metric-up' : 'metric-down';
            
            element.textContent = `${arrow} ${Math.abs(diff).toFixed(1)}${elementId.includes('Rate') ? '%' : ''}`;
            element.className = `metric-change ${className}`;
        }
        
        function clearChart() {
            const svg = document.getElementById('progressChart');
            svg.innerHTML = '';
            progressHistory = [];
        }
        
        function drawProgressChart() {
            if (progressHistory.length < 2) return;
            
            const svg = document.getElementById('progressChart');
            const rect = svg.getBoundingClientRect();
            const width = rect.width;
            const height = rect.height;
            
            if (width === 0 || height === 0) return; // SVG not ready
            
            svg.innerHTML = ''; // Clear existing
            
            // Chart margins
            const margin = { top: 20, right: 20, bottom: 30, left: 40 };
            const chartWidth = width - margin.left - margin.right;
            const chartHeight = height - margin.top - margin.bottom;
            
            // Find data ranges
            const maxCacheRate = Math.max(...progressHistory.map(d => d.cacheHitRate));
            const maxSuccessRate = Math.max(...progressHistory.map(d => d.successRate));
            const maxRate = Math.max(maxCacheRate, maxSuccessRate, 100);
            
            // Create scales
            const xScale = (i) => margin.left + (i / (progressHistory.length - 1)) * chartWidth;
            const yScale = (value) => margin.top + chartHeight - (value / maxRate) * chartHeight;
            
            // Draw axes
            svg.innerHTML += `<line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + chartHeight}" class="chart-axis"/>`;
            svg.innerHTML += `<line x1="${margin.left}" y1="${margin.top + chartHeight}" x2="${margin.left + chartWidth}" y2="${margin.top + chartHeight}" class="chart-axis"/>`;
            
            // Draw cache hit rate line
            const cachePoints = progressHistory.map((d, i) => `${xScale(i)},${yScale(d.cacheHitRate)}`).join(' ');
            svg.innerHTML += `<polyline points="${cachePoints}" class="chart-line" stroke="#00ff88"/>`;
            
            // Draw success rate line
            const successPoints = progressHistory.map((d, i) => `${xScale(i)},${yScale(d.successRate)}`).join(' ');
            svg.innerHTML += `<polyline points="${successPoints}" class="chart-line" stroke="#0088ff"/>`;
            
            // Draw dots for latest points
            const latest = progressHistory[progressHistory.length - 1];
            const latestIndex = progressHistory.length - 1;
            svg.innerHTML += `<circle cx="${xScale(latestIndex)}" cy="${yScale(latest.cacheHitRate)}" class="chart-dot" fill="#00ff88"/>`;
            svg.innerHTML += `<circle cx="${xScale(latestIndex)}" cy="${yScale(latest.successRate)}" class="chart-dot" fill="#0088ff"/>`;
            
            // Add labels
            svg.innerHTML += `<text x="${margin.left + 10}" y="${margin.top + 15}" class="chart-text">Cache Hit Rate</text>`;
            svg.innerHTML += `<text x="${margin.left + 10}" y="${margin.top + 30}" class="chart-text" fill="#0088ff">Success Rate</text>`;
            
            // Y-axis labels
            svg.innerHTML += `<text x="${margin.left - 10}" y="${yScale(0)}" class="chart-text" text-anchor="end">0%</text>`;
            svg.innerHTML += `<text x="${margin.left - 10}" y="${yScale(maxRate)}" class="chart-text" text-anchor="end">${Math.round(maxRate)}%</text>`;
        }
        
        function startAutoRefresh() {
            refreshInterval = setInterval(() => {
                if (autoRefresh) updateData();
            }, 2000); // Uppdatera var 2:a sekund
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            updateData();
            startAutoRefresh();
        });
    </script>
</body>
</html>'''
        
        # Skriv HTML till static directory
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        with open("static/simple_index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            with open("static/simple_index.html", encoding="utf-8") as f:
                return HTMLResponse(f.read())
                
        @self.app.get("/api/sessions")
        async def get_sessions():
            return [s.to_dict() for s in self.sessions.values()]
            
        @self.app.get("/api/messages")
        async def get_messages():
            return self.all_messages[-100:]  # Senaste 100
            
        @self.app.post("/api/start-training")
        async def start_training_api(request: Request, background_tasks: BackgroundTasks):
            data = await request.json()
            training_type = data.get("training_type")
            
            if training_type not in self.training_types:
                return JSONResponse({"success": False, "error": "Okänd träningstyp"})
                
            success = await self.start_training_session(training_type)
            return JSONResponse({"success": success})
            
        @self.app.post("/api/stop-all")
        async def stop_all_api():
            stopped_count = 0
            for session_name in list(self.sessions.keys()):
                if self.stop_training_session(session_name):
                    stopped_count += 1
            return JSONResponse({"stopped_count": stopped_count})
            
        @self.app.get("/api/system-status")
        async def system_status_api():
            """Omfattande systemstatus och självkontroll"""
            status = self.perform_system_health_check()
            return JSONResponse(status)
            
        @self.app.post("/api/cleanup-failed")
        async def cleanup_failed_api():
            """Rensa alla failed sessions från minnet"""
            failed_sessions = [name for name, session in self.sessions.items() if session.status == "failed"]
            cleaned_count = len(failed_sessions)
            
            for session_name in failed_sessions:
                del self.sessions[session_name]
                
            self.add_global_message(f"🗑️ Rensade {cleaned_count} failed sessions", "info", "CLEANUP")
            return JSONResponse({"cleaned_count": cleaned_count})
            
    def ensure_alice_services_running(self):
        """Säkerställ att Alice services körs"""
        self.add_global_message("🔍 Kontrollerar Alice services...", "info", "SYSTEM")
        
        try:
            # Kontrollera om Docker körs
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                self.add_global_message("❌ Docker körs inte", "error", "SYSTEM")
                return False
                
            # Kontrollera om Alice services körs
            if "alice-orchestrator" not in result.stdout:
                self.add_global_message("🚀 Alice services saknas - startar med 'make up'...", "warning", "SYSTEM")
                
                # Starta services med make up
                make_result = subprocess.run(["make", "up"], capture_output=True, text=True, timeout=60)
                if make_result.returncode != 0:
                    self.add_global_message(f"❌ 'make up' misslyckades: {make_result.stderr}", "error", "SYSTEM")
                    return False
                    
                self.add_global_message("✅ Alice services startade", "success", "SYSTEM")
                
                # Starta dev-proxy för port 8001 (från AGENTS.md fix)
                self.add_global_message("🌐 Startar dev-proxy för port 8001...", "info", "SYSTEM")
                proxy_result = subprocess.run(
                    ["docker", "compose", "up", "-d", "dev-proxy"], 
                    capture_output=True, text=True, timeout=30
                )
                if proxy_result.returncode == 0:
                    self.add_global_message("✅ Dev-proxy startad", "success", "SYSTEM")
                else:
                    self.add_global_message("⚠️ Dev-proxy kunde inte startas", "warning", "SYSTEM")
                    
                # Vänta på att services blir klara
                self.add_global_message("⏳ Väntar 10 sekunder på att services blir klara...", "info", "SYSTEM")
                time.sleep(10)
            
            # Health check via Guardian (port 8787 som vi vet fungerar)
            import urllib.request
            try:
                with urllib.request.urlopen("http://localhost:8787/health", timeout=3) as response:
                    if response.getcode() == 200:
                        self.add_global_message("✅ Guardian svarar - Alice services OK", "success", "SYSTEM")
                        return True
                    else:
                        self.add_global_message("⚠️ Guardian svarar men inte OK status", "warning", "SYSTEM")
                        return False
            except Exception as e:
                self.add_global_message(f"❌ Alice API inte tillgänglig på port 8001: {str(e)}", "error", "SYSTEM")
                
                # Försök starta dev-proxy igen
                self.add_global_message("🔧 Försöker starta dev-proxy igen...", "info", "SYSTEM")
                subprocess.run(["docker", "compose", "up", "-d", "dev-proxy"], 
                             capture_output=True, text=True, timeout=30)
                time.sleep(5)
                
                # Försök health check igen
                try:
                    with urllib.request.urlopen("http://localhost:8787/health", timeout=3) as response:
                        if response.getcode() == 200:
                            self.add_global_message("✅ Guardian svarar nu!", "success", "SYSTEM")
                            return True
                except:
                    pass
                    
                self.add_global_message("❌ Kunde inte få Alice API att svara", "error", "SYSTEM")
                return False
                
        except subprocess.TimeoutExpired:
            self.add_global_message("❌ Timeout vid start av services", "error", "SYSTEM")
            return False
        except Exception as e:
            self.add_global_message(f"❌ Fel vid kontroll av services: {str(e)}", "error", "SYSTEM")
            return False
            
    def perform_system_health_check(self):
        """Omfattande systemhälsokontroll"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "unknown",
            "services": {},
            "ports": {},
            "filesystem": {},
            "training_environment": {},
            "alerts": [],
            "recommendations": []
        }
        
        alerts = []
        
        try:
            # Docker kontroll
            docker_result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=10)
            if docker_result.returncode == 0:
                status["services"]["docker"] = {"status": "running", "containers": []}
                
                # Parsa container info
                lines = docker_result.stdout.split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip() and 'alice' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            container_name = parts[-1]
                            container_status = "running" if "Up" in line else "stopped"
                            status["services"]["docker"]["containers"].append({
                                "name": container_name,
                                "status": container_status
                            })
                            
                # Kontrollera kritiska Alice containers
                required_containers = ["alice-orchestrator", "alice-cache", "alice-nlu", "guardian", "alice-dev-proxy"]
                running_containers = [c["name"] for c in status["services"]["docker"]["containers"] if c["status"] == "running"]
                
                for container in required_containers:
                    if container not in running_containers:
                        alerts.append(f"🔴 KRITISK: {container} körs inte")
                        
            else:
                status["services"]["docker"] = {"status": "failed", "error": docker_result.stderr}
                alerts.append("🔴 KRITISK: Docker körs inte eller är inte tillgängligt")
                
        except Exception as e:
            status["services"]["docker"] = {"status": "error", "error": str(e)}
            alerts.append(f"🔴 KRITISK: Docker fel - {str(e)}")
            
        # Port kontroller
        ports_to_check = {
            "8001": "Alice API (via Caddy)",
            "8787": "Guardian",
            "9002": "NLU Service", 
            "6379": "Redis Cache"
        }
        
        for port, service_name in ports_to_check.items():
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', int(port)))
                sock.close()
                
                if result == 0:
                    status["ports"][port] = {"status": "open", "service": service_name}
                    
                    # Specifik health check för Alice API
                    if port == "8001":
                        try:
                            import urllib.request
                            with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=3) as response:
                                if response.getcode() == 200:
                                    status["ports"][port]["health_check"] = "passed"
                                else:
                                    status["ports"][port]["health_check"] = "failed"
                                    alerts.append(f"⚠️ VARNING: Port {port} öppen men health check misslyckades")
                        except Exception as e:
                            status["ports"][port]["health_check"] = "error"
                            alerts.append(f"⚠️ VARNING: Port {port} health check fel - {str(e)}")
                else:
                    status["ports"][port] = {"status": "closed", "service": service_name}
                    alerts.append(f"🟡 PROBLEM: Port {port} ({service_name}) är inte öppen")
                    
            except Exception as e:
                status["ports"][port] = {"status": "error", "error": str(e)}
                alerts.append(f"🔴 FEL: Kunde inte kontrollera port {port} - {str(e)}")
                
        # Filsystem kontroller
        critical_paths = {
            "scripts/fibonacci_simple_training.py": "Fibonacci träningsskript",
            "scripts/fibonacci_training_loop.py": "Fibonacci loop script", 
            ".venv/bin/activate": "Virtual environment",
            "docker-compose.yml": "Docker konfiguration",
            "Makefile": "Make kommandon"
        }
        
        for path, description in critical_paths.items():
            if Path(path).exists():
                status["filesystem"][path] = {"status": "exists", "description": description}
            else:
                status["filesystem"][path] = {"status": "missing", "description": description}
                alerts.append(f"🔴 KRITISK: {description} saknas ({path})")
                
        # Tränings-miljö kontroller
        try:
            # Kontrollera Python virtual env
            venv_python = Path(".venv/bin/python")
            if venv_python.exists():
                python_result = subprocess.run([str(venv_python), "--version"], 
                                             capture_output=True, text=True, timeout=5)
                if python_result.returncode == 0:
                    status["training_environment"]["python"] = {
                        "status": "ok", 
                        "version": python_result.stdout.strip()
                    }
                else:
                    status["training_environment"]["python"] = {"status": "error"}
                    alerts.append("🟡 PROBLEM: Python i virtual env fungerar inte korrekt")
            else:
                status["training_environment"]["python"] = {"status": "missing"}
                alerts.append("🔴 KRITISK: Python virtual environment saknas")
                
        except Exception as e:
            alerts.append(f"🔴 FEL: Kunde inte kontrollera tränings-miljö - {str(e)}")
            
        # Rekommendationer baserat på problem
        recommendations = []
        if any("Docker" in alert for alert in alerts):
            recommendations.append("🔧 Starta Docker Desktop och vänta på att den blir klar")
            recommendations.append("🔧 Kör 'docker ps' manuellt för att testa Docker")
            
        if any("Port" in alert for alert in alerts):
            recommendations.append("🔧 Kör 'make up' för att starta Alice services")
            recommendations.append("🔧 Kör 'docker compose up -d dev-proxy' för port 8001")
            
        if any("virtual env" in alert.lower() for alert in alerts):
            recommendations.append("🔧 Kör 'python -m venv .venv' för att skapa virtual environment")
            
        # Bestäm overall health
        critical_alerts = [a for a in alerts if "KRITISK" in a]
        warning_alerts = [a for a in alerts if "VARNING" in a or "PROBLEM" in a]
        
        if critical_alerts:
            overall_health = "critical"
        elif warning_alerts:
            overall_health = "warning" 
        elif alerts:
            overall_health = "issues"
        else:
            overall_health = "healthy"
            
        status["overall_health"] = overall_health
        status["alerts"] = alerts
        status["recommendations"] = recommendations
        status["summary"] = {
            "critical_issues": len(critical_alerts),
            "warnings": len(warning_alerts),
            "total_alerts": len(alerts)
        }
        
        return status

    async def start_training_session(self, training_type: str) -> bool:
        """Starta träningssession med full service-kontroll"""
        if training_type not in self.training_types:
            return False
            
        # Förhindra multipla aktiva sessioner
        active_sessions = [s for s in self.sessions.values() if s.status == "running"]
        if active_sessions:
            self.add_global_message(f"❌ Kan inte starta: {len(active_sessions)} träning(ar) pågår redan", "warning")
            return False
            
        config = self.training_types[training_type]
        timestamp = datetime.now().strftime("%H%M%S")
        session_name = f"{training_type}_{timestamp}"
        
        # Kontrollera script
        script_path = config["script"]
        if not Path(script_path).exists():
            self.add_global_message(f"❌ Script inte funnen: {script_path}", "error")
            return False
            
        # Skapa session
        session = SimpleTrainingSession(session_name, script_path, config["name"])
        self.sessions[session_name] = session
        
        self.add_global_message(f"🚀 Startar {config['name']}", "info", session_name)
        
        # Säkerställ att Alice services körs FÖRST - TEMPORÄRT SKIPPAD
        # if not self.ensure_alice_services_running():
        #     session.status = "failed"
        #     self.add_global_message("❌ Kunde inte starta Alice services - träning avbruten", "error", session_name)
        #     return False
        self.add_global_message("⚠️ TEMP: Service-check skippad (port 8001 intermittent issue)", "warning", session_name)
        
        # Starta process
        try:
            cmd = f"source .venv/bin/activate && python {script_path}"
            session.process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, universal_newlines=True
            )
            
            session.status = "running"
            self.add_global_message("✅ Träning startad", "success", session_name)
            
            # Starta monitoring i enkel thread
            monitor_thread = threading.Thread(
                target=self._monitor_session,
                args=(session,),
                daemon=True
            )
            monitor_thread.start()
            
            return True
            
        except Exception as e:
            session.status = "failed"
            self.add_global_message(f"❌ Fel vid start: {str(e)}", "error", session_name)
            return False
            
    def _monitor_session(self, session: SimpleTrainingSession):
        """Enkel monitoring utan async komplexitet"""
        try:
            while session.process and session.process.poll() is None:
                if session.process.stdout:
                    line = session.process.stdout.readline()
                    if line:
                        clean_line = line.strip()
                        if clean_line:
                            level = "info"
                            if "error" in clean_line.lower() or "fail" in clean_line.lower():
                                level = "error"
                            elif "success" in clean_line.lower() or "✅" in clean_line:
                                level = "success"
                            elif "warning" in clean_line.lower() or "⚠️" in clean_line:
                                level = "warning"
                                
                            session.add_message(clean_line, level)
                            # Parse metrics från meddelandet
                            session.parse_metrics_from_message(clean_line)
                            self.add_global_message(clean_line, level, session.name)
                            
                time.sleep(0.2)  # Lite längre paus för stabilitet
                
            # Process slutad
            if session.process:
                return_code = session.process.poll()
                if return_code == 0:
                    session.status = "completed"
                    self.add_global_message("🎉 Träning slutförd", "success", session.name)
                    
                    # Spara historisk data och beräkna förbättringar
                    session_data = session.to_dict()
                    training_type = session.name.split('_')[0]  # 'fibonacci' från 'fibonacci_123456'
                    
                    # Beräkna förbättring mot tidigare
                    improvements = self.get_improvement_vs_previous(training_type, session_data["performance_stats"])
                    
                    if not improvements["is_first_run"]:
                        if improvements["response_time"] < 0:  # Negativ = bättre response time
                            self.add_global_message(f"📈 Response time förbättring: {abs(improvements['response_time']):.1f}% snabbare!", "success", session.name)
                        elif improvements["response_time"] > 0:
                            self.add_global_message(f"📉 Response time: {improvements['response_time']:.1f}% långsammare", "warning", session.name)
                            
                        if improvements["cache_rate"] > 0:
                            self.add_global_message(f"🚀 Cache hit rate förbättring: +{improvements['cache_rate']:.1f}%", "success", session.name)
                        elif improvements["cache_rate"] < 0:
                            self.add_global_message(f"📉 Cache hit rate: {improvements['cache_rate']:.1f}%", "warning", session.name)
                    else:
                        self.add_global_message("🎯 Första träningsrun - inga jämförelser ännu", "info", session.name)
                    
                    # Lägg till i historik
                    self.add_training_to_history(training_type, session_data)
                    
                    # Visa bästa resultat hittills
                    best_stats = self.historical_stats.get(training_type, {})
                    if best_stats.get("best_avg_ms", 999) < 999:
                        self.add_global_message(f"🏆 Bäst hittills: {best_stats['best_avg_ms']:.1f}ms, {best_stats['best_cache_rate']:.1f}% cache", "info", session.name)
                        
                else:
                    session.status = "failed"
                    self.add_global_message(f"❌ Träning misslyckades (kod: {return_code})", "error", session.name)
                    
        except Exception as e:
            session.status = "failed"
            self.add_global_message(f"❌ Monitor fel: {str(e)}", "error", session.name)
            
    def add_global_message(self, message: str, level: str = "info", session_name: str = "SYSTEM"):
        """Lägg till meddelande i global feed"""
        timestamp = datetime.now()
        log_entry = {
            "time": timestamp.strftime("%H:%M:%S"),
            "timestamp": timestamp.isoformat(),
            "level": level, 
            "message": message,
            "session": session_name
        }
        
        self.all_messages.append(log_entry)
        
        # Ring buffer för global feed
        if len(self.all_messages) > 200:
            self.all_messages = self.all_messages[-200:]
            
    def stop_training_session(self, session_name: str) -> bool:
        """Stoppa träningssession"""
        if session_name not in self.sessions:
            return False
            
        session = self.sessions[session_name]
        if session.process and session.process.poll() is None:
            try:
                session.process.terminate()
                session.status = "stopped"
                self.add_global_message("⏹️ Träning stoppad", "warning", session_name)
                return True
            except Exception as e:
                return False
                
        return False
        
    def run_server(self, open_browser: bool = True):
        """Starta web servern"""
        if open_browser:
            def open_browser_delayed():
                time.sleep(2)
                webbrowser.open(f"http://{self.host}:{self.port}")
                
            threading.Thread(target=open_browser_delayed, daemon=True).start()
            
        print(f"🌐 Simple Training HUD startar på http://{self.host}:{self.port}")
        
        uvicorn.run(
            self.app,
            host=self.host, 
            port=self.port,
            log_level="error"  # Mindre verbose
        )

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="🌐 Simple Training Web HUD")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=3001, help="Server port")
    parser.add_argument("--no-browser", action="store_true", help="Öppna inte webbrowser")
    
    args = parser.parse_args()
    
    hud = SimpleTrainingHUD(host=args.host, port=args.port)
    hud.run_server(open_browser=not args.no_browser)

if __name__ == "__main__":
    main()