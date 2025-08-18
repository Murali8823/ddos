# Phase 6: Monitoring and Analysis Commands

This file contains all commands for monitoring the DDoS simulation and analyzing results.

## Prerequisites
- All previous phases completed successfully
- Attacks have been executed
- Log data available for analysis
- Monitoring tools configured

## Step 1: Real-Time Monitoring Setup

### C2 Server Monitoring

```bash
# Create comprehensive C2 monitoring script
cat > monitor_c2_detailed.sh << 'EOF'
#!/bin/bash

LOG_FILE="c2_monitoring_$(date +%Y%m%d_%H%M%S).log"

echo "Starting detailed C2 server monitoring..."
echo "Log file: $LOG_FILE"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Get C2 status
    C2_STATUS=$(curl -s http://localhost:8080/api/status)
    
    # Get system metrics
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
    
    # Log to file
    echo "[$TIMESTAMP] CPU: ${CPU_USAGE}%, Memory: ${MEMORY_USAGE}%, Disk: ${DISK_USAGE}%" >> "$LOG_FILE"
    echo "[$TIMESTAMP] C2_STATUS: $C2_STATUS" >> "$LOG_FILE"
    
    # Display summary
    echo "[$TIMESTAMP] System: CPU ${CPU_USAGE}%, Mem ${MEMORY_USAGE}%, Disk ${DISK_USAGE}%"
    
    # Parse and display C2 info
    echo "$C2_STATUS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'  Bots: {data[\"active_bots\"]}/{data[\"max_bots\"]}')
    if data.get('current_attack'):
        attack = data['current_attack']
        print(f'  Attack: {attack[\"attack_type\"]} -> {attack[\"target_ip\"]}:{attack[\"target_port\"]}')
    else:
        print('  Attack: None')
except:
    print('  Error parsing C2 status')
"
    
    sleep 10
done
EOF

chmod +x monitor_c2_detailed.sh
```

### Bot Network Monitoring

```bash
# Create bot network monitoring script
cat > monitor_bot_network.sh << 'EOF'
#!/bin/bash

echo "Bot Network Monitoring Dashboard"
echo "==============================="

while true; do
    clear
    echo "Bot Network Status - $(date)"
    echo "=============================="
    
    # Get bot information
    BOTS_DATA=$(curl -s http://localhost:8080/api/bots)
    
    echo "$BOTS_DATA" | python3 -c "
import sys, json
from collections import Counter

try:
    data = json.load(sys.stdin)
    bots = data['bots']
    
    print(f'Total bots: {len(bots)}')
    
    # Status distribution
    statuses = [bot['status'] for bot in bots]
    status_count = Counter(statuses)
    
    print('\\nStatus Distribution:')
    for status, count in status_count.items():
        print(f'  {status}: {count}')
    
    # Load distribution
    if bots:
        loads = [bot.get('current_load', 0) for bot in bots]
        avg_load = sum(loads) / len(loads)
        max_load = max(loads)
        min_load = min(loads)
        
        print(f'\\nLoad Distribution:')
        print(f'  Average: {avg_load:.1f}%')
        print(f'  Maximum: {max_load:.1f}%')
        print(f'  Minimum: {min_load:.1f}%')
    
    # Show top 5 bots by load
    if bots:
        sorted_bots = sorted(bots, key=lambda x: x.get('current_load', 0), reverse=True)
        print('\\nTop 5 Bots by Load:')
        for i, bot in enumerate(sorted_bots[:5]):
            print(f'  {i+1}. {bot[\"bot_id\"]}: {bot.get(\"current_load\", 0):.1f}% ({bot[\"ip_address\"]})')

except Exception as e:
    print(f'Error: {e}')
"
    
    sleep 5
done
EOF

chmod +x monitor_bot_network.sh
```

### Target System Monitoring

