"""
Bot management for the C2 server.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from fastapi import WebSocket

from shared.config import LabConfig
from shared.models import BotClient, CommandMessage, HeartbeatMessage, BotStatus
from .database import DatabaseManager


class BotManager:
    """Manages bot connections and communication."""
    
    def __init__(self, db_manager: DatabaseManager, config: LabConfig):
        self.db_manager = db_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Active bot connections
        self.active_bots: Dict[str, BotClient] = {}
        self.bot_websockets: Dict[str, WebSocket] = {}
        
        # Heartbeat monitoring
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start(self):
        """Start the bot manager."""
        self.running = True
        
        # Start heartbeat monitoring task
        self.heartbeat_task = asyncio.create_task(self.heartbeat_monitor())
        
        self.logger.info("Bot manager started")
    
    async def stop(self):
        """Stop the bot manager."""
        self.running = False
        
        # Cancel heartbeat monitoring
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all bots
        await self.disconnect_all_bots()
        
        self.logger.info("Bot manager stopped")
    
    async def register_bot(self, bot: BotClient) -> bool:
        """Register a new bot."""
        try:
            # Check if we've reached the maximum number of bots
            if len(self.active_bots) >= self.config.safety.max_bots:
                self.logger.warning(f"Maximum number of bots ({self.config.safety.max_bots}) reached")
                return False
            
            # Validate bot IP is in allowed networks
            if not self.config.network.is_ip_allowed(bot.ip_address):
                self.logger.warning(f"Bot {bot.bot_id} IP {bot.ip_address} not in allowed networks")
                return False
            
            # Add to active bots
            self.active_bots[bot.bot_id] = bot
            
            # Register in database
            success = await self.db_manager.register_bot(bot)
            
            if success:
                self.logger.info(f"Bot registered: {bot.bot_id} ({bot.ip_address})")
                return True
            else:
                # Remove from active bots if database registration failed
                if bot.bot_id in self.active_bots:
                    del self.active_bots[bot.bot_id]
                return False
        
        except Exception as e:
            self.logger.error(f"Error registering bot {bot.bot_id}: {e}")
            return False
    
    async def register_bot_websocket(self, bot_id: str, websocket: WebSocket):
        """Register a WebSocket connection for a bot."""
        self.bot_websockets[bot_id] = websocket
        self.logger.info(f"WebSocket registered for bot {bot_id}")
    
    async def unregister_bot(self, bot_id: str):
        """Unregister a bot."""
        try:
            # Remove from active bots
            if bot_id in self.active_bots:
                del self.active_bots[bot_id]
            
            # Remove WebSocket connection
            if bot_id in self.bot_websockets:
                del self.bot_websockets[bot_id]
            
            # Update database status
            await self.db_manager.update_bot_heartbeat(
                bot_id, 
                datetime.now(), 
                BotStatus.DISCONNECTED.value, 
                0.0
            )
            
            self.logger.info(f"Bot unregistered: {bot_id}")
        
        except Exception as e:
            self.logger.error(f"Error unregistering bot {bot_id}: {e}")
    
    async def update_bot_heartbeat(self, bot_id: str, heartbeat: HeartbeatMessage) -> bool:
        """Update bot heartbeat information."""
        try:
            # Update in-memory bot info
            if bot_id in self.active_bots:
                bot = self.active_bots[bot_id]
                bot.last_heartbeat = heartbeat.timestamp
                bot.status = heartbeat.status
                bot.current_load = heartbeat.current_load
            
            # Update in database
            success = await self.db_manager.update_bot_heartbeat(
                bot_id,
                heartbeat.timestamp,
                heartbeat.status.value,
                heartbeat.current_load
            )
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error updating bot heartbeat {bot_id}: {e}")
            return False
    
    async def get_active_bots(self) -> List[BotClient]:
        """Get list of currently active bots."""
        try:
            # Get bots from database (this ensures we have the most up-to-date info)
            db_bots = await self.db_manager.get_active_bots(
                self.config.safety.heartbeat_timeout
            )
            
            # Update in-memory cache
            active_bot_ids = {bot.bot_id for bot in db_bots}
            
            # Remove bots that are no longer active
            for bot_id in list(self.active_bots.keys()):
                if bot_id not in active_bot_ids:
                    del self.active_bots[bot_id]
            
            # Update active bots cache
            for bot in db_bots:
                self.active_bots[bot.bot_id] = bot
            
            return db_bots
        
        except Exception as e:
            self.logger.error(f"Error getting active bots: {e}")
            return []
    
    async def get_bot(self, bot_id: str) -> Optional[BotClient]:
        """Get a specific bot by ID."""
        return self.active_bots.get(bot_id)
    
    async def broadcast_command(self, command: CommandMessage) -> bool:
        """Broadcast a command to all or specific bots."""
        try:
            # Determine target bots
            if command.target_bots:
                target_bots = command.target_bots
            else:
                target_bots = list(self.active_bots.keys())
            
            # Send command to each target bot
            success_count = 0
            total_count = len(target_bots)
            
            for bot_id in target_bots:
                if bot_id in self.bot_websockets:
                    try:
                        websocket = self.bot_websockets[bot_id]
                        message = {
                            "type": "command",
                            "data": command.dict()
                        }
                        await websocket.send_text(json.dumps(message))
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to send command to bot {bot_id}: {e}")
                        # Remove failed WebSocket connection
                        if bot_id in self.bot_websockets:
                            del self.bot_websockets[bot_id]
                else:
                    self.logger.warning(f"No WebSocket connection for bot {bot_id}")
            
            self.logger.info(f"Command broadcast: {success_count}/{total_count} bots reached")
            
            # Return True if at least one bot received the command
            return success_count > 0
        
        except Exception as e:
            self.logger.error(f"Error broadcasting command: {e}")
            return False
    
    async def send_command_to_bot(self, bot_id: str, command: CommandMessage) -> bool:
        """Send a command to a specific bot."""
        try:
            if bot_id not in self.bot_websockets:
                self.logger.warning(f"No WebSocket connection for bot {bot_id}")
                return False
            
            websocket = self.bot_websockets[bot_id]
            message = {
                "type": "command",
                "data": command.dict()
            }
            
            await websocket.send_text(json.dumps(message))
            self.logger.info(f"Command sent to bot {bot_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending command to bot {bot_id}: {e}")
            # Remove failed WebSocket connection
            if bot_id in self.bot_websockets:
                del self.bot_websockets[bot_id]
            return False
    
    async def disconnect_all_bots(self):
        """Disconnect all bots gracefully."""
        try:
            # Send disconnect command to all bots
            disconnect_command = CommandMessage(
                command="disconnect",
                timestamp=datetime.now()
            )
            
            await self.broadcast_command(disconnect_command)
            
            # Wait a moment for graceful disconnection
            await asyncio.sleep(2)
            
            # Close all WebSocket connections
            for bot_id, websocket in list(self.bot_websockets.items()):
                try:
                    await websocket.close()
                except Exception as e:
                    self.logger.error(f"Error closing WebSocket for bot {bot_id}: {e}")
            
            # Clear all connections
            self.bot_websockets.clear()
            self.active_bots.clear()
            
            self.logger.info("All bots disconnected")
        
        except Exception as e:
            self.logger.error(f"Error disconnecting all bots: {e}")
    
    async def heartbeat_monitor(self):
        """Monitor bot heartbeats and remove inactive bots."""
        while self.running:
            try:
                # Check for inactive bots
                cutoff_time = datetime.now() - timedelta(seconds=self.config.safety.heartbeat_timeout)
                inactive_bots = []
                
                for bot_id, bot in self.active_bots.items():
                    if bot.last_heartbeat < cutoff_time:
                        inactive_bots.append(bot_id)
                
                # Remove inactive bots
                for bot_id in inactive_bots:
                    self.logger.warning(f"Bot {bot_id} heartbeat timeout, removing")
                    await self.unregister_bot(bot_id)
                
                # Wait before next check
                await asyncio.sleep(self.config.safety.heartbeat_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def get_bot_statistics(self) -> dict:
        """Get statistics about connected bots."""
        try:
            total_bots = len(self.active_bots)
            connected_bots = sum(1 for bot in self.active_bots.values() 
                               if bot.status == BotStatus.CONNECTED)
            attacking_bots = sum(1 for bot in self.active_bots.values() 
                                if bot.status == BotStatus.ATTACKING)
            
            avg_load = 0.0
            if total_bots > 0:
                avg_load = sum(bot.current_load for bot in self.active_bots.values()) / total_bots
            
            return {
                "total_bots": total_bots,
                "connected_bots": connected_bots,
                "attacking_bots": attacking_bots,
                "max_bots": self.config.safety.max_bots,
                "average_load": avg_load,
                "websocket_connections": len(self.bot_websockets)
            }
        
        except Exception as e:
            self.logger.error(f"Error getting bot statistics: {e}")
            return {
                "total_bots": 0,
                "connected_bots": 0,
                "attacking_bots": 0,
                "max_bots": self.config.safety.max_bots,
                "average_load": 0.0,
                "websocket_connections": 0,
                "error": str(e)
            }