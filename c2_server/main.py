"""
Main C2 server application with FastAPI and WebSocket support.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from shared.config import LabConfig
from shared.models import (
    BotClient, AttackConfig, CommandMessage, HeartbeatMessage, 
    LogEntry, AttackSession, SessionMetrics, BotStatus, AttackType
)
from shared.utils import setup_logging, generate_session_id, generate_attack_id, get_local_ip
from .database import DatabaseManager
from .bot_manager import BotManager
from .command_handler import CommandDistributor


class C2Server:
    """Main C2 server class."""
    
    def __init__(self, config: LabConfig):
        self.config = config
        self.logger = setup_logging(
            config.c2_server.log_level,
            config.c2_server.log_file
        )
        
        # Initialize components
        self.db_manager = DatabaseManager(config.database.database_url)
        self.bot_manager = BotManager(self.db_manager, config)
        self.command_distributor = CommandDistributor(config)
        
        # Active sessions and statistics
        self.active_sessions: Dict[str, AttackSession] = {}
        self.current_attack: Optional[AttackConfig] = None
        
        # WebSocket connections
        self.websocket_connections: Dict[str, WebSocket] = {}
        
        self.logger.info("C2 Server initialized")
    
    async def startup(self):
        """Initialize server components."""
        try:
            await self.db_manager.initialize()
            await self.bot_manager.start()
            await self.command_distributor.start()
            self.logger.info("C2 Server startup completed")
        except Exception as e:
            self.logger.error(f"Failed to start C2 server: {e}")
            raise
    
    async def shutdown(self):
        """Cleanup server components."""
        try:
            # Stop any active attacks
            if self.current_attack:
                await self.stop_attack()
            
            # Stop command distributor
            await self.command_distributor.stop()
            
            # Disconnect all bots
            await self.bot_manager.disconnect_all_bots()
            
            # Close database
            await self.db_manager.close()
            
            self.logger.info("C2 Server shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def handle_bot_connection(self, websocket: WebSocket, bot_id: str):
        """Handle new bot WebSocket connection."""
        try:
            await websocket.accept()
            self.websocket_connections[bot_id] = websocket
            
            self.logger.info(f"Bot {bot_id} connected via WebSocket")
            
            # Register bot with manager
            await self.bot_manager.register_bot_websocket(bot_id, websocket)
            
            # Listen for messages from bot
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self.handle_bot_message(bot_id, message)
                    
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON from bot {bot_id}")
                except Exception as e:
                    self.logger.error(f"Error handling message from bot {bot_id}: {e}")
                    break
        
        except Exception as e:
            self.logger.error(f"Error in bot connection {bot_id}: {e}")
        
        finally:
            # Clean up connection
            if bot_id in self.websocket_connections:
                del self.websocket_connections[bot_id]
            await self.bot_manager.unregister_bot(bot_id)
            self.logger.info(f"Bot {bot_id} disconnected")
    
    async def handle_bot_message(self, bot_id: str, message: dict):
        """Handle messages from bot clients."""
        try:
            message_type = message.get("type")
            
            if message_type == "heartbeat":
                heartbeat = HeartbeatMessage(**message["data"])
                await self.bot_manager.update_bot_heartbeat(bot_id, heartbeat)
            
            elif message_type == "registration":
                bot_data = BotClient(**message["data"])
                await self.bot_manager.register_bot(bot_data)
            
            elif message_type == "attack_status":
                # Handle attack status updates from bots
                status = message["data"]
                await self.handle_attack_status_update(bot_id, status)
            
            elif message_type in ["command_acknowledged", "command_completed", "command_failed"]:
                # Handle command responses
                await self.command_distributor.handle_command_response(bot_id, message)
            
            elif message_type == "error":
                error_msg = message["data"].get("message", "Unknown error")
                self.logger.error(f"Bot {bot_id} reported error: {error_msg}")
                
                # Log error to database
                log_entry = LogEntry(
                    timestamp=datetime.now(),
                    level="ERROR",
                    source="BOT",
                    message=f"Bot {bot_id}: {error_msg}",
                    bot_id=bot_id
                )
                await self.db_manager.log_entry(log_entry)
            
            else:
                self.logger.warning(f"Unknown message type from bot {bot_id}: {message_type}")
        
        except Exception as e:
            self.logger.error(f"Error handling message from bot {bot_id}: {e}")
    
    async def handle_attack_status_update(self, bot_id: str, status: dict):
        """Handle attack status updates from bots."""
        try:
            # Update session metrics if we have an active attack
            if self.current_attack:
                # This would be expanded to aggregate metrics from all bots
                self.logger.info(f"Attack status from bot {bot_id}: {status}")
        
        except Exception as e:
            self.logger.error(f"Error handling attack status from bot {bot_id}: {e}")
    
    async def start_attack(self, attack_config: AttackConfig) -> bool:
        """Start a new attack with the given configuration."""
        try:
            # Validate attack configuration
            if not self.validate_attack_config(attack_config):
                return False
            
            # Check if we already have an active attack
            if self.current_attack:
                self.logger.warning("Attack already in progress")
                return False
            
            # Get active bots
            active_bots = await self.bot_manager.get_active_bots()
            if not active_bots:
                self.logger.warning("No active bots available for attack")
                return False
            
            # Update attack config with active bots
            attack_config.active_bots = [bot.bot_id for bot in active_bots[:self.config.safety.max_bots]]
            
            # Create attack session
            session = AttackSession(
                session_id=generate_session_id(),
                start_time=datetime.now(),
                attack_config=attack_config,
                participating_bots=active_bots,
                metrics=SessionMetrics()
            )
            
            # Store session
            self.active_sessions[session.session_id] = session
            await self.db_manager.create_attack_session(session)
            
            # Send attack command to bots using command distributor
            command = CommandMessage(
                command="start_attack",
                attack_config=attack_config,
                target_bots=attack_config.active_bots
            )
            
            try:
                command_id = await self.command_distributor.distribute_command(
                    command,
                    attack_config.active_bots,
                    self.websocket_connections
                )
                success = True
                self.logger.info(f"Attack command {command_id} distributed to bots")
            except Exception as e:
                self.logger.error(f"Failed to distribute attack command: {e}")
                success = False
            
            if success:
                self.current_attack = attack_config
                self.logger.info(f"Attack started: {attack_config.attack_id}")
                
                # Log attack start
                log_entry = LogEntry(
                    timestamp=datetime.now(),
                    level="INFO",
                    source="C2",
                    message=f"Attack started: {attack_config.attack_type.value} against {attack_config.target_ip}:{attack_config.target_port}",
                    attack_id=attack_config.attack_id
                )
                await self.db_manager.log_entry(log_entry)
                
                return True
            else:
                # Clean up if broadcast failed
                del self.active_sessions[session.session_id]
                return False
        
        except Exception as e:
            self.logger.error(f"Error starting attack: {e}")
            return False
    
    async def stop_attack(self) -> bool:
        """Stop the current attack."""
        try:
            if not self.current_attack:
                self.logger.warning("No active attack to stop")
                return False
            
            # Send stop command to bots using command distributor
            command = CommandMessage(
                command="stop_attack",
                target_bots=self.current_attack.active_bots
            )
            
            try:
                command_id = await self.command_distributor.distribute_command(
                    command,
                    self.current_attack.active_bots,
                    self.websocket_connections
                )
                success = True
                self.logger.info(f"Stop command {command_id} distributed to bots")
            except Exception as e:
                self.logger.error(f"Failed to distribute stop command: {e}")
                success = False
            
            # Update session end time
            for session in self.active_sessions.values():
                if session.attack_config.attack_id == self.current_attack.attack_id:
                    session.end_time = datetime.now()
                    await self.db_manager.update_attack_session(session)
                    break
            
            # Log attack stop
            log_entry = LogEntry(
                timestamp=datetime.now(),
                level="INFO",
                source="C2",
                message=f"Attack stopped: {self.current_attack.attack_id}",
                attack_id=self.current_attack.attack_id
            )
            await self.db_manager.log_entry(log_entry)
            
            self.current_attack = None
            self.logger.info("Attack stopped")
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error stopping attack: {e}")
            return False
    
    def validate_attack_config(self, config: AttackConfig) -> bool:
        """Validate attack configuration against safety rules."""
        try:
            # Check if target IP is allowed
            if not self.config.network.is_ip_allowed(config.target_ip):
                self.logger.error(f"Target IP {config.target_ip} is not allowed")
                return False
            
            # Check intensity limits
            if config.intensity > self.config.safety.max_requests_per_second_per_bot:
                self.logger.error(f"Attack intensity {config.intensity} exceeds limit")
                return False
            
            # Check duration limits
            if config.duration > self.config.safety.max_attack_duration:
                self.logger.error(f"Attack duration {config.duration} exceeds limit")
                return False
            
            # Check port range
            if not (1 <= config.target_port <= 65535):
                self.logger.error(f"Invalid target port: {config.target_port}")
                return False
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error validating attack config: {e}")
            return False
    
    async def get_server_status(self) -> dict:
        """Get current server status and statistics."""
        try:
            active_bots = await self.bot_manager.get_active_bots()
            
            status = {
                "server_ip": get_local_ip(),
                "server_port": self.config.c2_server.port,
                "websocket_port": self.config.c2_server.websocket_port,
                "active_bots": len(active_bots),
                "max_bots": self.config.safety.max_bots,
                "current_attack": self.current_attack.dict() if self.current_attack else None,
                "active_sessions": len(self.active_sessions),
                "uptime": datetime.now().isoformat(),
                "bots": [bot.dict() for bot in active_bots]
            }
            
            return status
        
        except Exception as e:
            self.logger.error(f"Error getting server status: {e}")
            return {"error": str(e)}


# Global server instance
server_instance: Optional[C2Server] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    global server_instance
    
    # Startup
    config = LabConfig.load_from_env()
    server_instance = C2Server(config)
    await server_instance.startup()
    
    yield
    
    # Shutdown
    if server_instance:
        await server_instance.shutdown()


# Create FastAPI application
app = FastAPI(
    title="DDoS Simulation Lab - C2 Server",
    description="Command and Control server for educational DDoS simulation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_server() -> C2Server:
    """Dependency to get server instance."""
    if not server_instance:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return server_instance


# WebSocket endpoint for bot connections
@app.websocket("/ws/bot/{bot_id}")
async def websocket_bot_endpoint(websocket: WebSocket, bot_id: str):
    """WebSocket endpoint for bot connections."""
    server = get_server()
    await server.handle_bot_connection(websocket, bot_id)


# REST API endpoints
@app.get("/api/status")
async def get_status(server: C2Server = Depends(get_server)):
    """Get server status and statistics."""
    return await server.get_server_status()


@app.post("/api/attack/start")
async def start_attack_endpoint(
    attack_config: AttackConfig,
    server: C2Server = Depends(get_server)
):
    """Start a new attack."""
    # Generate attack ID if not provided
    if not attack_config.attack_id:
        attack_config.attack_id = generate_attack_id()
    
    success = await server.start_attack(attack_config)
    
    if success:
        return {"status": "success", "attack_id": attack_config.attack_id}
    else:
        raise HTTPException(status_code=400, detail="Failed to start attack")


@app.post("/api/attack/stop")
async def stop_attack_endpoint(server: C2Server = Depends(get_server)):
    """Stop the current attack."""
    success = await server.stop_attack()
    
    if success:
        return {"status": "success", "message": "Attack stopped"}
    else:
        raise HTTPException(status_code=400, detail="Failed to stop attack")


@app.get("/api/bots")
async def get_bots(server: C2Server = Depends(get_server)):
    """Get list of active bots."""
    bots = await server.bot_manager.get_active_bots()
    return {"bots": [bot.dict() for bot in bots]}


@app.get("/api/logs")
async def get_logs(
    limit: int = 100,
    level: Optional[str] = None,
    server: C2Server = Depends(get_server)
):
    """Get recent log entries."""
    logs = await server.db_manager.get_recent_logs(limit, level)
    return {"logs": [log.dict() for log in logs]}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    # Load configuration
    config = LabConfig.load_from_env()
    
    # Run server
    uvicorn.run(
        "c2_server.main:app",
        host=config.c2_server.host,
        port=config.c2_server.port,
        log_level=config.c2_server.log_level.lower(),
        reload=False
    )
@app.get(
"/api/commands")
async def get_commands(server: C2Server = Depends(get_server)):
    """Get active commands status."""
    return {
        "active_commands": server.command_distributor.get_active_commands()
    }


@app.get("/api/commands/{command_id}")
async def get_command_status(command_id: str, server: C2Server = Depends(get_server)):
    """Get status of a specific command."""
    status = server.command_distributor.get_command_status(command_id)
    if status:
        return status
    else:
        raise HTTPException(status_code=404, detail="Command not found")


@app.post("/api/emergency-stop")
async def emergency_stop_endpoint(server: C2Server = Depends(get_server)):
    """Emergency stop all attacks immediately."""
    try:
        command_id = await server.command_distributor.emergency_stop_all(
            server.websocket_connections
        )
        
        # Also stop current attack tracking
        if server.current_attack:
            server.current_attack = None
        
        return {
            "status": "success", 
            "message": "Emergency stop initiated",
            "command_id": command_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")