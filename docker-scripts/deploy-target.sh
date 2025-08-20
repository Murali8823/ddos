#!/bin/bash
# 🎯 Deploy Target Server on victim system

echo "🎯 Deploying Target Server..."

# Create target content
mkdir -p target-content
cat > target-content/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>🎯 DDoS Target Server</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; }
        .status { color: green; font-size: 24px; }
        .info { color: blue; margin: 20px; }
    </style>
</head>
<body>
    <h1>🎯 DDoS Simulation Target</h1>
    <div class="status">✅ Server is running normally</div>
    <div class="info">
        <p>This server is the target for DDoS simulation attacks.</p>
        <p>Server IP: <strong id="server-ip"></strong></p>
        <p>Current Time: <strong id="current-time"></strong></p>
        <p>Requests Served: <strong id="request-count">0</strong></p>
    </div>
    
    <script>
        // Display server info
        document.getElementById('server-ip').textContent = window.location.hostname;
        
        // Update time every second
        setInterval(() => {
            document.getElementById('current-time').textContent = new Date().toLocaleString();
        }, 1000);
        
        // Simulate request counter (for demo)
        let count = 0;
        setInterval(() => {
            count += Math.floor(Math.random() * 10) + 1;
            document.getElementById('request-count').textContent = count;
        }, 2000);
    </script>
</body>
</html>
EOF

# Run target server
docker run -d \
  --name ddos-target-server \
  --restart unless-stopped \
  -p 80:80 \
  -p 8090:80 \
  -v $(pwd)/target-content:/usr/share/nginx/html:ro \
  nginx:alpine

echo "✅ Target Server deployed!"
echo "🌐 Target URL: http://$(hostname -I | awk '{print $1}'):80"
echo "🌐 Alt URL: http://$(hostname -I | awk '{print $1}'):8090"