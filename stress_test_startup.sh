#!/bin/bash
# 🔥 Backend Startup Stresstest - Säkerställer att systemet startar VARJE gång
# Kör make down/up i loop och verifierar att alla tjänster fungerar

set -e

ITERATIONS=${1:-10}  # Default 10 gånger, eller använd argument
FAILED=0
PASSED=0

echo "🔥 STRESSTEST: Testar backend startup $ITERATIONS gånger"
echo "=================================="

for i in $(seq 1 $ITERATIONS); do
    echo ""
    echo "🚀 ITERATION $i/$ITERATIONS"
    echo "------------------------"
    
    # Stäng ner allt
    echo "⬇️  Stänger ner..."
    make down > /dev/null 2>&1 || true
    
    # Vänta lite för att säkerställa cleanup
    sleep 2
    
    # Starta upp
    echo "⬆️  Startar upp..."
    if ! make up > /dev/null 2>&1; then
        echo "❌ FAILED: make up misslyckades iteration $i"
        ((FAILED++))
        continue
    fi
    
    # Vänta på att servicerna ska starta
    echo "⏳ Väntar på tjänster..."
    sleep 10
    
    # Testa alla kritiska tjänster
    echo "🔍 Testar tjänster..."
    
    # Test 1: API funktionalitet
    if curl -m 5 http://localhost:8001/api/orchestrator/chat \
        -H 'Content-Type: application/json' \
        -d '{"message":"stresstest","session_id":"test'$i'"}' \
        > /dev/null 2>&1; then
        echo "  ✅ Alice API (8001) - OK"
    else
        echo "  ❌ Alice API (8001) - FAIL"
        ((FAILED++))
        continue
    fi
    
    # Test 2: Guardian
    if curl -m 3 http://localhost:8787/health > /dev/null 2>&1; then
        echo "  ✅ Guardian (8787) - OK"
    else
        echo "  ❌ Guardian (8787) - FAIL"
        ((FAILED++))
        continue
    fi
    
    # Test 3: NLU
    if curl -m 3 http://localhost:9002/health > /dev/null 2>&1; then
        echo "  ✅ NLU (9002) - OK"
    else
        echo "  ❌ NLU (9002) - FAIL"
        ((FAILED++))
        continue
    fi
    
    # Test 4: Redis
    if redis-cli -p 6379 ping > /dev/null 2>&1; then
        echo "  ✅ Redis (6379) - OK"
    else
        echo "  ❌ Redis (6379) - FAIL"
        ((FAILED++))
        continue
    fi
    
    # Test 5: Dev-proxy på nya porten
    if curl -m 3 http://localhost:19000 > /dev/null 2>&1; then
        echo "  ✅ Dev-proxy (19000) - OK"
    else
        echo "  ⚠️  Dev-proxy (19000) - WARNING (kan vara OK om orchestrator har problem)"
    fi
    
    echo "  🎉 ITERATION $i - PASSED"
    ((PASSED++))
done

# Slutresultat
echo ""
echo "🏁 STRESSTEST RESULTAT"
echo "======================"
echo "✅ PASSED: $PASSED/$ITERATIONS"
echo "❌ FAILED: $FAILED/$ITERATIONS"

if [ $FAILED -eq 0 ]; then
    echo "🎊 PERFEKT! Alla $ITERATIONS iterationer lyckades!"
    echo "Backend är stabil och pålitlig för produktion."
else
    echo "⚠️  VARNING: $FAILED/$ITERATIONS iterationer misslyckades"
    echo "Backend behöver stabiliseras innan Fibonacci-test."
    exit 1
fi