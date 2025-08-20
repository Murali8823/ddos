#!/bin/bash
# 🤖 Deploy Bot Client on each bot system

if [ -z "$1" ]; then
    echo "🤖 Bot Deployment Script"
    echo "Usage: $0 <C2_SERVER_IP>"
    echo "Example: $0 192.168.1.100"
    exit 1
fi

C2_SERVER_IP=$1
BOT_ID="bot-$(hostname)"

echo "🤖 Deploying Bot Client..."
echo "Bot ID: $BOT_ID"
echo "C2 Server: $C2_SERVER_IP"

# Build bot client image
docker build -f Dockerfile.bot -t ddos-lab/bot-client .

# Run bot client container
docker run -d \
  --name $BOT_ID \
  --restart unless-stopped \
  -e BOT_ID=$BOT_ID \
  -e C2_SERVER_HOST=$C2_SERVER_IP \
  -e C2_SERVER_PORT=8081 \
  -e BOT_NAME=$BOT_ID \
  -e PYTHONPATH=/app \
  ddos-lab/bot-client

echo "✅ Bot $BOT_ID deployed and connecting to C2 server!"
echo "📊 Check status: docker logs $BOT_ID"