```bash
# Create target monitoring script (run from C2 server)
cat > monitor_target_detailed.sh << 'EOF'
#!/bin/bash

TARGET_IP="192.168.1.200"
LOG_FILE="target_monitoring_$(date +%Y%m%d_%H%M%S).log"

echo "Starting detailed target monitoring for $TARGET_IP"
echo "Log file: $LOG_FILE"

# Function to test HTTP response
test_http_response() {
    local url="http://$TARGET_IP"
    local response_time=$(curl -o /dev/null -s -w "%{time_total}" "$url" 2>/dev/null)
    local http_code=$(curl -o /dev/null -s -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$http_code" = "200" ]; then
        echo "HTTP_OK:$response_time"
    else
        echo "HTTP_ERROR:$http_code"
    fi
}

# Function to test ping
test_ping() {
    local ping_result=$(ping -c 1 -W 2 "$TARGET_IP" 2>/dev/null | grep "time=" | cut -d'=' -f4 | cut -d' ' -f1)
    if [ -n "$ping_result" ]; then
        echo "PING_OK:$ping_result"
    else
        echo "PING_TIMEOUT"
    fi
}

# Function to test TCP connection
test_tcp_connection() {
    local port="$1"
    if timeout 2 bash -c "echo >/dev/tcp/$TARGET_IP/$port" 2>/dev/null; then
        echo "TCP_${port}_OK"
    else
        echo "TCP_${port}_FAILED"
    fi
}

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Test various aspects
    HTTP_RESULT=$(test_http_response)
    PING_RESULT=$(test_ping)
    TCP80_RESULT=$(test_tcp_connection 80)
    TCP443_RESULT=$(test_tcp_connection 443)
    
    # Log results
    echo "[$TIMESTAMP] $HTTP_RESULT $PING_RESULT $TCP80_RESULT $TCP443_RESULT" >> "$LOG_FILE"
    
    # Display results
    echo "[$TIMESTAMP] Target Status:"
    echo "  HTTP: $HTTP_RESULT"
    echo "  Ping: $PING_RESULT"
    echo "  TCP 80: $TCP80_RESULT"
    echo "  TCP 443: $TCP443_RESULT"
    echo
    
    sleep 5
done
EOF

chmod +x monitor_target_detailed.sh
```

## Step 2: Performance Analysis

### Attack Performance Analysis

```bash
# Create attack performance analyzer
cat > analyze_attack_performance.py << 'EOF'
#!/usr/bin/env python3
import json
import sys
from datetime import datetime
import statistics

def analyze_attack_performance(stats_dir):
    print("Attack Performance Analysis")
    print("=" * 40)
    
    # Load attack logs
    try:
        with open(f"{stats_dir}/attack_logs.json") as f:
            logs_data = json.load(f)
        logs = logs_data['logs']
    except FileNotFoundError:
        print("Error: attack_logs.json not found")
        return
    
    # Parse attack events
    attack_starts = []
    attack_stops = []
    
    for log in logs:
        if 'Attack started' in log['message']:
            attack_starts.append({
                'timestamp': log['timestamp'],
                'message': log['message'],
                'attack_id': log.get('attack_id', 'unknown')
            })
        elif 'Attack stopped' in log['message']:
            attack_stops.append({
                'timestamp': log['timestamp'],
                'message': log['message'],
                'attack_id': log.get('attack_id', 'unknown')
            })
    
    print(f"Total attacks initiated: {len(attack_starts)}")
    print(f"Total attacks completed: {len(attack_stops)}")
    
    # Analyze attack types
    attack_types = {}
    for attack in attack_starts:
        if 'http_flood' in attack['message']:
            attack_types['HTTP Flood'] = attack_types.get('HTTP Flood', 0) + 1
        elif 'tcp_syn' in attack['message']:
            attack_types['TCP SYN'] = attack_types.get('TCP SYN', 0) + 1
        elif 'udp_flood' in attack['message']:
            attack_types['UDP Flood'] = attack_types.get('UDP Flood', 0) + 1
    
    print("\nAttack Type Distribution:")
    for attack_type, count in attack_types.items():
        print(f"  {attack_type}: {count} attacks")
    
    # Analyze bot performance
    try:
        with open(f"{stats_dir}/bot_info.json") as f:
            bots_data = json.load(f)
        bots = bots_data['bots']
        
        if bots:
            loads = [bot.get('current_load', 0) for bot in bots]
            print(f"\nBot Performance Statistics:")
            print(f"  Total bots: {len(bots)}")
            print(f"  Average load: {statistics.mean(loads):.2f}%")
            print(f"  Median load: {statistics.median(loads):.2f}%")
            print(f"  Max load: {max(loads):.2f}%")
            print(f"  Min load: {min(loads):.2f}%")
            
            # Load distribution
            high_load_bots = [load for load in loads if load > 80]
            medium_load_bots = [load for load in loads if 50 <= load <= 80]
            low_load_bots = [load for load in loads if load < 50]
            
            print(f"\nLoad Distribution:")
            print(f"  High load (>80%): {len(high_load_bots)} bots")
            print(f"  Medium load (50-80%): {len(medium_load_bots)} bots")
            print(f"  Low load (<50%): {len(low_load_bots)} bots")
    
    except FileNotFoundError:
        print("Warning: bot_info.json not found")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 analyze_attack_performance.py <stats_directory>")
        sys.exit(1)
    
    analyze_attack_performance(sys.argv[1])
EOF

chmod +x analyze_attack_performance.py
```

