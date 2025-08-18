"""
Unit tests for WebSocket client with auto-reconnection.
"""
import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from shared.config import BotClientConfig
from shared.models import BotStatus
from bot_client.websocket_client import WebSocketClient


@pytest.fixture
def config():
    """Test bot client configuration."""
    config = BotClientConfig()
    config.c2_server_host = "127.0.0.1"
    config.c2_server_port = 8081
    config.reconnect_interval = 1
    config.max_reconnect_attempts = 3
    config.heartbeat_interval = 2
    return config


@pytest.fixture
def websocket_client(config):
    """WebSocket client for testing."""
    return WebSocketClient(config, "test-bot-001")


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.wait_closed = AsyncMock()
    return mock_ws


@pytest.mark.asyncio
async def test_websocket_client_initialization(websocket_client):
    """Test WebSocket client initialization."""
    assert websocket_client.bot_id == "test-bot-001"
    assert not websocket_client.connected
    assert not websocket_client.running
    assert websocket_client.reconnect_attempts == 0
    assert websocket_client.messages_sent == 0
    assert websocket_client.messages_received == 0


@pytest.mark.asyncio
async def test_message_handler_registration(websocket_client):
    """Test message handler registration."""
    async def test_handler(message):
        pass
    
    websocket_client.register_message_handler("test_message", test_handler)
    
    assert "test_message" in websocket_client.message_handlers
    assert websocket_client.message_handlers["test_message"] == test_handler


@pytest.mark.asyncio
async def test_send_message_not_connected(websocket_client):
    """Test sending message when not connected."""
    result = await websocket_client.send_message("test", {"data": "test"})
    
    assert result is False


@pytest.mark.asyncio
async def test_send_message_connected(websocket_client, mock_websocket):
    """Test sending message when connected."""
    # Set up connected state
    websocket_client.websocket = mock_websocket
    websocket_client.connected = True
    
    # Send message
    result = await websocket_client.send_message("test", {"data": "test"})
    
    # Verify
    assert result is True
    assert websocket_client.messages_sent == 1
    mock_websocket.send.assert_called_once()
    
    # Check message format
    sent_message = json.loads(mock_websocket.send.call_args[0][0])
    assert sent_message["type"] == "test"
    assert sent_message["data"] == {"data": "test"}
    assert sent_message["bot_id"] == "test-bot-001"


@pytest.mark.asyncio
async def test_send_heartbeat(websocket_client, mock_websocket):
    """Test sending heartbeat message."""
    # Set up connected state
    websocket_client.websocket = mock_websocket
    websocket_client.connected = True
    
    # Send heartbeat
    result = await websocket_client.send_heartbeat(
        BotStatus.CONNECTED, 
        25.5, 
        {"memory_percent": 60.0}
    )
    
    # Verify
    assert result is True
    mock_websocket.send.assert_called_once()
    
    # Check heartbeat message format
    sent_message = json.loads(mock_websocket.send.call_args[0][0])
    assert sent_message["type"] == "heartbeat"
    assert sent_message["data"]["status"] == BotStatus.CONNECTED.value
    assert sent_message["data"]["current_load"] == 25.5
    assert sent_message["data"]["metrics"]["memory_percent"] == 60.0


@pytest.mark.asyncio
async def test_send_registration(websocket_client, mock_websocket):
    """Test sending registration message."""
    # Set up connected state
    websocket_client.websocket = mock_websocket
    websocket_client.connected = True
    
    # Registration data
    bot_info = {
        "bot_id": "test-bot-001",
        "ip_address": "192.168.1.100",
        "hostname": "test-host",
        "capabilities": ["http_flood", "tcp_syn"]
    }
    
    # Send registration
    result = await websocket_client.send_registration(bot_info)
    
    # Verify
    assert result is True
    mock_websocket.send.assert_called_once()
    
    # Check registration message format
    sent_message = json.loads(mock_websocket.send.call_args[0][0])
    assert sent_message["type"] == "registration"
    assert sent_message["data"] == bot_info


@pytest.mark.asyncio
async def test_send_command_response(websocket_client, mock_websocket):
    """Test sending command response."""
    # Set up connected state
    websocket_client.websocket = mock_websocket
    websocket_client.connected = True
    
    # Send command response
    result = await websocket_client.send_command_response(
        "cmd-123", 
        "command_acknowledged", 
        {"status": "received"}
    )
    
    # Verify
    assert result is True
    mock_websocket.send.assert_called_once()
    
    # Check command response format
    sent_message = json.loads(mock_websocket.send.call_args[0][0])
    assert sent_message["type"] == "command_response"
    assert sent_message["data"]["command_id"] == "cmd-123"
    assert sent_message["data"]["type"] == "command_acknowledged"
    assert sent_message["data"]["data"]["status"] == "received"


