# Phase 7: Troubleshooting Commands

This file contains comprehensive troubleshooting commands for common issues in the DDoS simulation lab.

## Prerequisites
- Basic understanding of the lab setup
- Access to C2 server and bot machines
- Administrative privileges where needed

## Section 1: C2 Server Issues

### C2 Server Won't Start

```bash
# Check service status
sudo systemctl status ddos-c2 -l

# Check detailed logs
sudo journalctl -u ddos-c2 --no-pager -l

# Check if ports are in use
sudo netstat -tlnp | grep -E ':(8080|8081)'
sudo lsof -i :8080
sudo lsof -i :8081

# Kill processes using the ports
sudo pkill -f "c2_server"
sudo fuser -k 8080/tcp
sudo fuser -k 8081/tcp

# Check configuration file
sudo -u ddos-c2 cat /opt/ddos-c2/c2_config.json

# Test configuration manually
sudo -u ddos-c2 /opt/ddos-c2/venv/bin/python -c "
import json
with open('/opt/ddos-c2/c2_config.json') as f:
    config = json.load(f)
print('Configuration loaded successfully')
print(f'Server will bind to: {config[\"c2_server\"][\"host\"]}:{config[\"c2_server\"][\"port\"]}')
"

# Restart service
sudo systemctl restart ddos-c2
sudo systemctl status ddos-c2
```

### C2 Server Database Issues

```bash
# Check database file permissions
ls -la /opt/ddos-c2/ddos_lab.db
sudo chown ddos-c2:ddos-c2 /opt/ddos-c2/ddos_lab.db

# Test database connection
sudo -u ddos-c2 /opt/ddos-c2/venv/bin/python -c "
import sqlite3
try:
    conn = sqlite3.connect('/opt/ddos-c2/ddos_lab.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\";')
    tables = cursor.fetchall()
    print(f'Database tables: {tables}')
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database error: {e}')
"

# Recreate database if corrupted
sudo systemctl stop ddos-c2
sudo -u ddos-c2 mv /opt/ddos-c2/ddos_lab.db /opt/ddos-c2/ddos_lab.db.backup
sudo systemctl start ddos-c2
```

### C2 Server Network Issues

```bash
# Check network interface
ip addr show

# Check routing
ip route show

# Test local connectivity
curl http://localhost:8080/health
curl http://localhost:8081

# Check firewall rules
sudo ufw status verbose
sudo iptables -L -n

# Test from external machine
# Run on another machine:
curl http://192.168.1.100:8080/health
telnet 192.168.1.100 8080

# Check if service is binding correctly
sudo ss -tlnp | grep -E ':(8080|8081)'
```

### C2 Server Performance Issues

```bash
# Check system resources
top -p $(pgrep -f c2_server)
htop -p $(pgrep -f c2_server)

# Check memory usage
sudo -u ddos-c2 /opt/ddos-c2/venv/bin/python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"

# Check disk space
df -h /opt/ddos-c2
df -h /var/log/ddos-lab

# Check log file sizes
ls -lh /var/log/ddos-lab/
sudo du -sh /var/log/ddos-lab/*

# Rotate logs if too large
sudo logrotate -f /etc/logrotate.d/ddos-lab
```

## Section 2: Bot Client Issues

### Bot Won't Connect to C2 Server

```bash
# Check bot service status
sudo systemctl status ddos-bot -l

# Check bot logs
sudo journalctl -u ddos-bot -f
sudo tail -f /var/log/ddos-lab/bot_client.log

# Test network connectivity to C2 server
ping -c 3 192.168.1.100
telnet 192.168.1.100 8081
curl http://192.168.1.100:8080/health

# Check bot configuration
sudo cat /opt/ddos-bot/bot_config.json

# Test WebSocket connection manually
sudo -u ddos-bot /opt/ddos-bot/venv/bin/python -c "
import asyncio
import websockets

async def test_connection():
    try:
        uri = 'ws://192.168.1.100:8081/ws/bot/test-bot'
        async with websockets.connect(uri) as websocket:
            print('WebSocket connection successful')
            await websocket.send('test message')
            response = await websocket.recv()
            print(f'Received: {response}')
    except Exception as e:
        print(f'WebSocket connection failed: {e}')

asyncio.run(test_connection())
"

# Restart bot service
sudo systemctl restart ddos-bot
sudo systemctl status ddos-bot
```