### Network Impact Analysis

```bash
# Create network impact analyzer
cat > analyze_network_impact.py << 'EOF'
#!/usr/bin/env python3
import json
import re
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

def parse_monitoring_log(log_file):
    """Parse monitoring log file and extract metrics."""
    timestamps = []
    cpu_usage = []
    memory_usage = []
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Parse system metrics
                if 'CPU:' in line and 'Memory:' in line:
                    # Extract timestamp
                    timestamp_match = re.search(r'\[(.*?)\]', line)
                    if timestamp_match:
                        timestamps.append(timestamp_match.group(1))
                    
                    # Extract CPU usage
                    cpu_match = re.search(r'CPU: ([\d.]+)%', line)
                    if cpu_match:
                        cpu_usage.append(float(cpu_match.group(1)))
                    
                    # Extract memory usage
                    mem_match = re.search(r'Memory: ([\d.]+)%', line)
                    if mem_match:
                        memory_usage.append(float(mem_match.group(1)))
    
    except FileNotFoundError:
        print(f"Warning: {log_file} not found")
        return [], [], []
    
    return timestamps, cpu_usage, memory_usage

def analyze_target_response_log(log_file):
    """Analyze target response times."""
    response_times = []
    timestamps = []
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if 'HTTP_OK:' in line:
                    # Extract timestamp
                    timestamp_match = re.search(r'\[(.*?)\]', line)
                    if timestamp_match:
                        timestamps.append(timestamp_match.group(1))
                    
                    # Extract response time
                    response_match = re.search(r'HTTP_OK:([\d.]+)', line)
                    if response_match:
                        response_times.append(float(response_match.group(1)))
    
    except FileNotFoundError:
        print(f"Warning: {log_file} not found")
        return [], []
    
    return timestamps, response_times

def generate_impact_report():
    """Generate comprehensive network impact report."""
    print("Network Impact Analysis Report")
    print("=" * 50)
    
    # Find monitoring log files
    import glob
    c2_logs = glob.glob("c2_monitoring_*.log")
    target_logs = glob.glob("target_monitoring_*.log")
    
    if c2_logs:
        print(f"Analyzing C2 server logs: {len(c2_logs)} files")
        for log_file in c2_logs[-1:]:  # Analyze most recent
            print(f"\nC2 Server Analysis ({log_file}):")
            timestamps, cpu_usage, memory_usage = parse_monitoring_log(log_file)
            
            if cpu_usage:
                print(f"  Average CPU usage: {np.mean(cpu_usage):.2f}%")
                print(f"  Peak CPU usage: {max(cpu_usage):.2f}%")
                print(f"  CPU usage std dev: {np.std(cpu_usage):.2f}%")
            
            if memory_usage:
                print(f"  Average memory usage: {np.mean(memory_usage):.2f}%")
                print(f"  Peak memory usage: {max(memory_usage):.2f}%")
    
    if target_logs:
        print(f"\nAnalyzing target logs: {len(target_logs)} files")
        for log_file in target_logs[-1:]:  # Analyze most recent
            print(f"\nTarget Response Analysis ({log_file}):")
            timestamps, response_times = analyze_target_response_log(log_file)
            
            if response_times:
                print(f"  Average response time: {np.mean(response_times):.3f}s")
                print(f"  Slowest response: {max(response_times):.3f}s")
                print(f"  Fastest response: {min(response_times):.3f}s")
                print(f"  Response time std dev: {np.std(response_times):.3f}s")
                
                # Categorize response times
                fast_responses = [t for t in response_times if t < 0.1]
                slow_responses = [t for t in response_times if t > 1.0]
                
                print(f"  Fast responses (<0.1s): {len(fast_responses)}")
                print(f"  Slow responses (>1.0s): {len(slow_responses)}")

if __name__ == "__main__":
    generate_impact_report()
EOF

chmod +x analyze_network_impact.py
```

## Step 3: Log Analysis and Reporting

### Comprehensive Log Analysis