@pytest.mark.asyncio
async def test_connection_stats(websocket_client):
    """Test getting connection statistics."""
    # Set some state
    websocket_client.connected = True
    websocket_client.connection_count = 2
    websocket_client.messages_sent = 10
    websocket_client.messages_received = 5
    websocket_client.last_connection_time = datetime.now()
    
    stats = websocket_client.get_connection_stats()
    
    assert stats["connected"] is True
    assert stats["bot_id"] == "test-bot-001"
    assert stats["connection_count"] == 2
    assert stats["messages_sent"] == 10
    assert stats["messages_received"] == 5
    assert stats["c2_server_host"] == "127.0.0.1"
    assert stats["c2_server_port"] == 8081


@pytest.mark.asyncio
async def test_handle_message_with_handler(websocket_client):
    """Test handling message with registered handler."""
    # Register handler
    handler_called = False
    received_message = None
    
    async def test_handler(message):
        nonlocal handler_called, received_message
        handler_called = True
        received_message = message
    
    websocket_client.register_message_handler("test_command", test_handler)
    
    # Handle message
    test_message = {
        "type": "test_command",
        "data": {"command": "test"}
    }
    
    await websocket_client._handle_message(test_message)
    
    # Verify handler was called
    assert handler_called is True
    assert received_message == test_message


@pytest.mark.asyncio
async def test_handle_message_without_handler(websocket_client):
    """Test handling message without registered handler."""
    # This should not raise an exception, just log a warning
    test_message = {
        "type": "unknown_command",
        "data": {"command": "test"}
    }
    
    # Should complete without error
    await websocket_client._handle_message(test_message)


@pytest.mark.asyncio
async def test_handle_message_invalid_format(websocket_client):
    """Test handling message with invalid format."""
    # Message without type
    invalid_message = {
        "data": {"command": "test"}
    }
    
    # Should complete without error
    await websocket_client._handle_message(invalid_message)


@pytest.mark.asyncio
@patch('bot_client.websocket_client.websockets.connect')
async def test_connection_success(mock_connect, websocket_client, mock_websocket):
    """Test successful WebSocket connection."""
    # Mock successful connection
    mock_connect.return_value = mock_websocket
    
    # Mock system utilities
    with patch('bot_client.websocket_client.get_local_ip', return_value='192.168.1.100'), \
         patch('bot_client.websocket_client.get_hostname', return_value='test-host'), \
         patch('shared.utils.get_system_metrics', return_value={'cpu_percent': 10.0}):
        
        # Start client
        await websocket_client.start()
        
        # Give it a moment to connect
        await asyncio.sleep(0.1)
        
        # Verify connection attempt
        mock_connect.assert_called_once()
        
        # Stop client
        await websocket_client.stop()


@pytest.mark.asyncio
async def test_connection_failure_and_retry(websocket_client):
    """Test connection failure and retry logic."""
    # Mock connection failure
    with patch('bot_client.websocket_client.websockets.connect', side_effect=OSError("Connection failed")):
        
        # Start client
        await websocket_client.start()
        
        # Give it time to attempt connection and fail
        await asyncio.sleep(0.1)
        
        # Verify reconnection attempts are tracked
        assert websocket_client.reconnect_attempts > 0
        assert not websocket_client.connected
        
        # Stop client
        await websocket_client.stop()


@pytest.mark.asyncio
async def test_max_reconnection_attempts(websocket_client):
    """Test that client stops after max reconnection attempts."""
    # Set low max attempts for testing
    websocket_client.config.max_reconnect_attempts = 2
    websocket_client.config.reconnect_interval = 0.1  # Fast retry for testing
    
    # Mock connection failure
    with patch('bot_client.websocket_client.websockets.connect', side_effect=OSError("Connection failed")):
        
        # Start client
        await websocket_client.start()
        
        # Give it time to exhaust retry attempts
        await asyncio.sleep(0.5)
        
        # Verify client stopped trying
        assert not websocket_client.running
        assert websocket_client.reconnect_attempts >= websocket_client.config.max_reconnect_attempts


@pytest.mark.asyncio
async def test_stop_client(websocket_client, mock_websocket):
    """Test stopping the WebSocket client."""
    # Set up running state
    websocket_client.running = True
    websocket_client.connected = True
    websocket_client.websocket = mock_websocket
    
    # Create mock tasks
    websocket_client.connection_task = AsyncMock()
    websocket_client.heartbeat_task = AsyncMock()
    websocket_client.message_handler_task = AsyncMock()
    
    # Stop client
    await websocket_client.stop()
    
    # Verify cleanup
    assert not websocket_client.running
    assert not websocket_client.connected
    assert websocket_client.websocket is None
    mock_websocket.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])