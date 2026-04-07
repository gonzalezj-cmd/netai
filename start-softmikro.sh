#!/bin/bash

echo "=================================="
echo "🚀 INICIANDO SOFTMIKRO"
echo "=================================="

cd ~/netai || exit

echo "🐍 Activando entorno..."
source venv/bin/activate

echo "🧹 Limpiando procesos anteriores..."
pkill -f uvicorn
pkill -f collector_loop.py

sleep 2

echo "🌐 Iniciando API..."
nohup uvicorn api:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &

sleep 2

echo "📡 Iniciando collector..."
nohup python3 collector_loop.py > collector.log 2>&1 &

echo "=================================="
echo "✅ SOFTMIKRO INICIADO"
echo "🌐 http://$(hostname -I | awk '{print $1}'):8000/dashboard"
echo "=================================="