```bash
# Create comprehensive log analyzer
cat > analyze_logs_comprehensive.sh << 'EOF'
#!/bin/bash

echo "Comprehensive Log Analysis"
echo "========================="

# Create analysis directory
ANALYSIS_DIR="log_analysis_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ANALYSIS_DIR"

echo "Analysis directory: $ANALYSIS_DIR"

# Collect all logs
echo "Collecting logs..."
curl -s http://localhost:8080/api/logs?limit=5000 > "$ANALYSIS_DIR/all_logs.json"

# Analyze attack patterns
echo "Analyzing attack patterns..."
python3 << 'PYTHON' > "$ANALYSIS_DIR/attack_patterns.txt"
import json
from collections import defaultdict, Counter
from datetime import datetime

# Load logs
with open("$ANALYSIS_DIR/all_logs.json") as f:
    data = json.load(f)

logs = data['logs']

print("Attack Pattern Analysis")
print("=" * 30)

# Count events by type
event_types = Counter()
attack_events = []

for log in logs:
    message = log['message']
    
    if 'Attack started' in message:
        event_types['Attack Started'] += 1
        attack_events.append(('start', log))
    elif 'Attack stopped' in message:
        event_types['Attack Stopped'] += 1
        attack_events.append(('stop', log))
    elif 'Bot' in message and 'connected' in message:
        event_types['Bot Connected'] += 1
    elif 'Bot' in message and 'disconnected' in message:
        event_types['Bot Disconnected'] += 1
    elif 'Emergency stop' in message:
        event_types['Emergency Stop'] += 1

print("Event Summary:")
for event_type, count in event_types.most_common():
    print(f"  {event_type}: {count}")

# Analyze attack types
attack_types = Counter()
for event_type, log in attack_events:
    if event_type == 'start':
        message = log['message']
        if 'http_flood' in message:
            attack_types['HTTP Flood'] += 1
        elif 'tcp_syn' in message:
            attack_types['TCP SYN'] += 1
        elif 'udp_flood' in message:
            attack_types['UDP Flood'] += 1

print("\nAttack Type Distribution:")
for attack_type, count in attack_types.most_common():
    print(f"  {attack_type}: {count}")

# Analyze timing patterns
print("\nTiming Analysis:")
if len(attack_events) >= 2:
    start_times = [log['timestamp'] for event_type, log in attack_events if event_type == 'start']
    if len(start_times) >= 2:
        print(f"  First attack: {start_times[0]}")
        print(f"  Last attack: {start_times[-1]}")
        print(f"  Total attacks: {len(start_times)}")

PYTHON

# Analyze error patterns
echo "Analyzing error patterns..."
python3 << 'PYTHON' > "$ANALYSIS_DIR/error_analysis.txt"
import json
from collections import Counter

# Load logs
with open("$ANALYSIS_DIR/all_logs.json") as f:
    data = json.load(f)

logs = data['logs']

print("Error Analysis")
print("=" * 20)

# Find error logs
error_logs = [log for log in logs if log['level'] == 'ERROR']
warning_logs = [log for log in logs if log['level'] == 'WARNING']

print(f"Total errors: {len(error_logs)}")
print(f"Total warnings: {len(warning_logs)}")

if error_logs:
    print("\nRecent Errors:")
    for log in error_logs[-5:]:
        print(f"  {log['timestamp']}: {log['message']}")

if warning_logs:
    print("\nRecent Warnings:")
    for log in warning_logs[-5:]:
        print(f"  {log['timestamp']}: {log['message']}")

# Analyze error sources
error_sources = Counter(log['source'] for log in error_logs)
print("\nError Sources:")
for source, count in error_sources.most_common():
    print(f"  {source}: {count}")

PYTHON

# Generate summary report
echo "Generating summary report..."
cat > "$ANALYSIS_DIR/summary_report.txt" << 'SUMMARY'
DDoS Simulation Lab - Analysis Summary
=====================================

Analysis Date: $(date)
Analysis Directory: $ANALYSIS_DIR

This analysis includes:
1. Attack pattern analysis
2. Error and warning analysis
3. Bot performance metrics
4. Network impact assessment

Key Files:
- attack_patterns.txt: Attack execution patterns
- error_analysis.txt: Error and warning analysis
- all_logs.json: Complete log data

Recommendations:
- Review error patterns for system improvements
- Analyze attack effectiveness metrics
- Monitor bot performance distribution
- Assess network impact on target systems

SUMMARY

echo "Analysis completed in: $ANALYSIS_DIR"
ls -la "$ANALYSIS_DIR"
EOF

chmod +x analyze_logs_comprehensive.sh
```

### Generate Educational Report

