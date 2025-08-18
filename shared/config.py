"""
Configuration management for the DDoS simulation lab.
"""
import os
import ipaddress
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class NetworkConfig(BaseModel):
    """Network configuration and safety settings."""
    
    # Lab network configuration
    lab_network_cidr: str = Field(default="192.168.1.0/24", description="Lab network CIDR")
    c2_server_port: int = Field(default=8080, description="C2 server port")
    websocket_port: int = Field(default=8081, description="WebSocket port")
    
    # Safety network boundaries
    allowed_networks: List[str] = Field(
        default=["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"],
        description="Allowed network ranges for operations"
    )
    
    # Blocked networks (never attack these)
    blocked_networks: List[str] = Field(
        default=["127.0.0.0/8", "169.254.0.0/16", "224.0.0.0/4"],
        description="Blocked network ranges"
    )
    
    @validator('lab_network_cidr', 'allowed_networks', 'blocked_networks')
    def validate_network_ranges(cls, v):
        """Validate network CIDR ranges."""
        if isinstance(v, str):
            try:
                ipaddress.ip_network(v, strict=False)
                return v
            except ValueError:
                raise ValueError(f"Invalid network CIDR: {v}")
        elif isinstance(v, list):
            for network in v:
                try:
                    ipaddress.ip_network(network, strict=False)
                except ValueError:
                    raise ValueError(f"Invalid network CIDR in list: {network}")
            return v
        return v
    
    def is_ip_allowed(self, ip: str) -> bool:
        """Check if an IP address is within allowed networks."""
        try:
            target_ip = ipaddress.ip_address(ip)
            
            # Check if IP is in blocked networks
            for blocked in self.blocked_networks:
                if target_ip in ipaddress.ip_network(blocked, strict=False):
                    return False
            
            # Check if IP is in allowed networks
            for allowed in self.allowed_networks:
                if target_ip in ipaddress.ip_network(allowed, strict=False):
                    return True
            
            return False
        except ValueError:
            return False


class SafetyConfig(BaseModel):
    """Safety limits and thresholds."""
    
    # Resource limits
    max_cpu_usage: float = Field(default=80.0, description="Max CPU usage percentage")
    max_memory_usage: float = Field(default=80.0, description="Max memory usage percentage")
    max_network_usage: float = Field(default=80.0, description="Max network usage percentage")
    
    # Attack limits
    max_requests_per_second_per_bot: int = Field(default=100, description="Max RPS per bot")
    max_total_requests_per_second: int = Field(default=2800, description="Max total RPS (28 bots * 100)")
    max_attack_duration: int = Field(default=300, description="Max attack duration in seconds")
    
    # Emergency thresholds
    emergency_stop_cpu: float = Field(default=95.0, description="Emergency stop CPU threshold")
    emergency_stop_memory: float = Field(default=95.0, description="Emergency stop memory threshold")
    
    # Connection limits
    max_bots: int = Field(default=28, description="Maximum number of bots")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    heartbeat_interval: int = Field(default=10, description="Heartbeat interval in seconds")
    heartbeat_timeout: int = Field(default=30, description="Heartbeat timeout in seconds")


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    database_url: str = Field(default="sqlite:///ddos_lab.db", description="Database URL")
    log_retention_days: int = Field(default=30, description="Log retention in days")
    session_retention_days: int = Field(default=90, description="Session retention in days")


class C2ServerConfig(BaseModel):
    """C2 Server configuration."""
    
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")
    websocket_port: int = Field(default=8081, description="WebSocket port")
    
    # Dashboard settings
    dashboard_enabled: bool = Field(default=True, description="Enable web dashboard")
    dashboard_auth: bool = Field(default=False, description="Enable dashboard authentication")
    dashboard_username: str = Field(default="admin", description="Dashboard username")
    dashboard_password: str = Field(default="admin", description="Dashboard password")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="c2_server.log", description="Log file path")


class BotClientConfig(BaseModel):
    """Bot client configuration."""
    
    c2_server_host: Optional[str] = Field(None, description="C2 server host (auto-discover if None)")
    c2_server_port: int = Field(default=8081, description="C2 server WebSocket port")
    
    # Connection settings
    reconnect_interval: int = Field(default=5, description="Reconnection interval in seconds")
    max_reconnect_attempts: int = Field(default=10, description="Max reconnection attempts")
    heartbeat_interval: int = Field(default=10, description="Heartbeat interval in seconds")
    
    # Bot identification
    bot_id: Optional[str] = Field(None, description="Bot ID (auto-generate if None)")
    hostname: Optional[str] = Field(None, description="Hostname (auto-detect if None)")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="bot_client.log", description="Log file path")


class LabConfig(BaseModel):
    """Main lab configuration combining all components."""
    
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    c2_server: C2ServerConfig = Field(default_factory=C2ServerConfig)
    bot_client: BotClientConfig = Field(default_factory=BotClientConfig)
    
    @classmethod
    def load_from_env(cls) -> 'LabConfig':
        """Load configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        if os.getenv('LAB_NETWORK_CIDR'):
            config.network.lab_network_cidr = os.getenv('LAB_NETWORK_CIDR')
        
        if os.getenv('C2_SERVER_HOST'):
            config.c2_server.host = os.getenv('C2_SERVER_HOST')
        
        if os.getenv('C2_SERVER_PORT'):
            config.c2_server.port = int(os.getenv('C2_SERVER_PORT'))
        
        if os.getenv('WEBSOCKET_PORT'):
            config.c2_server.websocket_port = int(os.getenv('WEBSOCKET_PORT'))
            config.bot_client.c2_server_port = int(os.getenv('WEBSOCKET_PORT'))
        
        if os.getenv('MAX_BOTS'):
            config.safety.max_bots = int(os.getenv('MAX_BOTS'))
        
        if os.getenv('LOG_LEVEL'):
            config.c2_server.log_level = os.getenv('LOG_LEVEL')
            config.bot_client.log_level = os.getenv('LOG_LEVEL')
        
        return config
    
    def save_to_file(self, filepath: str):
        """Save configuration to JSON file."""
        with open(filepath, 'w') as f:
            f.write(self.json(indent=2))
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'LabConfig':
        """Load configuration from JSON file."""
        with open(filepath, 'r') as f:
            return cls.parse_raw(f.read())