#!/bin/bash
# 🐳 Build Docker Images Script

echo "🚀 Building DDoS Simulation Lab Docker Images..."

# Build C2 Server
echo "🏢 Building C2 Server image..."
docker build -f Dockerfile.c2 -t ddos-lab/c2-server:latest .

# Build Bot Client
echo "🤖 Building Bot Client image..."
docker build -f Dockerfile.bot -t ddos-lab/bot-client:latest .

echo "✅ Docker images built successfully!"
echo ""
echo "📋 Available images:"
docker images | grep ddos-lab

echo ""
echo "🎯 Next steps:"
echo "  • Run basic setup: docker-compose up"
echo "  • Run scaled setup: docker-compose -f docker-compose.scale.yml up"
echo "  • Scale bots: docker-compose -f docker-compose.scale.yml up --scale bot=28"