#!/bin/bash

# Enhanced DecentralChain Stress Test Dashboard Launcher
# Starts the complete monitoring and control system

WORKSPACE="/Users/mac/PY mass transfer script dcc"
cd "$WORKSPACE"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   🎛️  DecentralChain Stress Test Dashboard                ║"
echo "║   Enhanced Real-Time Monitoring & Control System          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Kill any existing dashboard
echo "⏹  Cleaning up existing processes..."
pkill -f dashboard_backend.py 2>/dev/null || true
sleep 1

# Start dashboard
echo "🚀 Starting dashboard backend..."
nohup .venv/bin/python dashboard_backend.py > dashboard.log 2>&1 & 
DASH_PID=$!
echo $DASH_PID > dashboard.pid

# Wait for startup
sleep 3

# Check if running
if ps -p $DASH_PID > /dev/null; then
    echo "✅ Dashboard running (PID: $DASH_PID)"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   📊 DASHBOARD READY                                       ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║   🌐 Open: http://localhost:8888                          ║"
    echo "║   📁 Workspace: $WORKSPACE                                ║"
    echo "║   📜 Logs: tail -f dashboard.log                          ║"
    echo "║   🛑 Stop: pkill -f dashboard_backend.py                 ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Features:"
    echo "  ✓ Real-time KPI monitoring"
    echo "  ✓ Live transaction charts"
    echo "  ✓ Error tracking & analysis"
    echo "  ✓ Wallet status display"
    echo "  ✓ Live log streaming"
    echo "  ✓ One-click test control"
    echo ""
    echo "Monitored Data:"
    echo "  • Total transactions & success rate"
    echo "  • Throughput (tx/sec)"
    echo "  • Error breakdown (asset/balance/checksum)"
    echo "  • Wallet loading & funding status"
    echo "  • Elapsed time & completion %" 
    echo ""
else
    echo "❌ Dashboard failed to start"
    echo "Check dashboard.log for errors:"
    cat dashboard.log
    exit 1
fi