### Bot Authentication/Registration Issues

```bash
# Check bot ID generation
sudo -u ddos-bot /opt/ddos-bot/venv/bin/python -c "
from shared.utils import generate_bot_id, get_local_ip, get_hostname
print(f'Bot ID: {generate_bot_id()}')
print(f'Local IP: {get_local_ip()}')
print(f'Hostname: {get_hostname()}')
"

# Check network validation
sudo -u ddos-bot /opt/ddos-bot/venv/bin/python -c "
from shared.config import LabConfig
from bot_client.safety_validator import SafetyValidator

config = LabConfig.load_from_file('/opt/ddos-bot/bot_config.json')
validator = SafetyValidator(config.network, config.safety)

# Test network interface validation
is_valid, interfaces = validator.validate_network_interfaces()
print(f'Network interfaces valid: {is_valid}')
for interface in interfaces:
    print(f'  {interface[\"name\"]}: {interface[\"is_valid\"]}')
"

# Check if bot appears in C2 server
curl -s http://192.168.1.100:8080/api/bots | python3 -c "
import sys, json
data = json.load(sys.stdin)
bot_ips = [bot['ip_address'] for bot in data['bots']]
local_ip = '$(hostname -I | awk \"{print \$1}\")'
if local_ip in bot_ips:
    print(f'✓ Bot with IP {local_ip} is registered')
else:
    print(f'✗ Bot with IP {local_ip} is NOT registered')
    print(f'Registered IPs: {bot_ips}')
"
```

### Bot Attack Execution Issues

```bash
# Check bot capabilities
sudo -u ddos-bot /opt/ddos-bot/venv/bin/python -c "
from shared.models import AttackType
print('Supported attack types:')
for attack_type in AttackType:
    print(f'  - {attack_type.value}')
"

# Test raw socket capability (for TCP SYN floods)
sudo -u ddos-bot /opt/ddos-bot/venv/bin/python -c "
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
    print('✓ Raw socket creation successful (TCP SYN flood available)')
    sock.close()
except PermissionError:
    print('✗ Raw socket permission denied (TCP SYN flood unavailable)')
    print('  Solution: Ensure bot service has CAP_NET_RAW capability')
except Exception as e:
    print(f'✗ Raw socket error: {e}')
"

# Check attack module imports
sudo -u ddos-bot /opt/ddos-bot/venv/bin/python -c "
try:
    from bot_client.attack_modules import HTTPFloodAttack, TCPSYNFloodAttack, UDPFloodAttack
    print('✓ All attack modules imported successfully')
except ImportError as e:
    print(f'✗ Attack module import error: {e}')
"

# Test HTTP attack capability
sudo -u ddos-bot /opt/ddos-bot/venv/bin/python -c "
import asyncio
import aiohttp

async def test_http():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://192.168.1.200') as response:
                print(f'✓ HTTP test successful: {response.status}')
    except Exception as e:
        print(f'✗ HTTP test failed: {e}')

asyncio.run(test_http())
"
```

### Bot Resource Issues

```bash
# Check bot system resources
free -h
df -h
top -bn1 | head -20

# Check bot process resources
ps aux | grep ddos-bot
sudo systemctl show ddos-bot --property=MainPID
top -p $(sudo systemctl show ddos-bot --property=MainPID --value)

# Check file descriptor limits
sudo -u ddos-bot bash -c 'ulimit -n'
cat /proc/$(sudo systemctl show ddos-bot --property=MainPID --value)/limits

# Check network connections
sudo netstat -tulpn | grep $(sudo systemctl show ddos-bot --property=MainPID --value)

# Monitor bot performance
sudo -u ddos-bot /opt/ddos-bot/venv/bin/python -c "
import psutil
import os

process = psutil.Process(os.getpid())
print(f'CPU usage: {process.cpu_percent()}%')
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
print(f'Open files: {process.num_fds()}')
print(f'Connections: {len(process.connections())}')
"
```

## Section 3: Network Issues

### Network Connectivity Problems