```bash
# Create educational report generator
cat > generate_educational_report.py << 'EOF'
#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from collections import Counter

def generate_educational_report(stats_dir):
    """Generate educational report for DDoS simulation."""
    
    print("DDoS Simulation Lab - Educational Report")
    print("=" * 50)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load data
    try:
        with open(f"{stats_dir}/attack_logs.json") as f:
            logs_data = json.load(f)
        
        with open(f"{stats_dir}/bot_info.json") as f:
            bots_data = json.load(f)
        
        with open(f"{stats_dir}/c2_status.json") as f:
            status_data = json.load(f)
    
    except FileNotFoundError as e:
        print(f"Error: Required file not found - {e}")
        return
    
    logs = logs_data['logs']
    bots = bots_data['bots']
    
    # Section 1: Lab Setup Summary
    print("1. LAB SETUP SUMMARY")
    print("-" * 20)
    print(f"C2 Server: {status_data['server_ip']}:{status_data['server_port']}")
    print(f"Total Bots Deployed: {len(bots)}")
    print(f"Target System: Windows machine")
    print()
    
    # Section 2: Attack Execution Summary
    print("2. ATTACK EXECUTION SUMMARY")
    print("-" * 30)
    
    attack_starts = [log for log in logs if 'Attack started' in log['message']]
    attack_stops = [log for log in logs if 'Attack stopped' in log['message']]
    
    print(f"Total Attacks Executed: {len(attack_starts)}")
    print(f"Successfully Completed: {len(attack_stops)}")
    
    # Attack type breakdown
    attack_types = Counter()
    for attack in attack_starts:
        if 'http_flood' in attack['message']:
            attack_types['HTTP Flood'] += 1
        elif 'tcp_syn' in attack['message']:
            attack_types['TCP SYN Flood'] += 1
        elif 'udp_flood' in attack['message']:
            attack_types['UDP Flood'] += 1
    
    print("\nAttack Types Demonstrated:")
    for attack_type, count in attack_types.items():
        print(f"  - {attack_type}: {count} attacks")
    print()
    
    # Section 3: Bot Network Performance
    print("3. BOT NETWORK PERFORMANCE")
    print("-" * 28)
    
    if bots:
        connected_bots = [bot for bot in bots if bot['status'] == 'connected']
        attacking_bots = [bot for bot in bots if bot['status'] == 'attacking']
        
        print(f"Connected Bots: {len(connected_bots)}")
        print(f"Bots in Attack Mode: {len(attacking_bots)}")
        
        # Load analysis
        loads = [bot.get('current_load', 0) for bot in bots]
        if loads:
            avg_load = sum(loads) / len(loads)
            print(f"Average Bot Load: {avg_load:.1f}%")
            
            high_load_count = len([load for load in loads if load > 80])
            print(f"High Load Bots (>80%): {high_load_count}")
    print()
    
    # Section 4: Educational Objectives Met
    print("4. EDUCATIONAL OBJECTIVES")
    print("-" * 25)
    
    objectives_met = []
    
    if len(attack_types) >= 2:
        objectives_met.append("✓ Demonstrated multiple attack types")
    
    if len(bots) >= 20:
        objectives_met.append("✓ Showed distributed attack coordination")
    
    if len(attack_starts) >= 3:
        objectives_met.append("✓ Executed multiple attack scenarios")
    
    emergency_stops = [log for log in logs if 'Emergency stop' in log['message']]
    if emergency_stops:
        objectives_met.append("✓ Demonstrated emergency stop procedures")
    
    for objective in objectives_met:
        print(f"  {objective}")
    print()
    
    # Section 5: Key Learning Points
    print("5. KEY LEARNING POINTS")
    print("-" * 22)
    
    learning_points = [
        "• DDoS attacks use multiple distributed sources",
        "• Different attack types have different impacts",
        "• Coordination is key to effective DDoS attacks",
        "• Monitoring and detection are crucial for defense",
        "• Emergency response procedures are essential"
    ]
    
    for point in learning_points:
        print(f"  {point}")
    print()
    
    # Section 6: Technical Observations
    print("6. TECHNICAL OBSERVATIONS")
    print("-" * 25)
    
    if attack_types.get('HTTP Flood', 0) > 0:
        print("  • HTTP floods target application layer resources")
    
    if attack_types.get('TCP SYN Flood', 0) > 0:
        print("  • SYN floods exploit TCP connection establishment")
    
    if attack_types.get('UDP Flood', 0) > 0:
        print("  • UDP floods consume network bandwidth")
    
    print("  • Bot coordination requires reliable C2 communication")
    print("  • Attack effectiveness depends on target capacity")
    print()
    
    # Section 7: Recommendations for Further Study
    print("7. RECOMMENDATIONS FOR FURTHER STUDY")
    print("-" * 38)
    
    recommendations = [
        "• Study DDoS mitigation techniques (rate limiting, filtering)",
        "• Explore network monitoring and intrusion detection",
        "• Research botnet detection and takedown methods",
        "• Investigate cloud-based DDoS protection services",
        "• Analyze real-world DDoS attack case studies"
    ]
    
    for rec in recommendations:
        print(f"  {rec}")
    print()
    
    print("=" * 50)
    print("End of Educational Report")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 generate_educational_report.py <stats_directory>")
        sys.exit(1)
    
    generate_educational_report(sys.argv[1])
EOF

chmod +x generate_educational_report.py
```

