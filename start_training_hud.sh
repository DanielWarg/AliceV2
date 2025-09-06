#!/bin/bash

# 🧮 Alice v2 Training HUD - Quick Start Script
# 
# Detta script startar Training HUD med pre-konfigurerade inställningar
# och förbereder systemet för träningsmonitoring.

set -euo pipefail

echo "🧮 Alice v2 Training HUD - Startar..."

# Kontrollera att vi är i rätt directory
if [ ! -f "training_hud.py" ]; then
    echo "❌ Fel: training_hud.py inte funnen. Kör från alice-v2 root directory."
    exit 1
fi

# Kontrollera virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Fel: .venv inte funnen. Kör 'python -m venv .venv' först."
    exit 1
fi

# Aktivera venv och kontrollera dependencies
echo "📦 Kontrollerar dependencies..."
source .venv/bin/activate

# Installera Rich om det inte finns
if ! python -c "import rich" 2>/dev/null; then
    echo "📦 Installerar Rich för beautiful terminal UI..."
    pip install rich
fi

# Kontrollera att Docker services körs (behövs för träningar)
echo "🐳 Kontrollerar Docker services..."
if ! docker ps >/dev/null 2>&1; then
    echo "❌ Docker körs inte. Starta Docker först."
    exit 1
fi

# Kontrollera att Alice services körs
if ! docker ps | grep -q alice-orchestrator; then
    echo "🚀 Alice services körs inte. Startar grundläggande services..."
    make up
    
    # Starta dev-proxy för port 18000 (enligt AGENTS.md fix)
    echo "🌐 Startar dev-proxy för port 18000..."
    docker compose up -d dev-proxy
    
    echo "⏳ Väntar på att services ska bli klara..."
    sleep 5
fi

# Kontrollera att port 18000 fungerar
echo "🔍 Kontrollerar att Alice API är tillgänglig på port 18000..."
if ! curl -s http://localhost:18000/health >/dev/null; then
    echo "⚠️ Port 18000 svarar inte. Startar dev-proxy..."
    docker compose up -d dev-proxy
    sleep 3
    
    if ! curl -s http://localhost:18000/health >/dev/null; then
        echo "❌ Alice API inte tillgänglig. Kontrollera att 'make up' fungerar."
        echo "💡 Tips: Kör 'docker compose up -d dev-proxy' manuellt"
        exit 1
    fi
fi

echo "✅ System ready! Alice API svarar på http://localhost:18000"

# Visa snabba instruktioner
echo ""
echo "🎯 Training HUD Quick Start:"
echo "   Välj ett alternativ nedan..."
echo ""

# Interaktiv meny
echo "1) 🧮 Starta bara HUD (manuell träningsstart)"
echo "2) 🚀 Auto-starta Fibonacci training + HUD"  
echo "3) 🤖 Auto-starta RL pipeline + HUD"
echo "4) ⚡ Auto-starta alla träningar + HUD"
echo "5) 📚 Visa full dokumentation först"
echo ""

read -p "Välj (1-5): " choice

case $choice in
    1)
        echo "🧮 Startar Training HUD..."
        python training_hud.py
        ;;
    2)
        echo "🧮 Auto-startar Fibonacci training..."
        python training_hud.py --auto-start fibonacci
        ;;
    3)
        echo "🤖 Auto-startar RL pipeline..."
        python training_hud.py --auto-start rl_pipeline
        ;;
    4)
        echo "⚡ Auto-startar alla träningar..."
        python training_hud.py --auto-start fibonacci,rl_pipeline,cache_bandit
        ;;
    5)
        echo "📚 Visar dokumentation..."
        if command -v less >/dev/null; then
            less TRAINING_HUD.md
        else
            cat TRAINING_HUD.md
        fi
        echo ""
        echo "🧮 Startar HUD efter dokumentation..."
        python training_hud.py
        ;;
    *)
        echo "❌ Ogiltigt val. Startar standard HUD..."
        python training_hud.py
        ;;
esac