"""
Utility functions for the DDoS simulation lab.
"""
import socket
import psutil
import uuid
import logging
import ipaddress
from datetime import datetime
from typing import List, Optional, Dict, Any
from .config import NetworkConfig


def get_local_ip() -> str:
    """Get the local IP address of the machine."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_hostname() -> str:
    """Get the hostname of the machine."""
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def generate_bot_id() -> str:
    """Generate a unique bot ID."""
    hostname = get_hostname()
    unique_id = str(uuid.uuid4())[:8]
    return f"bot-{hostname}-{unique_id}"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"session-{timestamp}-{unique_id}"


def generate_attack_id() -> str:
    """Generate a unique attack ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"attack-{timestamp}-{unique_id}"


def get_system_metrics() -> Dict[str, Any]:
    """Get current system resource metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available": memory.available,
            "memory_total": memory.total,
            "disk_percent": (disk.used / disk.total) * 100,
            "disk_free": disk.free,
            "disk_total": disk.total,
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Error getting system metrics: {e}")
        return {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_available": 0,
            "memory_total": 0,
            "disk_percent": 0.0,
            "disk_free": 0,
            "disk_total": 0,
            "network_bytes_sent": 0,
            "network_bytes_recv": 0,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


def is_port_open(host: str, port: int, timeout: int = 5) -> bool:
    """Check if a port is open on a host."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def discover_c2_server(network_range: str, port: int = 8081) -> Optional[str]:
    """Discover C2 server on the network by scanning for open ports."""
    try:
        network = ipaddress.ip_network(network_range, strict=False)
        
        # Scan first 50 IPs in the network range
        for ip in list(network.hosts())[:50]:
            if is_port_open(str(ip), port, timeout=2):
                logging.info(f"Found potential C2 server at {ip}:{port}")
                return str(ip)
        
        return None
    except Exception as e:
        logging.error(f"Error discovering C2 server: {e}")
        return None


def validate_target_ip(target_ip: str, network_config: NetworkConfig) -> bool:
    """Validate that a target IP is allowed for attacks."""
    return network_config.is_ip_allowed(target_ip)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Set up logging configuration."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def calculate_exponential_backoff(attempt: int, base_delay: int = 1, max_delay: int = 60) -> int:
    """Calculate exponential backoff delay."""
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"


def get_network_interfaces() -> List[Dict[str, Any]]:
    """Get information about network interfaces."""
    interfaces = []
    try:
        for interface_name, addresses in psutil.net_if_addrs().items():
            interface_info = {
                "name": interface_name,
                "addresses": []
            }
            
            for addr in addresses:
                if addr.family == socket.AF_INET:  # IPv4
                    interface_info["addresses"].append({
                        "family": "IPv4",
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast
                    })
            
            if interface_info["addresses"]:  # Only include interfaces with IPv4 addresses
                interfaces.append(interface_info)
    
    except Exception as e:
        logging.error(f"Error getting network interfaces: {e}")
    
    return interfaces


def is_safe_to_attack(target_ip: str, target_port: int, network_config: NetworkConfig) -> tuple[bool, str]:
    """
    Check if it's safe to attack a target based on network configuration.
    Returns (is_safe, reason).
    """
    # Validate IP format
    try:
        ipaddress.ip_address(target_ip)
    except ValueError:
        return False, f"Invalid IP address format: {target_ip}"
    
    # Check if IP is in allowed networks
    if not network_config.is_ip_allowed(target_ip):
        return False, f"Target IP {target_ip} is not in allowed networks"
    
    # Check port range
    if not (1 <= target_port <= 65535):
        return False, f"Invalid port number: {target_port}"
    
    # Additional safety checks
    if target_ip == "127.0.0.1" or target_ip.startswith("127."):
        return False, "Cannot attack localhost"
    
    if target_ip.startswith("169.254."):
        return False, "Cannot attack link-local addresses"
    
    if target_ip.startswith("224.") or target_ip.startswith("239."):
        return False, "Cannot attack multicast addresses"
    
    return True, "Target is safe to attack"