```bash
# Test basic connectivity
ping -c 3 192.168.1.100  # C2 server
ping -c 3 192.168.1.200  # Target
ping -c 3 8.8.8.8        # Internet

# Check routing table
ip route show
route -n

# Check DNS resolution
nslookup 192.168.1.100
dig 192.168.1.100

# Test specific ports
telnet 192.168.1.100 8080
telnet 192.168.1.100 8081
telnet 192.168.1.200 80

# Use netcat for port testing
nc -zv 192.168.1.100 8080
nc -zv 192.168.1.100 8081
nc -zv 192.168.1.200 80

# Check network interface status
ip link show
ethtool eth0  # Replace with your interface name
```

### Firewall Issues

```bash
# Check UFW status (Ubuntu/Debian)
sudo ufw status verbose
sudo ufw show raw

# Check iptables rules
sudo iptables -L -n -v
sudo iptables -t nat -L -n -v

# Check firewalld (CentOS/RHEL)
sudo firewall-cmd --list-all
sudo firewall-cmd --list-ports

# Temporarily disable firewall for testing
sudo ufw disable  # Ubuntu/Debian
sudo systemctl stop firewalld  # CentOS/RHEL

# Re-enable after testing
sudo ufw enable
sudo systemctl start firewalld

# Add specific rules if needed
sudo ufw allow from 192.168.1.0/24 to any port 8080
sudo ufw allow from 192.168.1.0/24 to any port 8081
```

### Network Performance Issues

```bash
# Check network statistics
cat /proc/net/dev
netstat -i

# Monitor network traffic
sudo iftop -i eth0
sudo nethogs
sudo tcpdump -i eth0 host 192.168.1.100

# Check for packet loss
ping -c 100 192.168.1.100 | tail -2

# Test bandwidth
# Install iperf3 first: sudo apt install iperf3
# On target: iperf3 -s
# On bot: iperf3 -c 192.168.1.200

# Check network buffer sizes
cat /proc/sys/net/core/rmem_max
cat /proc/sys/net/core/wmem_max
```

## Section 4: Target System Issues

### Windows Target Not Responding

```cmd
REM Run these commands on Windows target

REM Check web server status
sc query w3svc
sc query Apache2.4

REM Check port listeners
netstat -an | findstr :80
netstat -an | findstr :443

REM Check firewall status
netsh advfirewall show allprofiles state

REM Test local web server
curl http://localhost
curl http://127.0.0.1

REM Check system resources
wmic cpu get loadpercentage /value
wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value

REM Check event logs
eventvwr
```

### Windows Target Performance Issues

```cmd
REM Monitor system performance
perfmon
resmon

REM Check running processes
tasklist /svc
wmic process get processid,percentprocessortime,workingsetsize

REM Check network connections
netstat -an | findstr ESTABLISHED
netstat -e

REM Check disk space
dir C:\ /-c
wmic logicaldisk get size,freespace,caption

REM Restart web services if needed
net stop w3svc
net start w3svc

REM Or for Apache
net stop Apache2.4
net start Apache2.4
```

### Windows Target Network Issues

```cmd
REM Check IP configuration
ipconfig /all

REM Test connectivity to C2 server
ping 192.168.1.100
telnet 192.168.1.100 8080

REM Check routing
route print

REM Flush DNS cache
ipconfig /flushdns

REM Reset network stack if needed
netsh winsock reset
netsh int ip reset
REM Reboot required after these commands
```

## Section 5: Attack Execution Issues

### Attacks Not Starting

```bash
# Check C2 server status
curl -s http://localhost:8080/api/status | python3 -m json.tool

# Check connected bots
curl -s http://localhost:8080/api/bots | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Connected bots: {len(data[\"bots\"])}/28')
connected = [bot for bot in data['bots'] if bot['status'] == 'connected']
print(f'Ready bots: {len(connected)}')
"

# Test attack command manually
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "test-attack",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 1,
    "duration": 10
  }' -v

# Check command status
curl -s http://localhost:8080/api/commands | python3 -m json.tool

# Check for validation errors
curl -s http://localhost:8080/api/logs?limit=10 | python3 -c "
import sys, json
data = json.load(sys.stdin)
for log in data['logs'][-10:]:
    if 'ERROR' in log['level'] or 'validation' in log['message'].lower():
        print(f'{log[\"timestamp\"]}: {log[\"message\"]}')
"
```