## Step 4: Data Visualization

### Create Performance Graphs

```bash
# Install required packages for visualization
pip3 install matplotlib numpy pandas

# Create visualization script
cat > create_visualizations.py << 'EOF'
#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
import json
import re
from datetime import datetime
import pandas as pd

def create_attack_timeline(stats_dir):
    """Create attack timeline visualization."""
    try:
        with open(f"{stats_dir}/attack_logs.json") as f:
            logs_data = json.load(f)
        
        logs = logs_data['logs']
        
        # Extract attack events
        attack_events = []
        for log in logs:
            if 'Attack started' in log['message']:
                attack_type = 'Unknown'
                if 'http_flood' in log['message']:
                    attack_type = 'HTTP Flood'
                elif 'tcp_syn' in log['message']:
                    attack_type = 'TCP SYN'
                elif 'udp_flood' in log['message']:
                    attack_type = 'UDP Flood'
                
                attack_events.append({
                    'timestamp': log['timestamp'],
                    'type': attack_type,
                    'event': 'start'
                })
            elif 'Attack stopped' in log['message']:
                attack_events.append({
                    'timestamp': log['timestamp'],
                    'type': 'Stop',
                    'event': 'stop'
                })
        
        if not attack_events:
            print("No attack events found for timeline")
            return
        
        # Create timeline plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = {'HTTP Flood': 'red', 'TCP SYN': 'blue', 'UDP Flood': 'green', 'Stop': 'gray'}
        
        for i, event in enumerate(attack_events):
            color = colors.get(event['type'], 'black')
            ax.scatter(i, 1, c=color, s=100, alpha=0.7)
            ax.annotate(f"{event['type']}\n{event['timestamp'][-8:]}", 
                       (i, 1), textcoords="offset points", 
                       xytext=(0,10), ha='center', fontsize=8)
        
        ax.set_xlabel('Attack Sequence')
        ax.set_ylabel('Timeline')
        ax.set_title('DDoS Attack Timeline')
        ax.set_ylim(0.5, 1.5)
        ax.grid(True, alpha=0.3)
        
        # Create legend
        legend_elements = [plt.scatter([], [], c=color, s=100, label=attack_type) 
                          for attack_type, color in colors.items()]
        ax.legend(handles=legend_elements)
        
        plt.tight_layout()
        plt.savefig(f"{stats_dir}/attack_timeline.png", dpi=300, bbox_inches='tight')
        print(f"Attack timeline saved: {stats_dir}/attack_timeline.png")
        
    except Exception as e:
        print(f"Error creating attack timeline: {e}")

def create_bot_performance_chart(stats_dir):
    """Create bot performance visualization."""
    try:
        with open(f"{stats_dir}/bot_info.json") as f:
            bots_data = json.load(f)
        
        bots = bots_data['bots']
        
        if not bots:
            print("No bot data found for performance chart")
            return
        
        # Extract bot performance data
        bot_ids = [bot['bot_id'][-8:] for bot in bots]  # Last 8 chars of ID
        loads = [bot.get('current_load', 0) for bot in bots]
        
        # Create performance chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Individual bot loads
        bars = ax1.bar(range(len(bot_ids)), loads, alpha=0.7)
        ax1.set_xlabel('Bot ID')
        ax1.set_ylabel('CPU Load (%)')
        ax1.set_title('Individual Bot Performance')
        ax1.set_xticks(range(len(bot_ids)))
        ax1.set_xticklabels(bot_ids, rotation=45, ha='right')
        ax1.grid(True, alpha=0.3)
        
        # Color bars based on load level
        for bar, load in zip(bars, loads):
            if load > 80:
                bar.set_color('red')
            elif load > 50:
                bar.set_color('orange')
            else:
                bar.set_color('green')
        
        # Load distribution histogram
        ax2.hist(loads, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.set_xlabel('CPU Load (%)')
        ax2.set_ylabel('Number of Bots')
        ax2.set_title('Bot Load Distribution')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{stats_dir}/bot_performance.png", dpi=300, bbox_inches='tight')
        print(f"Bot performance chart saved: {stats_dir}/bot_performance.png")
        
    except Exception as e:
        print(f"Error creating bot performance chart: {e}")

def create_attack_summary_chart(stats_dir):
    """Create attack summary visualization."""
    try:
        with open(f"{stats_dir}/attack_logs.json") as f:
            logs_data = json.load(f)
        
        logs = logs_data['logs']
        
        # Count attack types
        attack_types = {'HTTP Flood': 0, 'TCP SYN': 0, 'UDP Flood': 0}
        
        for log in logs:
            if 'Attack started' in log['message']:
                if 'http_flood' in log['message']:
                    attack_types['HTTP Flood'] += 1
                elif 'tcp_syn' in log['message']:
                    attack_types['TCP SYN'] += 1
                elif 'udp_flood' in log['message']:
                    attack_types['UDP Flood'] += 1
        
        # Create pie chart
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Filter out zero values
        filtered_types = {k: v for k, v in attack_types.items() if v > 0}
        
        if filtered_types:
            colors = ['#ff9999', '#66b3ff', '#99ff99']
            wedges, texts, autotexts = ax.pie(filtered_types.values(), 
                                            labels=filtered_types.keys(),
                                            colors=colors[:len(filtered_types)],
                                            autopct='%1.1f%%',
                                            startangle=90)
            
            ax.set_title('Attack Type Distribution', fontsize=16, fontweight='bold')
            
            plt.savefig(f"{stats_dir}/attack_summary.png", dpi=300, bbox_inches='tight')
            print(f"Attack summary chart saved: {stats_dir}/attack_summary.png")
        else:
            print("No attack data found for summary chart")
        
    except Exception as e:
        print(f"Error creating attack summary chart: {e}")

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python3 create_visualizations.py <stats_directory>")
        sys.exit(1)
    
    stats_dir = sys.argv[1]
    
    print("Creating visualizations...")
    create_attack_timeline(stats_dir)
    create_bot_performance_chart(stats_dir)
    create_attack_summary_chart(stats_dir)
    print("Visualization creation completed!")

if __name__ == "__main__":
    main()
EOF

chmod +x create_visualizations.py
```

