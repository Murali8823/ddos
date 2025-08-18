"""
Data models and interfaces for the DDoS simulation lab.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class BotStatus(str, Enum):
    CONNECTED = "connected"
    ATTACKING = "attacking"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class AttackType(str, Enum):
    HTTP_FLOOD = "http_flood"
    TCP_SYN = "tcp_syn"
    UDP_FLOOD = "udp_flood"


class BotClient(BaseModel):
    bot_id: str = Field(..., description="Unique identifier for the bot")
    ip_address: str = Field(..., description="IP address of the bot")
    hostname: str = Field(..., description="Hostname of the bot")
    connection_time: datetime = Field(..., description="When the bot connected")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")
    status: BotStatus = Field(default=BotStatus.CONNECTED, description="Current bot status")
    capabilities: List[AttackType] = Field(default_factory=list, description="Supported attack types")
    current_load: float = Field(default=0.0, description="Current CPU/resource load")


class SafetyConfig(BaseModel):
    max_requests_per_second: int = Field(default=100, description="Max RPS per bot")
    max_cpu_usage: float = Field(default=80.0, description="Max CPU usage percentage")
    max_memory_usage: float = Field(default=80.0, description="Max memory usage percentage")
    network_timeout: int = Field(default=5, description="Network timeout in seconds")
    emergency_stop_threshold: float = Field(default=95.0, description="Emergency stop CPU threshold")


class AttackConfig(BaseModel):
    attack_id: str = Field(..., description="Unique attack identifier")
    attack_type: AttackType = Field(..., description="Type of attack to perform")
    target_ip: str = Field(..., description="Target IP address")
    target_port: int = Field(..., description="Target port number")
    intensity: int = Field(..., description="Requests per second per bot")
    duration: int = Field(default=0, description="Attack duration in seconds, 0 for indefinite")
    safety_limits: SafetyConfig = Field(default_factory=SafetyConfig, description="Safety configuration")
    active_bots: List[str] = Field(default_factory=list, description="List of participating bot IDs")


class SessionMetrics(BaseModel):
    total_requests: int = Field(default=0, description="Total requests sent")
    requests_per_second: float = Field(default=0.0, description="Current RPS")
    bandwidth_usage: float = Field(default=0.0, description="Bandwidth usage in MB/s")
    active_bots: int = Field(default=0, description="Number of active bots")
    target_response_time: float = Field(default=0.0, description="Target response time in ms")
    success_rate: float = Field(default=0.0, description="Success rate percentage")


class LogEntry(BaseModel):
    timestamp: datetime = Field(..., description="Log entry timestamp")
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR)")
    source: str = Field(..., description="Source component (C2, BOT, TARGET)")
    message: str = Field(..., description="Log message")
    bot_id: Optional[str] = Field(None, description="Associated bot ID if applicable")
    attack_id: Optional[str] = Field(None, description="Associated attack ID if applicable")


class AttackSession(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    start_time: datetime = Field(..., description="Session start time")
    end_time: Optional[datetime] = Field(None, description="Session end time")
    attack_config: AttackConfig = Field(..., description="Attack configuration")
    participating_bots: List[BotClient] = Field(default_factory=list, description="Participating bots")
    metrics: SessionMetrics = Field(default_factory=SessionMetrics, description="Session metrics")
    logs: List[LogEntry] = Field(default_factory=list, description="Session logs")


class CommandMessage(BaseModel):
    command: str = Field(..., description="Command type")
    attack_config: Optional[AttackConfig] = Field(None, description="Attack configuration")
    timestamp: datetime = Field(default_factory=datetime.now, description="Command timestamp")
    target_bots: Optional[List[str]] = Field(None, description="Target bot IDs, None for all")


class HeartbeatMessage(BaseModel):
    bot_id: str = Field(..., description="Bot identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Heartbeat timestamp")
    status: BotStatus = Field(..., description="Current bot status")
    current_load: float = Field(..., description="Current system load")
    metrics: Optional[dict] = Field(None, description="Additional metrics")