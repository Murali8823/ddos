"""
Unit tests for command distribution system.
"""
import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from shared.config import LabConfig
from shared.models import CommandMessage, AttackConfig, AttackType
from c2_server.command_handler import (
    CommandDistributor, CommandQueue, CommandExecution, 
    CommandType, CommandStatus
)


@pytest.fixture
def config():
    """Test configuration."""
    return LabConfig()


@pytest.fixture
def command_queue():
    """Command queue for testing."""
    return CommandQueue(max_size=10)


@pytest.fixture
def command_distributor(config):
    """Command distributor for testing."""
    return CommandDistributor(config)


@pytest.fixture
def sample_attack_config():
    """Sample attack configuration."""
    return AttackConfig(
        attack_id="test-attack-001",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="192.168.1.200",
        target_port=80,
        intensity=50,
        duration=60
    )


@pytest.fixture
def sample_command(sample_attack_config):
    """Sample command message."""
    return CommandMessage(
        command=CommandType.START_ATTACK.value,
        attack_config=sample_attack_config,
        timestamp=datetime.now()
    )


@pytest.mark.asyncio
async def test_command_execution_lifecycle():
    """Test command execution lifecycle."""
    # Arrange
    command = CommandMessage(
        command=CommandType.START_ATTACK.value,
        timestamp=datetime.now()
    )
    target_bots = ["bot-1", "bot-2", "bot-3"]
    
    execution = CommandExecution(command, target_bots)
    
    # Assert initial state
    assert execution.status == CommandStatus.PENDING
    assert len(execution.target_bots) == 3
    assert len(execution.sent_to) == 0
    
    # Test marking as sent
    execution.mark_sent("bot-1")
    execution.mark_sent("bot-2")
    assert execution.status == CommandStatus.PENDING  # Not all sent yet
    
    execution.mark_sent("bot-3")
    assert execution.status == CommandStatus.SENT  # All sent
    
    # Test marking as acknowledged
    execution.mark_acknowledged("bot-1")
    execution.mark_acknowledged("bot-2")
    execution.mark_acknowledged("bot-3")
    assert execution.status == CommandStatus.ACKNOWLEDGED
    
    # Test marking as completed
    execution.mark_completed("bot-1")
    execution.mark_completed("bot-2")
    execution.mark_completed("bot-3")
    assert execution.status == CommandStatus.COMPLETED


@pytest.mark.asyncio
async def test_command_queue_enqueue_dequeue(command_queue, sample_command):
    """Test command queue enqueue and dequeue operations."""
    # Test enqueue
    command_id = await command_queue.enqueue_command(sample_command, ["bot-1", "bot-2"])
    
    assert command_id in command_queue.active_commands
    assert len(command_queue.active_commands) == 1
    
    # Test dequeue
    result = await command_queue.get_next_command()
    assert result is not None
    
    dequeued_command_id, execution = result
    assert dequeued_command_id == command_id
    assert execution.command == sample_command


@pytest.mark.asyncio
async def test_command_queue_status_tracking(command_queue, sample_command):
    """Test command status tracking in queue."""
    # Enqueue command
    command_id = await command_queue.enqueue_command(sample_command, ["bot-1", "bot-2"])
    
    # Test marking as sent
    command_queue.mark_command_sent(command_id, "bot-1")
    command_queue.mark_command_sent(command_id, "bot-2")
    
    status = command_queue.get_command_status(command_id)
    assert status["status"] == CommandStatus.SENT.value
    assert status["sent_to"] == 2
    
    # Test marking as completed
    command_queue.mark_command_completed(command_id, "bot-1")
    command_queue.mark_command_completed(command_id, "bot-2")
    
    # Command should be moved to history
    assert command_id not in command_queue.active_commands
    assert len(command_queue.command_history) == 1
    
    # Should still be able to get status from history
    status = command_queue.get_command_status(command_id)
    assert status["status"] == CommandStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_command_distributor_validation(command_distributor, sample_attack_config):
    """Test command validation in distributor."""
    # Test valid command
    valid_command = CommandMessage(
        command=CommandType.START_ATTACK.value,
        attack_config=sample_attack_config,
        timestamp=datetime.now()
    )
    
    assert command_distributor._validate_command(valid_command) is True
    
    # Test invalid command type
    invalid_command = CommandMessage(
        command="invalid_command",
        timestamp=datetime.now()
    )
    
    assert command_distributor._validate_command(invalid_command) is False


