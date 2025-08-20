#!/bin/bash
# 🏢 Deploy C2 Server on dedicated system

echo "🏢 Deploying C2 Server..."

# Build C2 server image
docker build -f Dockerfile.c2 -t ddos-lab/c2-server .

# Run C2 server container
docker run -d \
  --name ddos-c2-server \
  --restart unless-stopped \
  -p 8080:8080 \
  -p 8081:8081 \
  -v $(pwd)/data:/app/data \
  -e PYTHONPATH=/app \
  -e DATABASE_PATH=/app/data/ddos_lab.db \
  ddos-lab/c2-server

echo "✅ C2 Server deployed!"
echo "🌐 Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo "📡 WebSocket: ws://$(hostname -I | awk '{print $1}'):8081"