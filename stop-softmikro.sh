#!/bin/bash

echo "🛑 Deteniendo SOFTMIKRO..."

pkill -f uvicorn
pkill -f collector_loop.py

sleep 1

echo "✅ Detenido"