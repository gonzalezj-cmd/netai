#!/bin/bash

set -e

echo "=================================="
echo "🚀 INICIANDO SOFTMIKRO V2"
echo "=================================="

cd ~/netai || exit
source venv/bin/activate

pkill -f "uvicorn api_v2:app" || true
pkill -f collector_loop.py || true

sleep 1

nohup uvicorn api_v2:app --host 0.0.0.0 --port 8001 > api_v2.log 2>&1 &
nohup python3 collector_loop.py > collector.log 2>&1 &

echo "✅ SOFTMIKRO V2 INICIADO"
echo "🌐 http://$(hostname -I | awk '{print $1}'):8001/dashboard"
