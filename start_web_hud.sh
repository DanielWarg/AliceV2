#!/bin/bash

# 🌐 Alice v2 Training Web HUD - Quick Start
# Startar web-baserad localhost interface på port 8080

set -euo pipefail

echo "🌐 Alice v2 Training Web HUD - Startar localhost server..."

# Kontrollera att vi är i rätt directory
if [ ! -f "training_web_hud.py" ]; then
    echo "❌ Fel: training_web_hud.py inte funnen. Kör från alice-v2 root directory."
    exit 1
fi

# Aktivera virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Fel: .venv inte funnen. Kör 'python -m venv .venv' först."
    exit 1
fi

echo "📦 Aktiverar virtual environment och kontrollerar dependencies..."
source .venv/bin/activate

# Kontrollera web dependencies
python -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "📦 Installerar web dependencies..."
    pip install fastapi uvicorn jinja2 python-multipart
}

# Kontrollera Docker (behövs för träningar)
echo "🐳 Kontrollerar Alice services..."
if ! docker ps >/dev/null 2>&1; then
    echo "❌ Docker körs inte. Starta Docker först."
    exit 1
fi

# Starta Alice services om de inte körs
if ! docker ps | grep -q alice-orchestrator; then
    echo "🚀 Startar Alice services..."
    make up
    
    # Starta dev-proxy för port 18000 (enligt AGENTS.md)
    echo "🌐 Startar dev-proxy för port 18000..."
    docker compose up -d dev-proxy
    
    echo "⏳ Väntar på att services ska bli klara..."
    sleep 5
else
    echo "✅ Alice services körs redan"
fi

# Kontrollera att port 18000 fungerar
if ! curl -s http://localhost:18000/health >/dev/null; then
    echo "⚠️ Port 18000 svarar inte. Startar dev-proxy..."
    docker compose up -d dev-proxy
    sleep 3
fi

echo ""
echo "🎯 Training Web HUD startar på:"
echo "   👉 http://localhost:8080"
echo ""
echo "🔥 Features:"
echo "   • Real-time träningsmonitoring"  
echo "   • Chat-liknande live feed"
echo "   • Starta/stoppa alla träningstyper"
echo "   • Live metrics och progress"
echo "   • WebSocket real-time updates"
echo ""
echo "🚀 Startar server... (öppnar automatiskt i webbrowser)"
echo ""

# Starta Web HUD servern
python training_web_hud.py --host localhost --port 8080