### Attacks Not Effective

```bash
# Check attack intensity
curl -s http://localhost:8080/api/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('current_attack'):
    attack = data['current_attack']
    print(f'Attack type: {attack[\"attack_type\"]}')
    print(f'Target: {attack[\"target_ip\"]}:{attack[\"target_port\"]}')
    print(f'Intensity: {attack[\"intensity\"]} req/sec per bot')
    print(f'Active bots: {len(attack[\"active_bots\"])}')
    total_rps = attack['intensity'] * len(attack['active_bots'])
    print(f'Total RPS: {total_rps}')
else:
    print('No active attack')
"

# Test target response manually
time curl http://192.168.1.200
time curl http://192.168.1.200/large_file.txt

# Check target system load (run on Windows target)
# wmic cpu get loadpercentage /value

# Increase attack intensity
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_id": "intense-attack",
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 100,
    "duration": 60
  }'
```

### Bot Coordination Issues

```bash
# Check bot synchronization
curl -s http://localhost:8080/api/bots | python3 -c "
import sys, json
from collections import Counter

data = json.load(sys.stdin)
bots = data['bots']

# Check status distribution
statuses = [bot['status'] for bot in bots]
status_count = Counter(statuses)

print('Bot Status Distribution:')
for status, count in status_count.items():
    print(f'  {status}: {count}')

# Check last heartbeat times
from datetime import datetime, timedelta
now = datetime.now()
stale_bots = []

for bot in bots:
    try:
        last_heartbeat = datetime.fromisoformat(bot['last_heartbeat'].replace('Z', '+00:00'))
        age = (now - last_heartbeat.replace(tzinfo=None)).total_seconds()
        if age > 60:  # More than 1 minute old
            stale_bots.append((bot['bot_id'], age))
    except:
        stale_bots.append((bot['bot_id'], 'unknown'))

if stale_bots:
    print(f'\\nStale bots ({len(stale_bots)}):')
    for bot_id, age in stale_bots[:5]:
        print(f'  {bot_id}: {age}s ago')
"

# Restart stale bots
for i in {101..128}; do
    echo "Checking bot on 192.168.1.$i"
    ssh root@192.168.1.$i "systemctl is-active ddos-bot" || \
    ssh root@192.168.1.$i "systemctl restart ddos-bot"
done
```

## Section 6: Performance Issues

### System Resource Problems

```bash
# Check overall system load
uptime
top -bn1 | head -5
htop

# Check memory usage
free -h
cat /proc/meminfo | grep -E "(MemTotal|MemFree|MemAvailable)"

# Check disk usage
df -h
du -sh /opt/ddos-c2
du -sh /var/log/ddos-lab

# Check swap usage
swapon -s
cat /proc/swaps

# Check for memory leaks
ps aux --sort=-%mem | head -10
pmap -x $(pgrep -f c2_server)

# Monitor system resources during attack
while true; do
    echo "$(date): CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}'), Memory: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
    sleep 5
done
```

### Database Performance Issues

```bash
# Check database size
ls -lh /opt/ddos-c2/ddos_lab.db

# Check database integrity
sudo -u ddos-c2 sqlite3 /opt/ddos-c2/ddos_lab.db "PRAGMA integrity_check;"

# Optimize database
sudo systemctl stop ddos-c2
sudo -u ddos-c2 sqlite3 /opt/ddos-c2/ddos_lab.db "VACUUM;"
sudo -u ddos-c2 sqlite3 /opt/ddos-c2/ddos_lab.db "ANALYZE;"
sudo systemctl start ddos-c2

# Check database statistics
sudo -u ddos-c2 sqlite3 /opt/ddos-c2/ddos_lab.db "
SELECT name, COUNT(*) as row_count 
FROM sqlite_master 
WHERE type='table' 
GROUP BY name;
"

# Clean old records if database is too large
sudo -u ddos-c2 sqlite3 /opt/ddos-c2/ddos_lab.db "
DELETE FROM log_entries WHERE timestamp < datetime('now', '-7 days');
DELETE FROM attack_sessions WHERE start_time < datetime('now', '-30 days');
VACUUM;
"
```