## Step 5: Automated Reporting

### Create Automated Report Generator

```bash
# Create automated report generator
cat > generate_full_report.sh << 'EOF'
#!/bin/bash

echo "Generating Full DDoS Simulation Report"
echo "====================================="

# Create report directory
REPORT_DIR="ddos_report_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

echo "Report directory: $REPORT_DIR"

# Step 1: Collect current statistics
echo "Step 1: Collecting current statistics..."
./collect_stats.sh
LATEST_STATS=$(ls -td attack_stats_* | head -1)
cp -r "$LATEST_STATS"/* "$REPORT_DIR/"

# Step 2: Run comprehensive log analysis
echo "Step 2: Running log analysis..."
./analyze_logs_comprehensive.sh
LATEST_ANALYSIS=$(ls -td log_analysis_* | head -1)
cp -r "$LATEST_ANALYSIS"/* "$REPORT_DIR/"

# Step 3: Generate performance analysis
echo "Step 3: Generating performance analysis..."
python3 analyze_attack_performance.py "$REPORT_DIR" > "$REPORT_DIR/performance_analysis.txt"

# Step 4: Generate network impact analysis
echo "Step 4: Analyzing network impact..."
python3 analyze_network_impact.py > "$REPORT_DIR/network_impact.txt"

# Step 5: Generate educational report
echo "Step 5: Creating educational report..."
python3 generate_educational_report.py "$REPORT_DIR" > "$REPORT_DIR/educational_report.txt"

# Step 6: Create visualizations
echo "Step 6: Creating visualizations..."
python3 create_visualizations.py "$REPORT_DIR"

# Step 7: Generate HTML report
echo "Step 7: Generating HTML report..."
cat > "$REPORT_DIR/index.html" << 'HTML'
<!DOCTYPE html>
<html>
<head>
    <title>DDoS Simulation Lab Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; border-bottom: 2px solid #333; }
        h2 { color: #666; border-bottom: 1px solid #ccc; }
        .section { margin: 20px 0; }
        .chart { text-align: center; margin: 20px 0; }
        .chart img { max-width: 100%; height: auto; }
        pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .summary { background: #e8f4fd; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>DDoS Simulation Lab Report</h1>
    <div class="summary">
        <h2>Report Summary</h2>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Lab Setup:</strong> 28 Linux Bots + 1 Linux C2 + 1 Windows Target</p>
        <p><strong>Report Directory:</strong> $REPORT_DIR</p>
    </div>

    <div class="section">
        <h2>Attack Timeline</h2>
        <div class="chart">
            <img src="attack_timeline.png" alt="Attack Timeline">
        </div>
    </div>

    <div class="section">
        <h2>Bot Performance</h2>
        <div class="chart">
            <img src="bot_performance.png" alt="Bot Performance">
        </div>
    </div>

    <div class="section">
        <h2>Attack Distribution</h2>
        <div class="chart">
            <img src="attack_summary.png" alt="Attack Summary">
        </div>
    </div>

    <div class="section">
        <h2>Educational Report</h2>
        <pre>$(cat educational_report.txt)</pre>
    </div>

    <div class="section">
        <h2>Performance Analysis</h2>
        <pre>$(cat performance_analysis.txt)</pre>
    </div>

    <div class="section">
        <h2>Network Impact Analysis</h2>
        <pre>$(cat network_impact.txt)</pre>
    </div>

    <div class="section">
        <h2>Files in This Report</h2>
        <ul>
$(for file in $(ls "$REPORT_DIR"); do echo "            <li>$file</li>"; done)
        </ul>
    </div>
</body>
</html>
HTML

# Step 8: Create summary
echo "Step 8: Creating final summary..."
cat > "$REPORT_DIR/README.txt" << 'README'
DDoS Simulation Lab - Complete Report
====================================

This directory contains a comprehensive analysis of the DDoS simulation lab session.

Key Files:
- index.html: Complete HTML report with visualizations
- educational_report.txt: Educational summary and learning outcomes
- performance_analysis.txt: Bot and attack performance analysis
- network_impact.txt: Network impact assessment
- attack_timeline.png: Visual timeline of attacks
- bot_performance.png: Bot performance charts
- attack_summary.png: Attack type distribution
- c2_status.json: C2 server status snapshot
- bot_info.json: Bot network information
- attack_logs.json: Complete attack logs
- all_logs.json: All system logs

Usage:
- Open index.html in a web browser for the complete report
- Review educational_report.txt for learning outcomes
- Analyze performance_analysis.txt for technical insights

Generated: $(date)
README

echo
echo "=========================================="
echo "Full report generation completed!"
echo "Report directory: $REPORT_DIR"
echo "Open $REPORT_DIR/index.html in a browser"
echo "=========================================="

# Show report contents
ls -la "$REPORT_DIR"
EOF

chmod +x generate_full_report.sh
```

