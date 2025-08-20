#!/bin/bash
# 🚀 Run Scaled DDoS Lab Setup (28 bots)

echo "🚀 Starting DDoS Simulation Lab - FULL SCALE..."
echo "📊 This will start:"
echo "  • 1 C2 Server"
echo "  • 28 Bot clients (scalable)"
echo "  • 1 Target server (Nginx)"
echo ""

# Create data directory
mkdir -p data
mkdir -p target-content

# Create target content
cat > target-content/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>🎯 DDoS Target Server - Full Scale Test</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; }
        .status { color: green; font-size: 24px; }
        .warning { color: orange; font-size: 18px; }
    </style>
</head>
<body>
    <h1>🎯 DDoS Simulation Target - FULL SCALE</h1>
    <div class="status">✅ Server is running normally</div>
    <div class="warning">⚠️ This server will be attacked by 28 bots!</div>
    <p>Monitor response times and server performance during the attack.</p>
    <p>Expected load: ~2,800 requests per second</p>
</body>
</html>
EOF

# Start with scaled bot army
echo "🤖 Deploying 28-bot army..."
docker-compose -f docker-compose.scale.yml up -d
docker-compose -f docker-compose.scale.yml up --scale bot=28 -d

echo ""
echo "✅ Full-scale DDoS Lab is deployed!"
echo ""
echo "🌐 Access points:"
echo "  • C2 Dashboard: http://localhost:8080"
echo "  • Target Server: http://localhost:8090"
echo ""
echo "📊 Monitor the army:"
echo "  • docker-compose -f docker-compose.scale.yml ps"
echo "  • docker-compose -f docker-compose.scale.yml logs -f bot"
echo ""
echo "🛑 Stop the army:"
echo "  • docker-compose -f docker-compose.scale.yml down"