## Section 7: Emergency Procedures

### Emergency Stop All Operations

```bash
# Create emergency stop script
cat > emergency_stop.sh << 'EOF'
#!/bin/bash

echo "EMERGENCY STOP - Stopping all DDoS operations immediately"
echo "========================================================="

# Stop current attacks
echo "1. Stopping current attacks..."
curl -X POST http://localhost:8080/api/emergency-stop

# Stop all bot services
echo "2. Stopping all bot services..."
for i in {101..128}; do
    echo "  Stopping bot on 192.168.1.$i"
    ssh root@192.168.1.$i "systemctl stop ddos-bot" &
done
wait

# Stop C2 server
echo "3. Stopping C2 server..."
sudo systemctl stop ddos-c2

# Check status
echo "4. Verifying shutdown..."
curl -s http://localhost:8080/health || echo "C2 server stopped"

echo "Emergency stop completed!"
EOF

chmod +x emergency_stop.sh
./emergency_stop.sh
```

### System Recovery

```bash
# Create recovery script
cat > recovery.sh << 'EOF'
#!/bin/bash

echo "System Recovery Procedure"
echo "========================"

# Start C2 server
echo "1. Starting C2 server..."
sudo systemctl start ddos-c2
sleep 5

# Check C2 server status
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✓ C2 server is running"
else
    echo "✗ C2 server failed to start"
    sudo systemctl status ddos-c2
    exit 1
fi

# Start all bot services
echo "2. Starting bot services..."
for i in {101..128}; do
    echo "  Starting bot on 192.168.1.$i"
    ssh root@192.168.1.$i "systemctl start ddos-bot" &
done
wait

# Wait for bots to connect
echo "3. Waiting for bot connections..."
sleep 30

# Check bot connections
BOT_COUNT=$(curl -s http://localhost:8080/api/bots | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data['bots']))
except:
    print(0)
")

echo "Connected bots: $BOT_COUNT/28"

if [ "$BOT_COUNT" -ge 20 ]; then
    echo "✓ Most bots connected successfully"
else
    echo "⚠ Only $BOT_COUNT bots connected, investigating..."
    
    # Check failed bots
    for i in {101..128}; do
        if ! ssh root@192.168.1.$i "systemctl is-active ddos-bot" > /dev/null 2>&1; then
            echo "  Bot on 192.168.1.$i is not running"
        fi
    done
fi

echo "Recovery procedure completed!"
EOF

chmod +x recovery.sh
```

### Complete System Reset

```bash
# Create complete reset script
cat > complete_reset.sh << 'EOF'
#!/bin/bash

echo "Complete System Reset"
echo "===================="

# Stop everything
./emergency_stop.sh

# Clean up logs
echo "Cleaning up logs..."
sudo systemctl stop rsyslog
sudo rm -f /var/log/ddos-lab/*.log
sudo systemctl start rsyslog

# Reset database
echo "Resetting database..."
sudo systemctl stop ddos-c2
sudo -u ddos-c2 rm -f /opt/ddos-c2/ddos_lab.db
sudo systemctl start ddos-c2

# Clear temporary files
echo "Clearing temporary files..."
rm -f c2_monitoring_*.log
rm -f target_monitoring_*.log
rm -f monitor_log.txt
rm -rf attack_stats_*
rm -rf log_analysis_*
rm -rf ddos_report_*

# Restart all services
echo "Restarting all services..."
./recovery.sh

echo "Complete system reset finished!"
EOF

chmod +x complete_reset.sh
```

## Section 8: Diagnostic Tools

### Create Diagnostic Script

