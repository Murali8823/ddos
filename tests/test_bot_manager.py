"""
Unit tests for bot connection management.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from shared.config import LabConfig
from shared.models import BotClient, HeartbeatMessage, BotStatus, AttackType
from c2_server.bot_manager import BotManager
from c2_server.database import DatabaseManager


@pytest.fixture
def config():
    """Test configuration."""
    return LabConfig()


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    db_manager = AsyncMock(spec=DatabaseManager)
    db_manager.register_bot.return_value = True
    db_manager.update_bot_heartbeat.return_value = True
    db_manager.get_active_bots.return_value = []
    return db_manager


@pytest.fixture
def bot_manager(config, mock_db_manager):
    """Bot manager instance for testing."""
    return BotManager(mock_db_manager, config)


@pytest.fixture
def sample_bot():
    """Sample bot client for testing."""
    return BotClient(
        bot_id="test-bot-001",
        ip_address="192.168.1.100",
        hostname="test-host",
        connection_time=datetime.now(),
        last_heartbeat=datetime.now(),
        status=BotStatus.CONNECTED,
        capabilities=[AttackType.HTTP_FLOOD, AttackType.TCP_SYN],
        current_load=25.5
    )


@pytest.mark.asyncio
async def test_register_bot_success(bot_manager, sample_bot, mock_db_manager):
    """Test successful bot registration."""
    # Act
    result = await bot_manager.register_bot(sample_bot)
    
    # Assert
    assert result is True
    assert sample_bot.bot_id in bot_manager.active_bots
    assert bot_manager.active_bots[sample_bot.bot_id] == sample_bot
    mock_db_manager.register_bot.assert_called_once_with(sample_bot)


@pytest.mark.asyncio
async def test_register_bot_max_limit(bot_manager, config, mock_db_manager):
    """Test bot registration when maximum limit is reached."""
    # Arrange - fill up to max bots
    config.safety.max_bots = 2
    
    for i in range(2):
        bot = BotClient(
            bot_id=f"bot-{i}",
            ip_address=f"192.168.1.{100+i}",
            hostname=f"host-{i}",
            connection_time=datetime.now(),
            last_heartbeat=datetime.now(),
            status=BotStatus.CONNECTED,
            capabilities=[AttackType.HTTP_FLOOD],
            current_load=0.0
        )
        await bot_manager.register_bot(bot)
    
    # Act - try to register one more bot
    extra_bot = BotClient(
        bot_id="extra-bot",
        ip_address="192.168.1.102",
        hostname="extra-host",
        connection_time=datetime.now(),
        last_heartbeat=datetime.now(),
        status=BotStatus.CONNECTED,
        capabilities=[AttackType.HTTP_FLOOD],
        current_load=0.0
    )
    
    result = await bot_manager.register_bot(extra_bot)
    
    # Assert
    assert result is False
    assert "extra-bot" not in bot_manager.active_bots
    assert len(bot_manager.active_bots) == 2


@pytest.mark.asyncio
async def test_register_bot_invalid_ip(bot_manager, config, mock_db_manager):
    """Test bot registration with invalid IP address."""
    # Arrange - set restrictive network config
    config.network.allowed_networks = ["10.0.0.0/8"]
    
    invalid_bot = BotClient(
        bot_id="invalid-bot",
        ip_address="192.168.1.100",  # Not in allowed networks
        hostname="invalid-host",
        connection_time=datetime.now(),
        last_heartbeat=datetime.now(),
        status=BotStatus.CONNECTED,
        capabilities=[AttackType.HTTP_FLOOD],
        current_load=0.0
    )
    
    # Act
    result = await bot_manager.register_bot(invalid_bot)
    
    # Assert
    assert result is False
    assert "invalid-bot" not in bot_manager.active_bots
    mock_db_manager.register_bot.assert_not_called()


@pytest.mark.asyncio
async def test_register_bot_database_failure(bot_manager, sample_bot, mock_db_manager):
    """Test bot registration when database registration fails."""
    # Arrange
    mock_db_manager.register_bot.return_value = False
    
    # Act
    result = await bot_manager.register_bot(sample_bot)
    
    # Assert
    assert result is False
    assert sample_bot.bot_id not in bot_manager.active_bots


@pytest.mark.asyncio
async def test_unregister_bot(bot_manager, sample_bot, mock_db_manager):
    """Test bot unregistration."""
    # Arrange - register bot first
    await bot_manager.register_bot(sample_bot)
    mock_websocket = MagicMock()
    bot_manager.bot_websockets[sample_bot.bot_id] = mock_websocket
    
    # Act
    await bot_manager.unregister_bot(sample_bot.bot_id)
    
    # Assert
    assert sample_bot.bot_id not in bot_manager.active_bots
    assert sample_bot.bot_id not in bot_manager.bot_websockets
    mock_db_manager.update_bot_heartbeat.assert_called_once()


@pytest.mark.asyncio
async def test_update_bot_heartbeat(bot_manager, sample_bot, mock_db_manager):
    """Test bot heartbeat update."""
    # Arrange
    await bot_manager.register_bot(sample_bot)
    
    heartbeat = HeartbeatMessage(
        bot_id=sample_bot.bot_id,
        timestamp=datetime.now(),
        status=BotStatus.ATTACKING,
        current_load=75.0
    )
    
    # Act
    result = await bot_manager.update_bot_heartbeat(sample_bot.bot_id, heartbeat)
    
    # Assert
    assert result is True
    
    # Check in-memory update
    updated_bot = bot_manager.active_bots[sample_bot.bot_id]
    assert updated_bot.status == BotStatus.ATTACKING
    assert updated_bot.current_load == 75.0
    assert updated_bot.last_heartbeat == heartbeat.timestamp
    
    # Check database call
    mock_db_manager.update_bot_heartbeat.assert_called_once_with(
        sample_bot.bot_id,
        heartbeat.timestamp,
        BotStatus.ATTACKING.value,
        75.0
    )


@pytest.mark.asyncio
async def test_get_active_bots(bot_manager, mock_db_manager):
    """Test getting active bots."""
    # Arrange
    db_bots = [
        BotClient(
            bot_id="bot-1",
            ip_address="192.168.1.100",
            hostname="host-1",
            connection_time=datetime.now(),
            last_heartbeat=datetime.now(),
            status=BotStatus.CONNECTED,
            capabilities=[AttackType.HTTP_FLOOD],
            current_load=10.0
        ),
        BotClient(
            bot_id="bot-2",
            ip_address="192.168.1.101",
            hostname="host-2",
            connection_time=datetime.now(),
            last_heartbeat=datetime.now(),
            status=BotStatus.ATTACKING,
            capabilities=[AttackType.TCP_SYN],
            current_load=50.0
        )
    ]
    
    mock_db_manager.get_active_bots.return_value = db_bots
    
    # Act
    result = await bot_manager.get_active_bots()
    
    # Assert
    assert len(result) == 2
    assert result[0].bot_id == "bot-1"
    assert result[1].bot_id == "bot-2"
    
    # Check that in-memory cache is updated
    assert len(bot_manager.active_bots) == 2
    assert "bot-1" in bot_manager.active_bots
    assert "bot-2" in bot_manager.active_bots


@pytest.mark.asyncio
async def test_get_bot_statistics(bot_manager):
    """Test getting bot statistics."""
    # Arrange - add some bots
    bots = [
        BotClient(
            bot_id="bot-1",
            ip_address="192.168.1.100",
            hostname="host-1",
            connection_time=datetime.now(),
            last_heartbeat=datetime.now(),
            status=BotStatus.CONNECTED,
            capabilities=[AttackType.HTTP_FLOOD],
            current_load=20.0
        ),
        BotClient(
            bot_id="bot-2",
            ip_address="192.168.1.101",
            hostname="host-2",
            connection_time=datetime.now(),
            last_heartbeat=datetime.now(),
            status=BotStatus.ATTACKING,
            capabilities=[AttackType.TCP_SYN],
            current_load=60.0
        ),
        BotClient(
            bot_id="bot-3",
            ip_address="192.168.1.102",
            hostname="host-3",
            connection_time=datetime.now(),
            last_heartbeat=datetime.now(),
            status=BotStatus.CONNECTED,
            capabilities=[AttackType.UDP_FLOOD],
            current_load=30.0
        )
    ]
    
    for bot in bots:
        bot_manager.active_bots[bot.bot_id] = bot
    
    # Act
    stats = bot_manager.get_bot_statistics()
    
    # Assert
    assert stats["total_bots"] == 3
    assert stats["connected_bots"] == 2
    assert stats["attacking_bots"] == 1
    assert stats["average_load"] == 36.666666666666664  # (20 + 60 + 30) / 3
    assert stats["max_bots"] == bot_manager.config.safety.max_bots


@pytest.mark.asyncio
async def test_heartbeat_monitor_removes_inactive_bots(bot_manager, config, mock_db_manager):
    """Test that heartbeat monitor removes inactive bots."""
    # Arrange
    config.safety.heartbeat_timeout = 1  # 1 second timeout for testing
    
    # Add an active bot
    active_bot = BotClient(
        bot_id="active-bot",
        ip_address="192.168.1.100",
        hostname="active-host",
        connection_time=datetime.now(),
        last_heartbeat=datetime.now(),
        status=BotStatus.CONNECTED,
        capabilities=[AttackType.HTTP_FLOOD],
        current_load=10.0
    )
    
    # Add an inactive bot (old heartbeat)
    inactive_bot = BotClient(
        bot_id="inactive-bot",
        ip_address="192.168.1.101",
        hostname="inactive-host",
        connection_time=datetime.now(),
        last_heartbeat=datetime.now() - timedelta(seconds=5),  # Old heartbeat
        status=BotStatus.CONNECTED,
        capabilities=[AttackType.HTTP_FLOOD],
        current_load=10.0
    )
    
    bot_manager.active_bots["active-bot"] = active_bot
    bot_manager.active_bots["inactive-bot"] = inactive_bot
    
    # Start bot manager
    await bot_manager.start()
    
    # Wait for heartbeat monitor to run
    await asyncio.sleep(1.5)
    
    # Stop bot manager
    await bot_manager.stop()
    
    # Assert - inactive bot should be removed
    assert "active-bot" in bot_manager.active_bots
    assert "inactive-bot" not in bot_manager.active_bots


if __name__ == "__main__":
    pytest.main([__file__])