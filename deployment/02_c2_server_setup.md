# Phase 2: C2 Server Setup Commands (Linux)

This file contains all commands to set up the Command & Control server on your Linux machine.

## Prerequisites
- Linux server (Ubuntu/Debian/CentOS/RHEL)
- Root or sudo access
- Network connectivity to bot machines
- Project files copied from Windows machine

## Step 1: Initial Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y
# For CentOS/RHEL: sudo yum update -y

# Install required system packages
sudo apt install -y python3 python3-pip python3-venv git curl wget htop net-tools
# For CentOS/RHEL: sudo yum install -y python3 python3-pip python3-venv git curl wget htop net-tools

# Check Python version
python3 --version
```

## Step 2: Create C2 User and Directories

```bash
# Create dedicated user for C2 server
sudo useradd -r -s /bin/bash -d /opt/ddos-c2 -m ddos-c2

# Create necessary directories
sudo mkdir -p /opt/ddos-c2
sudo mkdir -p /var/log/ddos-lab
sudo mkdir -p /etc/ddos-lab

# Set permissions
sudo chown -R ddos-c2:ddos-c2 /opt/ddos-c2
sudo chown -R ddos-c2:ddos-c2 /var/log/ddos-lab
```

## Step 3: Copy Project Files

```bash
# Copy project files to C2 server directory
sudo cp -r /path/to/ddos-simulation-lab/* /opt/ddos-c2/

# Alternative: if copying from Windows via SCP
# scp -r user@windows-machine:/path/to/ddos-simulation-lab/* /opt/ddos-c2/

# Set ownership
sudo chown -R ddos-c2:ddos-c2 /opt/ddos-c2
```

## Step 4: Setup Python Environment

```bash
# Switch to C2 user
sudo su - ddos-c2

# Navigate to project directory
cd /opt/ddos-c2

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt

# Exit back to root user
exit
```

## Step 5: Configure C2 Server

```bash
# Create C2 server configuration
sudo tee /opt/ddos-c2/c2_config.json > /dev/null << 'EOF'
{
  "network": {
    "lab_network_cidr": "192.168.1.0/24",
    "c2_server_port": 8080,
    "websocket_port": 8081,
    "allowed_networks": [
      "192.168.1.0/24",
      "10.0.0.0/8",
      "172.16.0.0/12"
    ],
    "blocked_networks": [
      "127.0.0.0/8",
      "169.254.0.0/16",
      "224.0.0.0/4"
    ]
  },
  "safety": {
    "max_bots": 28,
    "max_requests_per_second_per_bot": 100,
    "max_attack_duration": 300,
    "emergency_stop_cpu": 95.0,
    "emergency_stop_memory": 95.0
  },
  "c2_server": {
    "host": "0.0.0.0",
    "port": 8080,
    "websocket_port": 8081,
    "log_level": "INFO",
    "log_file": "/var/log/ddos-lab/c2_server.log"
  },
  "database": {
    "database_url": "sqlite:////opt/ddos-c2/ddos_lab.db"
  }
}
EOF

# Set ownership
sudo chown ddos-c2:ddos-c2 /opt/ddos-c2/c2_config.json
```

## Step 6: Create Systemd Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/ddos-c2.service > /dev/null << 'EOF'
[Unit]
Description=DDoS Simulation Lab C2 Server
Documentation=https://github.com/your-repo/ddos-simulation-lab
After=network.target
Wants=network.target

[Service]
Type=simple
User=ddos-c2
Group=ddos-c2
WorkingDirectory=/opt/ddos-c2
Environment=PYTHONPATH=/opt/ddos-c2
Environment=CONFIG_FILE=/opt/ddos-c2/c2_config.json
ExecStart=/opt/ddos-c2/venv/bin/python -m c2_server.main
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ddos-c2

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/ddos-lab /opt/ddos-c2

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
```

## Step 7: Configure Firewall

```bash
# For UFW (Ubuntu/Debian)
sudo ufw allow 8080/tcp comment "DDoS Lab C2 HTTP"
sudo ufw allow 8081/tcp comment "DDoS Lab C2 WebSocket"
sudo ufw reload

# For Firewalld (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --reload

# For iptables (manual)
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8081 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

## Step 8: Start and Enable C2 Service

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable ddos-c2

# Start the service
sudo systemctl start ddos-c2

# Check service status
sudo systemctl status ddos-c2

# Check if service is listening on correct ports
sudo netstat -tlnp | grep -E ':(8080|8081)'
```

## Step 9: Test C2 Server

```bash
# Test HTTP endpoint
curl http://localhost:8080/health

# Test status endpoint
curl http://localhost:8080/api/status

# Check logs
sudo journalctl -u ddos-c2 -f

# Check log file
sudo tail -f /var/log/ddos-lab/c2_server.log
```

## Step 10: Create Management Scripts

```bash
# Create start script
sudo tee /opt/ddos-c2/start_c2.sh > /dev/null << 'EOF'
#!/bin/bash
sudo systemctl start ddos-c2
sudo systemctl status ddos-c2
EOF

# Create stop script
sudo tee /opt/ddos-c2/stop_c2.sh > /dev/null << 'EOF'
#!/bin/bash
sudo systemctl stop ddos-c2
sudo systemctl status ddos-c2
EOF

# Create status script
sudo tee /opt/ddos-c2/status_c2.sh > /dev/null << 'EOF'
#!/bin/bash
echo "=== Service Status ==="
sudo systemctl status ddos-c2 --no-pager

echo -e "\n=== Port Status ==="
sudo netstat -tlnp | grep -E ':(8080|8081)'

echo -e "\n=== Recent Logs ==="
sudo journalctl -u ddos-c2 --no-pager -n 10

echo -e "\n=== API Status ==="
curl -s http://localhost:8080/api/status | python3 -m json.tool
EOF

# Make scripts executable
sudo chmod +x /opt/ddos-c2/*.sh
sudo chown ddos-c2:ddos-c2 /opt/ddos-c2/*.sh
```

## Step 11: Setup Log Rotation

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/ddos-lab > /dev/null << 'EOF'
/var/log/ddos-lab/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ddos-c2 ddos-c2
    postrotate
        systemctl reload ddos-c2 > /dev/null 2>&1 || true
    endscript
}
EOF
```

## Verification Commands

```bash
# Check if C2 server is running
sudo systemctl is-active ddos-c2

# Check if ports are open
sudo ss -tlnp | grep -E ':(8080|8081)'

# Test API endpoints
curl http://localhost:8080/health
curl http://localhost:8080/api/status
curl http://localhost:8080/api/bots

# Monitor logs in real-time
sudo journalctl -u ddos-c2 -f
```

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status ddos-c2 -l

# Check logs
sudo journalctl -u ddos-c2 --no-pager -l

# Check configuration
sudo -u ddos-c2 /opt/ddos-c2/venv/bin/python -m c2_server.main --check-config
```

### Port Binding Issues
```bash
# Check what's using the ports
sudo lsof -i :8080
sudo lsof -i :8081

# Kill processes if needed
sudo pkill -f "c2_server"
```

### Permission Issues
```bash
# Fix ownership
sudo chown -R ddos-c2:ddos-c2 /opt/ddos-c2
sudo chown -R ddos-c2:ddos-c2 /var/log/ddos-lab

# Check SELinux (if applicable)
sudo setsebool -P httpd_can_network_connect 1
```

## Next Steps

After completing this phase:
1. Verify C2 server is accessible from bot machines
2. Note down the C2 server IP address
3. Proceed to Phase 3: Bot Deployment

## Important Notes

- The C2 server IP will be: `192.168.1.100` (or your configured IP)
- Web interface: `http://192.168.1.100:8080`
- WebSocket endpoint: `ws://192.168.1.100:8081`
- Logs location: `/var/log/ddos-lab/c2_server.log`