```bash
# Create comprehensive diagnostic script
cat > diagnose_system.sh << 'EOF'
#!/bin/bash

echo "DDoS Simulation Lab - System Diagnostics"
echo "========================================"
echo "Timestamp: $(date)"
echo

# System Information
echo "=== SYSTEM INFORMATION ==="
echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')"
echo "Kernel: $(uname -r)"
echo "Uptime: $(uptime -p)"
echo

# C2 Server Status
echo "=== C2 SERVER STATUS ==="
if systemctl is-active ddos-c2 > /dev/null; then
    echo "✓ C2 service is running"
    
    if curl -s http://localhost:8080/health > /dev/null; then
        echo "✓ C2 HTTP endpoint responding"
    else
        echo "✗ C2 HTTP endpoint not responding"
    fi
    
    # Check WebSocket port
    if nc -z localhost 8081; then
        echo "✓ C2 WebSocket port open"
    else
        echo "✗ C2 WebSocket port not accessible"
    fi
    
    # Get C2 status
    curl -s http://localhost:8080/api/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Active bots: {data[\"active_bots\"]}/{data[\"max_bots\"]}')
    if data.get('current_attack'):
        print(f'Current attack: {data[\"current_attack\"][\"attack_type\"]}')
    else:
        print('No active attack')
except:
    print('Could not parse C2 status')
"
else
    echo "✗ C2 service is not running"
fi
echo

# Network Status
echo "=== NETWORK STATUS ==="
echo "IP Address: $(hostname -I | awk '{print $1}')"
echo "Default Gateway: $(ip route | grep default | awk '{print $3}')"

# Test connectivity
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo "✓ Internet connectivity"
else
    echo "✗ No internet connectivity"
fi

if ping -c 1 192.168.1.200 > /dev/null 2>&1; then
    echo "✓ Target reachable"
else
    echo "✗ Target not reachable"
fi
echo

# Resource Usage
echo "=== RESOURCE USAGE ==="
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')"
echo "Memory: $(free | grep Mem | awk '{printf "%.1f%% used", $3/$2 * 100.0}')"
echo "Disk: $(df / | tail -1 | awk '{print $5}') used"
echo

# Bot Status Summary
echo "=== BOT STATUS SUMMARY ==="
if curl -s http://localhost:8080/api/bots > /dev/null; then
    curl -s http://localhost:8080/api/bots | python3 -c "
import sys, json
from collections import Counter

try:
    data = json.load(sys.stdin)
    bots = data['bots']
    
    if not bots:
        print('No bots registered')
    else:
        statuses = [bot['status'] for bot in bots]
        status_count = Counter(statuses)
        
        print(f'Total bots: {len(bots)}')
        for status, count in status_count.items():
            print(f'  {status}: {count}')
        
        # Check for issues
        loads = [bot.get('current_load', 0) for bot in bots]
        high_load = [load for load in loads if load > 90]
        if high_load:
            print(f'⚠ {len(high_load)} bots with high load (>90%)')
except Exception as e:
    print(f'Error getting bot status: {e}')
"
else
    echo "Cannot connect to C2 server for bot status"
fi
echo

# Recent Errors
echo "=== RECENT ERRORS ==="
if curl -s http://localhost:8080/api/logs > /dev/null; then
    curl -s http://localhost:8080/api/logs?limit=50 | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    errors = [log for log in data['logs'] if log['level'] == 'ERROR']
    
    if not errors:
        print('No recent errors')
    else:
        print(f'Recent errors ({len(errors)}):')
        for error in errors[-5:]:
            print(f'  {error[\"timestamp\"][-8:]}: {error[\"message\"]}')
except:
    print('Could not retrieve error logs')
"
else
    echo "Cannot retrieve logs from C2 server"
fi
echo

echo "=== DIAGNOSTIC COMPLETE ==="
EOF

chmod +x diagnose_system.sh
```

## Usage Summary

### Quick Troubleshooting Checklist

```bash
# 1. Run system diagnostics
./diagnose_system.sh

# 2. Check specific component based on issue
# For C2 server issues:
sudo systemctl status ddos-c2 -l
sudo journalctl -u ddos-c2 -f

# For bot issues:
sudo systemctl status ddos-bot -l
sudo journalctl -u ddos-bot -f

# For network issues:
ping 192.168.1.100
telnet 192.168.1.100 8080

# 3. Emergency procedures if needed
./emergency_stop.sh
./recovery.sh

# 4. Complete reset if all else fails
./complete_reset.sh
```

## Important Notes

- Always check logs first for error messages
- Test network connectivity before assuming service issues
- Use emergency stop if systems become unresponsive
- Keep diagnostic outputs for analysis
- Document any recurring issues for future reference
- Consider system resources when troubleshooting performance issues