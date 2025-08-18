# Phase 1: Windows Setup Commands

This file contains all commands to run on your Windows machine to prepare for the DDoS simulation lab deployment.

## Prerequisites
- Windows 10/11 or Windows Server
- Python 3.8+ installed
- Git installed
- Network access to Linux machines

## Step 1: Prepare Project Directory

```cmd
# Create project directory
mkdir C:\ddos-simulation-lab
cd C:\ddos-simulation-lab

# If you have the project files, copy them here
# Otherwise, create the directory structure manually
```

## Step 2: Install Python Dependencies

```cmd
# Navigate to project directory
cd C:\ddos-simulation-lab

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Configure Network Settings

```cmd
# Open config.json for editing
notepad config.json
```

**Edit the following settings in config.json:**

```json
{
  "network": {
    "lab_network_cidr": "192.168.1.0/24",
    "c2_server_port": 8080,
    "websocket_port": 8081,
    "allowed_networks": [
      "192.168.1.0/24"
    ]
  },
  "c2_server": {
    "host": "0.0.0.0",
    "port": 8080,
    "websocket_port": 8081
  }
}
```

## Step 4: Test Local Setup

```cmd
# Test C2 server locally (optional)
python -m c2_server.main

# In another terminal, test if server is running
curl http://localhost:8080/health
```

## Step 5: Prepare Files for Linux Deployment

```cmd
# Create deployment package
mkdir deployment_package
xcopy /E /I . deployment_package\ddos-simulation-lab

# Create compressed archive (if you have 7-zip or WinRAR)
# 7z a ddos-lab.zip deployment_package\*
```

## Step 6: Network Planning

**Document your network setup:**

```
C2 Server IP: 192.168.1.100
Bot IPs: 192.168.1.101 - 192.168.1.128
Windows Victim IP: 192.168.1.200
```

**Create a file with your IP addresses:**

```cmd
# Create IP list file
echo 192.168.1.101 > bot_ips.txt
echo 192.168.1.102 >> bot_ips.txt
echo 192.168.1.103 >> bot_ips.txt
# ... continue for all 28 bots
echo 192.168.1.128 >> bot_ips.txt
```

## Step 7: SSH Key Setup (if using SSH)

```cmd
# Generate SSH key pair (if not already done)
ssh-keygen -t rsa -b 4096 -f C:\Users\%USERNAME%\.ssh\ddos_lab_key

# Copy public key to clipboard
type C:\Users\%USERNAME%\.ssh\ddos_lab_key.pub
```

## Next Steps

After completing this phase:
1. Copy the project files to your Linux C2 server
2. Proceed to Phase 2: C2 Server Setup
3. Use the generated SSH keys for secure access to Linux machines

## Troubleshooting

### Python Issues
```cmd
# Check Python version
python --version

# Check pip version
pip --version

# List installed packages
pip list
```

### Network Issues
```cmd
# Test network connectivity
ping 192.168.1.100
ping 192.168.1.101
ping 192.168.1.200

# Check open ports
netstat -an | findstr :8080
netstat -an | findstr :8081
```

### File Permission Issues
```cmd
# Run as administrator if needed
# Right-click Command Prompt -> "Run as administrator"
```

## Files Created in This Phase
- `config.json` (configured for your network)
- `bot_ips.txt` (list of bot IP addresses)
- SSH keys (if generated)
- Virtual environment with dependencies