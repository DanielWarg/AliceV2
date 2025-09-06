#!/usr/bin/env python3
"""
🌐 Alice v2 Training Web HUD - localhost web interface

Modern web-baserad träningsmonitor som körs på localhost med:
- Real-time WebSocket updates
- Modern responsive design
- Multi-training orchestration
- Live metrics och progress tracking

Usage:
    python training_web_hud.py                    # Start på localhost:8080
    python training_web_hud.py --port 3000        # Custom port
    python training_web_hud.py --host 0.0.0.0     # Access från andra datorer
"""

import asyncio
import json
import os
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
import signal
import sys
import webbrowser

# Web server dependencies
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.templating import Jinja2Templates
    import uvicorn
except ImportError:
    print("❌ Missing web dependencies. Install with:")
    print("pip install fastapi uvicorn jinja2 python-multipart")
    sys.exit(1)

class TrainingSession:
    """Web-kompatibel träningssession"""
    
    def __init__(self, name: str, script_path: str, session_type: str):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.script_path = script_path  
        self.session_type = session_type
        self.start_time = datetime.now()
        self.status = "starting"
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0,
            "cache_hit_rate": 0
        }
        self.process = None
        self.log_messages = []
        self.last_update = datetime.now()
        
    def add_message(self, message: str, level: str = "info"):
        """Lägg till meddelande och notifiera WebSocket clients"""
        timestamp = datetime.now()
        log_entry = {
            "id": str(uuid.uuid4())[:8],
            "time": timestamp.strftime("%H:%M:%S"),
            "timestamp": timestamp.isoformat(),
            "level": level, 
            "message": message,
            "session": self.name,
            "session_id": self.id
        }
        self.log_messages.append(log_entry)
        self.last_update = timestamp
        
        # Ring buffer - behåll bara senaste 100 meddelanden
        if len(self.log_messages) > 100:
            self.log_messages = self.log_messages[-100:]
            
        return log_entry
        
    def to_dict(self):
        """Serialisera för JSON API"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            "id": self.id,
            "name": self.name,
            "script_path": self.script_path,
            "session_type": self.session_type,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": uptime,
            "uptime_display": f"{int(uptime//60)}:{int(uptime%60):02d}",
            "metrics": self.metrics,
            "message_count": len(self.log_messages),
            "last_update": self.last_update.isoformat()
        }

class WebSocketManager:
    """Hantera WebSocket connections för real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
    async def broadcast(self, data: dict):
        """Skicka data till alla anslutna clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                disconnected.append(connection)
                
        # Ta bort disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

class TrainingWebHUD:
    """Main web HUD server"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.app = FastAPI(title="🧮 Alice v2 Training Web HUD")
        self.sessions: Dict[str, TrainingSession] = {}
        self.websocket_manager = WebSocketManager()
        
        # Träningstyper
        self.training_types = {
            "fibonacci": {
                "name": "🧮 Fibonacci Optimization", 
                "script": "scripts/fibonacci_simple_training.py",
                "description": "Golden ratio performance optimization (φ=1.618)",
                "color": "blue"
            },
            "fibonacci_loop": {
                "name": "🔄 Fibonacci Training Loop",
                "script": "scripts/fibonacci_training_loop.py", 
                "description": "Multi-phase Fibonacci training pipeline",
                "color": "purple"
            },
            "rl_pipeline": {
                "name": "🤖 RL Pipeline", 
                "script": "services/rl/automate_rl_pipeline.py",
                "description": "Reinforcement learning automation",
                "color": "green"
            },
            "cache_bandit": {
                "name": "💾 Cache Bandit RL",
                "script": "services/rl/bandits/cache_bandit.py", 
                "description": "Cache optimization reinforcement learning",
                "color": "orange"
            }
        }
        
        self.setup_routes()
        self.setup_static_files()
        
    def setup_static_files(self):
        """Skapa static files directory om det inte finns"""
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        
        # Skapa HTML template
        self.create_html_template()
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        
    def create_html_template(self):
        """Skapa modern HTML template"""
        html_content = '''<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧮 Alice v2 Training HUD</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 15px;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #00ff88;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        .panel {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .panel h2 {
            margin-bottom: 15px;
            color: #00ff88;
        }
        
        .session-grid {
            display: grid;
            gap: 15px;
        }
        
        .session-card {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #00ff88;
        }
        
        .session-card.running { border-left-color: #00ff88; }
        .session-card.starting { border-left-color: #ffaa00; }
        .session-card.completed { border-left-color: #0088ff; }
        .session-card.failed { border-left-color: #ff4444; }
        
        .session-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .session-name {
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .session-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .status-running { background: #00ff88; color: black; }
        .status-starting { background: #ffaa00; color: black; }
        .status-completed { background: #0088ff; color: white; }
        .status-failed { background: #ff4444; color: white; }
        
        .session-info {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 5px;
        }
        
        .chat-panel {
            height: 400px;
            overflow-y: auto;
        }
        
        .chat-messages {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .chat-message {
            padding: 8px 12px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85em;
            line-height: 1.4;
        }
        
        .chat-message.info { background: rgba(255,255,255,0.1); }
        .chat-message.success { background: rgba(0,255,136,0.2); }
        .chat-message.warning { background: rgba(255,170,0,0.2); }
        .chat-message.error { background: rgba(255,68,68,0.2); }
        
        .message-time {
            opacity: 0.6;
            margin-right: 8px;
        }
        
        .message-session {
            background: rgba(255,255,255,0.2);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75em;
            margin-right: 8px;
        }
        
        .controls {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        
        .control-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        
        .btn-primary {
            background: #00ff88;
            color: black;
        }
        
        .btn-secondary {
            background: #0088ff;
            color: white;
        }
        
        .btn-danger {
            background: #ff4444;
            color: white;
        }
        
        .training-type-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px;
            border-radius: 8px;
            font-weight: bold;
        }
        
        .connected { background: #00ff88; color: black; }
        .disconnected { background: #ff4444; color: white; }
    </style>
</head>
<body>
    <div id="connectionStatus" class="connection-status disconnected">
        🔌 Ansluter...
    </div>
    
    <div class="container">
        <div class="header">
            <h1>🧮 Alice v2 Training HUD</h1>
            <p>Real-time träningsmonitoring på localhost</p>
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
        
        <div class="main-content">
            <div class="panel">
                <h2>📊 Aktiva Träningar</h2>
                <div id="sessionsContainer" class="session-grid">
                    <div style="text-align: center; opacity: 0.5; padding: 40px;">
                        Inga aktiva träningar ännu.<br>
                        Starta din första träning nedan! 👇
                    </div>
                </div>
            </div>
            
            <div class="panel">
                <h2>💬 Live Chat</h2>
                <div id="chatContainer" class="chat-panel">
                    <div class="chat-messages" id="chatMessages">
                        <div class="chat-message info">
                            <span class="message-time">--:--:--</span>
                            <span class="message-session">SYSTEM</span>
                            🎯 Välkommen till Alice Training Web HUD! Starta din första träning nedan.
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <h2>🎮 Kontroller</h2>
            <div class="control-buttons">
                <button class="btn btn-danger" onclick="stopAllTraining()">⏹️ Stoppa Alla</button>
                <button class="btn btn-secondary" onclick="clearChat()">🧹 Rensa Chat</button>
                <button class="btn btn-secondary" onclick="exportMetrics()">📊 Exportera Metrics</button>
            </div>
            
            <h3 style="margin: 20px 0 10px 0;">🚀 Starta Träning</h3>
            <div class="training-type-grid" id="trainingTypes">
                <!-- Genereras dynamiskt -->
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let sessions = {};
        let totalMessages = 0;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                updateConnectionStatus(true);
                console.log('WebSocket connected');
            };
            
            ws.onclose = function() {
                updateConnectionStatus(false);
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateConnectionStatus(false);
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
        }
        
        function updateConnectionStatus(connected) {
            const status = document.getElementById('connectionStatus');
            if (connected) {
                status.textContent = '✅ Ansluten';
                status.className = 'connection-status connected';
            } else {
                status.textContent = '❌ Frånkopplad';
                status.className = 'connection-status disconnected';
            }
        }
        
        function handleWebSocketMessage(data) {
            if (data.type === 'session_update') {
                updateSession(data.session);
            } else if (data.type === 'new_message') {
                addChatMessage(data.message);
            } else if (data.type === 'sessions_list') {
                updateAllSessions(data.sessions);
            }
        }
        
        function updateSession(sessionData) {
            sessions[sessionData.id] = sessionData;
            renderSessions();
            updateStats();
        }
        
        function updateAllSessions(sessionsData) {
            sessions = {};
            sessionsData.forEach(session => {
                sessions[session.id] = session;
            });
            renderSessions();
            updateStats();
        }
        
        function renderSessions() {
            const container = document.getElementById('sessionsContainer');
            const sessionsList = Object.values(sessions);
            
            if (sessionsList.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; opacity: 0.5; padding: 40px;">
                        Inga aktiva träningar ännu.<br>
                        Starta din första träning nedan! 👇
                    </div>
                `;
                return;
            }
            
            container.innerHTML = sessionsList.map(session => `
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
                    <div class="session-info">
                        ${session.session_type}
                    </div>
                    <div class="session-info">
                        ⏱️ Uptime: ${session.uptime_display}
                    </div>
                    <div class="session-info">
                        💬 Meddelanden: ${session.message_count}
                    </div>
                    <div style="margin-top: 10px;">
                        <button class="btn btn-danger" onclick="stopSession('${session.id}')" 
                                style="font-size: 0.8em; padding: 5px 10px;">
                            ⏹️ Stoppa
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        function addChatMessage(message) {
            const chatMessages = document.getElementById('chatMessages');
            const messageElement = document.createElement('div');
            messageElement.className = `chat-message ${message.level}`;
            messageElement.innerHTML = `
                <span class="message-time">${message.time}</span>
                <span class="message-session">${message.session}</span>
                ${message.message}
            `;
            
            chatMessages.appendChild(messageElement);
            totalMessages++;
            
            // Scroll to bottom
            const chatContainer = document.getElementById('chatContainer');
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            // Ring buffer - behåll bara senaste 50 meddelanden i UI
            const messages = chatMessages.children;
            if (messages.length > 50) {
                chatMessages.removeChild(messages[0]);
            }
            
            updateStats();
        }
        
        function updateStats() {
            const activeCount = Object.values(sessions).filter(s => 
                s.status === 'running' || s.status === 'starting'
            ).length;
            
            document.getElementById('activeSessions').textContent = activeCount;
            document.getElementById('totalSessions').textContent = Object.keys(sessions).length;
            document.getElementById('totalMessages').textContent = totalMessages;
        }
        
        async function startTraining(trainingType) {
            try {
                const response = await fetch('/api/start-training', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ training_type: trainingType })
                });
                
                const result = await response.json();
                if (!result.success) {
                    alert(`Fel vid start av träning: ${result.error}`);
                }
            } catch (error) {
                alert(`Fel: ${error.message}`);
            }
        }
        
        async function stopSession(sessionId) {
            try {
                const response = await fetch('/api/stop-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                });
                
                const result = await response.json();
                if (!result.success) {
                    alert(`Fel vid stopp: ${result.error}`);
                }
            } catch (error) {
                alert(`Fel: ${error.message}`);
            }
        }
        
        async function stopAllTraining() {
            if (!confirm('Är du säker på att du vill stoppa alla träningar?')) return;
            
            try {
                const response = await fetch('/api/stop-all', { method: 'POST' });
                const result = await response.json();
                alert(`Stoppade ${result.stopped_count} träningar`);
            } catch (error) {
                alert(`Fel: ${error.message}`);
            }
        }
        
        function clearChat() {
            document.getElementById('chatMessages').innerHTML = '';
            totalMessages = 0;
            updateStats();
        }
        
        async function exportMetrics() {
            try {
                const response = await fetch('/api/export-metrics');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `training_metrics_${new Date().toISOString().slice(0,19)}.json`;
                a.click();
                window.URL.revokeObjectURL(url);
            } catch (error) {
                alert(`Fel vid export: ${error.message}`);
            }
        }
        
        async function loadTrainingTypes() {
            try {
                const response = await fetch('/api/training-types');
                const types = await response.json();
                
                const container = document.getElementById('trainingTypes');
                container.innerHTML = Object.entries(types).map(([key, config]) => `
                    <button class="btn btn-primary" onclick="startTraining('${key}')">
                        ${config.name}
                    </button>
                `).join('');
            } catch (error) {
                console.error('Fel vid laddning av träningstyper:', error);
            }
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            connectWebSocket();
            loadTrainingTypes();
            
            // Uppdatera sessions var 5:e sekund som backup
            setInterval(async () => {
                try {
                    const response = await fetch('/api/sessions');
                    const sessions = await response.json();
                    updateAllSessions(sessions);
                } catch (error) {
                    console.error('Fel vid sessionuppdatering:', error);
                }
            }, 5000);
        });
    </script>
</body>
</html>'''
        
        with open("static/index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            with open("static/index.html", encoding="utf-8") as f:
                return HTMLResponse(f.read())
                
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.websocket_manager.connect(websocket)
            try:
                # Skicka nuvarande sessions vid anslutning
                sessions_data = [s.to_dict() for s in self.sessions.values()]
                await websocket.send_json({
                    "type": "sessions_list",
                    "sessions": sessions_data
                })
                
                while True:
                    # Vänta på disconnect
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.websocket_manager.disconnect(websocket)
                
        @self.app.get("/api/sessions")
        async def get_sessions():
            return [s.to_dict() for s in self.sessions.values()]
            
        @self.app.get("/api/training-types")
        async def get_training_types():
            return self.training_types
            
        @self.app.post("/api/start-training")
        async def start_training_api(request: Request):
            data = await request.json()
            training_type = data.get("training_type")
            
            if training_type not in self.training_types:
                return JSONResponse({"success": False, "error": "Okänd träningstyp"})
                
            success = await self.start_training_session(training_type)
            return JSONResponse({"success": success})
            
        @self.app.post("/api/stop-session")
        async def stop_session_api(request: Request):
            data = await request.json()
            session_id = data.get("session_id")
            
            session = None
            for s in self.sessions.values():
                if s.id == session_id:
                    session = s
                    break
                    
            if not session:
                return JSONResponse({"success": False, "error": "Session inte funnen"})
                
            success = self.stop_training_session(session.name)
            return JSONResponse({"success": success})
            
        @self.app.post("/api/stop-all")
        async def stop_all_api():
            stopped_count = 0
            for session_name in list(self.sessions.keys()):
                if self.stop_training_session(session_name):
                    stopped_count += 1
            return JSONResponse({"stopped_count": stopped_count})
            
        @self.app.get("/api/export-metrics")
        async def export_metrics_api():
            metrics_data = {
                "timestamp": datetime.now().isoformat(),
                "sessions": {name: session.to_dict() for name, session in self.sessions.items()},
                "total_sessions": len(self.sessions),
                "active_sessions": len([s for s in self.sessions.values() if s.status in ["running", "starting"]])
            }
            
            return JSONResponse(metrics_data)
            
    async def start_training_session(self, training_type: str, session_name: Optional[str] = None) -> bool:
        """Starta träningssession med WebSocket notifications"""
        if training_type not in self.training_types:
            return False
            
        config = self.training_types[training_type]
        if not session_name:
            timestamp = datetime.now().strftime("%H%M%S")
            session_name = f"{training_type}_{timestamp}"
            
        # Kontrollera script
        script_path = config["script"]
        if not Path(script_path).exists():
            return False
            
        # Skapa session
        session = TrainingSession(session_name, script_path, config["name"])
        self.sessions[session_name] = session
        
        # Notify WebSocket clients
        await self.websocket_manager.broadcast({
            "type": "session_update",
            "session": session.to_dict()
        })
        
        log_entry = session.add_message(f"🚀 Startar {config['name']}", "info")
        await self.websocket_manager.broadcast({
            "type": "new_message",
            "message": log_entry
        })
        
        # Starta process
        try:
            cmd = f"source .venv/bin/activate && python {script_path}"
            session.process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, universal_newlines=True
            )
            
            session.status = "running"
            await self.websocket_manager.broadcast({
                "type": "session_update", 
                "session": session.to_dict()
            })
            
            log_entry = session.add_message("✅ Träning startad", "success")
            await self.websocket_manager.broadcast({
                "type": "new_message",
                "message": log_entry
            })
            
            # Starta monitoring
            monitor_thread = threading.Thread(
                target=self._monitor_session_async,
                args=(session,),
                daemon=True
            )
            monitor_thread.start()
            
            return True
            
        except Exception as e:
            session.status = "failed"
            log_entry = session.add_message(f"❌ Fel vid start: {str(e)}", "error")
            await self.websocket_manager.broadcast({
                "type": "session_update",
                "session": session.to_dict()
            })
            await self.websocket_manager.broadcast({
                "type": "new_message", 
                "message": log_entry
            })
            return False
            
    def _monitor_session_async(self, session: TrainingSession):
        """Monitor session och skicka updates via WebSocket"""
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
                                
                            log_entry = session.add_message(clean_line, level)
                            
                            # Broadcast via WebSocket (async safe)
                            asyncio.run_coroutine_threadsafe(
                                self.websocket_manager.broadcast({
                                    "type": "new_message",
                                    "message": log_entry
                                }),
                                asyncio.get_event_loop()
                            )
                            
                time.sleep(0.1)
                
            # Process slutad
            if session.process:
                return_code = session.process.poll()
                if return_code == 0:
                    session.status = "completed"
                    log_entry = session.add_message("🎉 Träning slutförd", "success")
                else:
                    session.status = "failed"
                    log_entry = session.add_message(f"❌ Träning misslyckades (kod: {return_code})", "error")
                    
                # Final WebSocket update
                asyncio.run_coroutine_threadsafe(
                    self.websocket_manager.broadcast({
                        "type": "session_update",
                        "session": session.to_dict()
                    }),
                    asyncio.get_event_loop()
                )
                asyncio.run_coroutine_threadsafe(
                    self.websocket_manager.broadcast({
                        "type": "new_message", 
                        "message": log_entry
                    }),
                    asyncio.get_event_loop()
                )
                
        except Exception as e:
            session.status = "failed"
            log_entry = session.add_message(f"❌ Monitor fel: {str(e)}", "error")
            asyncio.run_coroutine_threadsafe(
                self.websocket_manager.broadcast({
                    "type": "new_message",
                    "message": log_entry
                }),
                asyncio.get_event_loop()
            )
            
    def stop_training_session(self, session_name: str) -> bool:
        """Stoppa träningssession"""
        if session_name not in self.sessions:
            return False
            
        session = self.sessions[session_name]
        if session.process and session.process.poll() is None:
            try:
                session.process.terminate()
                session.status = "stopped"
                log_entry = session.add_message("⏹️ Träning stoppad", "warning")
                
                # Broadcast update
                asyncio.create_task(self.websocket_manager.broadcast({
                    "type": "session_update",
                    "session": session.to_dict()
                }))
                asyncio.create_task(self.websocket_manager.broadcast({
                    "type": "new_message",
                    "message": log_entry
                }))
                
                return True
            except Exception as e:
                return False
                
        return False
        
    def run_server(self, open_browser: bool = True):
        """Starta web servern"""
        if open_browser:
            # Öppna webbrowser automatiskt efter kort delay
            def open_browser_delayed():
                time.sleep(2)
                webbrowser.open(f"http://{self.host}:{self.port}")
                
            threading.Thread(target=open_browser_delayed, daemon=True).start()
            
        print(f"🌐 Training Web HUD startar på http://{self.host}:{self.port}")
        print(f"🎯 Öppna i webbrowser för att komma åt interfacet")
        
        # Använd run direkt istället för asyncio.run för att undvika event loop konflikt
        import uvicorn
        uvicorn.run(
            self.app,
            host=self.host, 
            port=self.port,
            log_level="info",
            access_log=False  # Mindre verbose logging
        )

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="🌐 Alice v2 Training Web HUD")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Öppna inte webbrowser automatiskt")
    
    args = parser.parse_args()
    
    # Kontrollera att vi är i rätt directory - leta efter en av våra filer
    if not (Path("training_hud.py").exists() or Path("scripts/fibonacci_simple_training.py").exists()):
        print("❌ Fel: Kör från alice-v2 root directory")
        sys.exit(1)
        
    hud = TrainingWebHUD(host=args.host, port=args.port)
    hud.run_server(open_browser=not args.no_browser)

if __name__ == "__main__":
    main()