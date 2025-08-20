#!/bin/bash
# 🎮 Run Basic DDoS Lab Setup (3 bots)

echo "🚀 Starting DDoS Simulation Lab - Basic Setup..."
echo "📊 This will start:"
echo "  • 1 C2 Server"
echo "  • 3 Bot clients"
echo "  • 1 Target server (Nginx)"
echo ""

# Create data directory
mkdir -p data
mkdir -p target-content

# Create simple target content
cat > target-content/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>🎯 DDoS Target Server</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; }
        .status { color: green; font-size: 24px; }
    </style>
</head>
<body>
    <h1>🎯 DDoS Simulation Target</h1>
    <div class="status">✅ Server is running normally</div>
    <p>This server is the target for DDoS simulation attacks.</p>
    <p>Monitor response times during attacks!</p>
</body>
</html>
EOF

# Start the lab
docker-compose up -d

echo ""
echo "✅ DDoS Lab is starting up!"
echo ""
echo "🌐 Access points:"
echo "  • C2 Dashboard: http://localhost:8080"
echo "  • Target Server: http://localhost:8090"
echo ""
echo "📊 Monitor with:"
echo "  • docker-compose logs -f"
echo "  • docker-compose ps"
echo ""
echo "🛑 Stop with:"
echo "  • docker-compose down"