@pytest.mark.asyncio
async def test_command_distributor_attack_validation(command_distributor, config):
    """Test attack command validation."""
    # Test valid attack config
    valid_config = AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="192.168.1.200",  # Should be in allowed networks
        target_port=80,
        intensity=50,  # Within limits
        duration=60   # Within limits
    )
    
    valid_command = CommandMessage(
        command=CommandType.START_ATTACK.value,
        attack_config=valid_config,
        timestamp=datetime.now()
    )
    
    assert command_distributor._validate_start_attack(valid_command) is True
    
    # Test invalid target IP
    invalid_config = AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="127.0.0.1",  # Blocked network
        target_port=80,
        intensity=50,
        duration=60
    )
    
    invalid_command = CommandMessage(
        command=CommandType.START_ATTACK.value,
        attack_config=invalid_config,
        timestamp=datetime.now()
    )
    
    assert command_distributor._validate_start_attack(invalid_command) is False
    
    # Test excessive intensity
    excessive_config = AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="192.168.1.200",
        target_port=80,
        intensity=1000,  # Exceeds limit
        duration=60
    )
    
    excessive_command = CommandMessage(
        command=CommandType.START_ATTACK.value,
        attack_config=excessive_config,
        timestamp=datetime.now()
    )
    
    assert command_distributor._validate_start_attack(excessive_command) is False


@pytest.mark.asyncio
async def test_command_distributor_distribute_command(command_distributor, sample_command):
    """Test command distribution to bots."""
    # Mock WebSocket connections
    mock_websocket_1 = AsyncMock()
    mock_websocket_2 = AsyncMock()
    
    bot_websockets = {
        "bot-1": mock_websocket_1,
        "bot-2": mock_websocket_2
    }
    
    target_bots = ["bot-1", "bot-2", "bot-3"]  # bot-3 not connected
    
    # Start distributor
    await command_distributor.start()
    
    try:
        # Distribute command
        command_id = await command_distributor.distribute_command(
            sample_command,
            target_bots,
            bot_websockets
        )
        
        # Verify command was sent to connected bots
        assert mock_websocket_1.send_text.called
        assert mock_websocket_2.send_text.called
        
        # Verify command status
        status = command_distributor.get_command_status(command_id)
        assert status is not None
        assert status["target_bots"] == 2  # Only connected bots
        assert status["sent_to"] == 2
    
    finally:
        await command_distributor.stop()


@pytest.mark.asyncio
async def test_command_distributor_handle_response(command_distributor, sample_command):
    """Test handling command responses from bots."""
    # Mock WebSocket connections
    bot_websockets = {"bot-1": AsyncMock()}
    
    # Start distributor
    await command_distributor.start()
    
    try:
        # Distribute command
        command_id = await command_distributor.distribute_command(
            sample_command,
            ["bot-1"],
            bot_websockets
        )
        
        # Handle acknowledgment response
        ack_response = {
            "command_id": command_id,
            "type": "command_acknowledged"
        }
        
        await command_distributor.handle_command_response("bot-1", ack_response)
        
        # Verify status update
        status = command_distributor.get_command_status(command_id)
        assert status["acknowledged_by"] == 1
        
        # Handle completion response
        completion_response = {
            "command_id": command_id,
            "type": "command_completed"
        }
        
        await command_distributor.handle_command_response("bot-1", completion_response)
        
        # Verify command is completed and moved to history
        status = command_distributor.get_command_status(command_id)
        assert status["status"] == CommandStatus.COMPLETED.value
    
    finally:
        await command_distributor.stop()


@pytest.mark.asyncio
async def test_command_distributor_emergency_stop(command_distributor):
    """Test emergency stop functionality."""
    # Mock WebSocket connections
    mock_websocket_1 = AsyncMock()
    mock_websocket_2 = AsyncMock()
    
    bot_websockets = {
        "bot-1": mock_websocket_1,
        "bot-2": mock_websocket_2
    }
    
    # Start distributor
    await command_distributor.start()
    
    try:
        # Send emergency stop
        command_id = await command_distributor.emergency_stop_all(bot_websockets)
        
        # Verify emergency stop was sent to all bots
        assert mock_websocket_1.send_text.called
        assert mock_websocket_2.send_text.called
        
        # Verify command status
        status = command_distributor.get_command_status(command_id)
        assert status is not None
        assert status["target_bots"] == 2
        
        # Check that the command type is emergency stop
        sent_message_1 = json.loads(mock_websocket_1.send_text.call_args[0][0])
        assert sent_message_1["data"]["command"] == CommandType.EMERGENCY_STOP.value
    
    finally:
        await command_distributor.stop()


@pytest.mark.asyncio
async def test_command_queue_full_handling(command_queue, sample_command):
    """Test command queue behavior when full."""
    # Fill up the queue
    for i in range(10):  # max_size is 10
        await command_queue.enqueue_command(sample_command, [f"bot-{i}"])
    
    # Try to add one more - should raise exception
    with pytest.raises(Exception, match="Command queue is full"):
        await command_queue.enqueue_command(sample_command, ["bot-overflow"])


if __name__ == "__main__":
    pytest.main([__file__])