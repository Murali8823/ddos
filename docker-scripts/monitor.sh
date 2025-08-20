#!/bin/bash
# 📊 Monitor DDoS Lab Script

echo "📊 DDoS Simulation Lab - Live Monitor"
echo "======================================"

# Function to show container status
show_status() {
    echo ""
    echo "🐳 Container Status:"
    docker-compose ps
    echo ""
    echo "📈 Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Function to show logs
show_logs() {
    echo ""
    echo "📋 Recent Logs (C2 Server):"
    docker-compose logs --tail=10 c2-server
    echo ""
    echo "📋 Recent Logs (Bots):"
    docker-compose logs --tail=5 bot-001 bot-002 bot-003
}

# Function to test target server
test_target() {
    echo ""
    echo "🎯 Testing Target Server Response:"
    echo "=================================="
    
    start_time=$(date +%s.%N)
    response=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:8090)
    end_time=$(date +%s.%N)
    
    response_time=$(echo "$end_time - $start_time" | bc)
    
    if [ "$response" = "200" ]; then
        echo "✅ Target server responding: HTTP $response"
        echo "⏱️  Response time: ${response_time}s"
    else
        echo "❌ Target server issues: HTTP $response"
        echo "⏱️  Response time: ${response_time}s"
    fi
}

# Main monitoring loop
case "$1" in
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "target")
        test_target
        ;;
    "live")
        echo "🔄 Starting live monitoring (Ctrl+C to stop)..."
        while true; do
            clear
            echo "📊 DDoS Lab Live Monitor - $(date)"
            echo "=================================="
            show_status
            test_target
            sleep 5
        done
        ;;
    *)
        echo "📊 DDoS Lab Monitor Commands:"
        echo ""
        echo "  $0 status  - Show container status and resources"
        echo "  $0 logs    - Show recent logs"
        echo "  $0 target  - Test target server response"
        echo "  $0 live    - Live monitoring (updates every 5s)"
        echo ""
        echo "🌐 Quick access:"
        echo "  • C2 Dashboard: http://localhost:8080"
        echo "  • Target Server: http://localhost:8090"
        ;;
esac