## Step 6: Cleanup and Archival

### Create Cleanup Script

```bash
# Create cleanup script
cat > cleanup_lab.sh << 'EOF'
#!/bin/bash

echo "DDoS Simulation Lab Cleanup"
echo "=========================="

# Stop all attacks
echo "Stopping all attacks..."
curl -X POST http://localhost:8080/api/emergency-stop

# Wait for cleanup
sleep 5

# Archive logs before cleanup
ARCHIVE_DIR="lab_archive_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHIVE_DIR"

echo "Archiving logs to: $ARCHIVE_DIR"

# Archive C2 logs
sudo cp /var/log/ddos-lab/c2_server.log "$ARCHIVE_DIR/" 2>/dev/null || echo "C2 logs not found"

# Archive monitoring logs
cp c2_monitoring_*.log "$ARCHIVE_DIR/" 2>/dev/null || echo "No C2 monitoring logs"
cp target_monitoring_*.log "$ARCHIVE_DIR/" 2>/dev/null || echo "No target monitoring logs"

# Archive analysis results
cp -r attack_stats_* "$ARCHIVE_DIR/" 2>/dev/null || echo "No attack stats"
cp -r log_analysis_* "$ARCHIVE_DIR/" 2>/dev/null || echo "No log analysis"
cp -r ddos_report_* "$ARCHIVE_DIR/" 2>/dev/null || echo "No reports"

# Clean up temporary files
echo "Cleaning up temporary files..."
rm -f c2_monitoring_*.log
rm -f target_monitoring_*.log
rm -f monitor_log.txt

# Reset bot status (optional)
echo "Resetting bot status..."
curl -s http://localhost:8080/api/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Final status: {data[\"active_bots\"]} bots connected, no active attacks')
except:
    print('Could not get final status')
"

echo "Cleanup completed!"
echo "Archived files in: $ARCHIVE_DIR"
ls -la "$ARCHIVE_DIR"
EOF

chmod +x cleanup_lab.sh
```

## Usage Summary

### Run Complete Monitoring and Analysis

```bash
# 1. Start monitoring (in separate terminals)
./monitor_c2_detailed.sh &
./monitor_bot_network.sh &
./monitor_target_detailed.sh &

# 2. Execute attacks (from Phase 5)
# ... run your attack scenarios ...

# 3. Generate comprehensive report
./generate_full_report.sh

# 4. Clean up and archive
./cleanup_lab.sh
```

## Next Steps

After completing this phase:
1. Review generated reports and visualizations
2. Document lessons learned
3. Archive important data
4. Prepare for next simulation session

## Important Notes

- Monitor system resources during analysis
- Keep reports for educational reference
- Archive logs before cleanup
- Review visualizations for insights
- Document any anomalies or interesting findings