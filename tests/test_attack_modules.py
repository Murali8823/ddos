"""
Unit tests for attack traffic generation modules.
"""
import pytest
import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from shared.models import AttackConfig, AttackType
from bot_client.attack_modules import (
    HTTPFloodAttack, TCPSYNFloodAttack, UDPFloodAttack, 
    AttackManager, AttackModule
)


@pytest.fixture
def http_attack_config():
    """HTTP flood attack configuration."""
    return AttackConfig(
        attack_id="test-http-attack",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="192.168.1.200",
        target_port=80,
        intensity=10,
        duration=5
    )


@pytest.fixture
def tcp_attack_config():
    """TCP SYN flood attack configuration."""
    return AttackConfig(
        attack_id="test-tcp-attack",
        attack_type=AttackType.TCP_SYN,
        target_ip="192.168.1.200",
        target_port=80,
        intensity=10,
        duration=5
    )


@pytest.fixture
def udp_attack_config():
    """UDP flood attack configuration."""
    return AttackConfig(
        attack_id="test-udp-attack",
        attack_type=AttackType.UDP_FLOOD,
        target_ip="192.168.1.200",
        target_port=53,
        intensity=10,
        duration=5
    )


class TestAttackModule:
    """Test base attack module functionality."""
    
    def test_attack_module_initialization(self, http_attack_config):
        """Test attack module initialization."""
        
        class TestAttackModule(AttackModule):
            async def execute_attack(self):
                pass
        
        module = TestAttackModule(http_attack_config)
        
        assert module.config == http_attack_config
        assert module.running is False
        assert module.requests_sent == 0
        assert module.bytes_sent == 0
        assert module.errors == 0
        assert module.start_time is None
    
    def test_get_statistics_no_activity(self, http_attack_config):
        """Test statistics when no activity has occurred."""
        
        class TestAttackModule(AttackModule):
            async def execute_attack(self):
                pass
        
        module = TestAttackModule(http_attack_config)
        stats = module.get_statistics()
        
        assert stats["attack_type"] == AttackType.HTTP_FLOOD.value
        assert stats["running"] is False
        assert stats["requests_sent"] == 0
        assert stats["bytes_sent"] == 0
        assert stats["errors"] == 0
        assert stats["requests_per_second"] == 0
        assert stats["bytes_per_second"] == 0
    
    @pytest.mark.asyncio
    async def test_attack_module_start_stop(self, http_attack_config):
        """Test attack module start and stop."""
        
        class TestAttackModule(AttackModule):
            def __init__(self, config):
                super().__init__(config)
                self.execute_count = 0
            
            async def execute_attack(self):
                self.execute_count += 1
                await asyncio.sleep(0.01)  # Small delay
        
        module = TestAttackModule(http_attack_config)
        
        # Start attack
        success = await module.start()
        assert success is True
        assert module.running is True
        assert module.start_time is not None
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop attack
        await module.stop()
        assert module.running is False
        
        # Check that some executions occurred
        assert module.execute_count > 0


class TestHTTPFloodAttack:
    """Test HTTP flood attack module."""
    
    def test_http_flood_initialization(self, http_attack_config):
        """Test HTTP flood attack initialization."""
        attack = HTTPFloodAttack(http_attack_config)
        
        assert attack.config == http_attack_config
        assert attack.session is None
        assert len(attack.user_agents) > 0
        assert len(attack.target_paths) > 0
    
    @pytest.mark.asyncio
    async def test_http_flood_start_stop(self, http_attack_config):
        """Test HTTP flood attack start and stop."""
        attack = HTTPFloodAttack(http_attack_config)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Start attack
            success = await attack.start()
            assert success is True
            assert attack.session is not None
            
            # Stop attack
            await attack.stop()
            assert attack.running is False
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_http_flood_execute_attack(self, http_attack_config):
        """Test HTTP flood attack execution."""
        attack = HTTPFloodAttack(http_attack_config)
        
        # Mock aiohttp session
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b"response content"
        
        mock_session.request.return_value.__aenter__.return_value = mock_response
        attack.session = mock_session
        
        # Execute attack
        await attack.execute_attack()
        
        # Verify request was made
        mock_session.request.assert_called_once()
        assert attack.bytes_sent > 0
    
    @pytest.mark.asyncio
    async def test_http_flood_execute_attack_no_session(self, http_attack_config):
        """Test HTTP flood attack execution without session."""
        attack = HTTPFloodAttack(http_attack_config)
        
        # Should raise exception when no session
        with pytest.raises(Exception, match="HTTP session not initialized"):
            await attack.execute_attack()


class TestTCPSYNFloodAttack:
    """Test TCP SYN flood attack module."""
    
    def test_tcp_syn_flood_initialization(self, tcp_attack_config):
        """Test TCP SYN flood attack initialization."""
        attack = TCPSYNFloodAttack(tcp_attack_config)
        
        assert attack.config == tcp_attack_config
        assert attack.socket is None
        assert len(attack.source_ports) > 0
        assert attack.port_index == 0
    
    def test_get_next_source_port(self, tcp_attack_config):
        """Test source port rotation."""
        attack = TCPSYNFloodAttack(tcp_attack_config)
        
        port1 = attack._get_next_source_port()
        port2 = attack._get_next_source_port()
        
        assert port1 != port2
        assert 1024 <= port1 <= 65534
        assert 1024 <= port2 <= 65534
    
    def test_calculate_checksum(self, tcp_attack_config):
        """Test checksum calculation."""
        attack = TCPSYNFloodAttack(tcp_attack_config)
        
        # Test with known data
        test_data = b"hello"
        checksum = attack._calculate_checksum(test_data)
        
        assert isinstance(checksum, int)
        assert 0 <= checksum <= 65535
    
    def test_create_ip_header(self, tcp_attack_config):
        """Test IP header creation."""
        attack = TCPSYNFloodAttack(tcp_attack_config)
        
        header = attack._create_ip_header("192.168.1.100", "192.168.1.200", 20)
        
        assert isinstance(header, bytes)
        assert len(header) == 20  # IP header length
    
    def test_create_tcp_header(self, tcp_attack_config):
        """Test TCP header creation."""
        attack = TCPSYNFloodAttack(tcp_attack_config)
        
        header = attack._create_tcp_header("192.168.1.100", "192.168.1.200", 12345, 80)
        
        assert isinstance(header, bytes)
        assert len(header) == 20  # TCP header length
    
    @pytest.mark.asyncio
    async def test_tcp_syn_flood_start_permission_error(self, tcp_attack_config):
        """Test TCP SYN flood start with permission error."""
        attack = TCPSYNFloodAttack(tcp_attack_config)
        
        with patch('socket.socket', side_effect=PermissionError("Permission denied")):
            success = await attack.start()
            assert success is False
    
    @pytest.mark.asyncio
    async def test_tcp_syn_flood_execute_attack_no_socket(self, tcp_attack_config):
        """Test TCP SYN flood execution without socket."""
        attack = TCPSYNFloodAttack(tcp_attack_config)
        
        # Should raise exception when no socket
        with pytest.raises(Exception, match="Raw socket not initialized"):
            await attack.execute_attack()


class TestUDPFloodAttack:
    """Test UDP flood attack module."""
    
    def test_udp_flood_initialization(self, udp_attack_config):
        """Test UDP flood attack initialization."""
        attack = UDPFloodAttack(udp_attack_config)
        
        assert attack.config == udp_attack_config
        assert attack.socket is None
        assert len(attack.payloads) > 0
    
    @pytest.mark.asyncio
    async def test_udp_flood_start_stop(self, udp_attack_config):
        """Test UDP flood attack start and stop."""
        attack = UDPFloodAttack(udp_attack_config)
        
        with patch('socket.socket') as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket
            
            # Start attack
            success = await attack.start()
            assert success is True
            assert attack.socket is not None
            
            # Stop attack
            await attack.stop()
            assert attack.running is False
            mock_socket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_udp_flood_execute_attack(self, udp_attack_config):
        """Test UDP flood attack execution."""
        attack = UDPFloodAttack(udp_attack_config)
        
        # Mock socket
        mock_socket = MagicMock()
        attack.socket = mock_socket
        
        # Mock asyncio executor
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = None
            
            # Execute attack
            await attack.execute_attack()
            
            # Verify socket sendto was called via executor
            mock_loop.run_in_executor.assert_called_once()
            assert attack.bytes_sent > 0
    
    @pytest.mark.asyncio
    async def test_udp_flood_execute_attack_no_socket(self, udp_attack_config):
        """Test UDP flood execution without socket."""
        attack = UDPFloodAttack(udp_attack_config)
        
        # Should raise exception when no socket
        with pytest.raises(Exception, match="UDP socket not initialized"):
            await attack.execute_attack()


class TestAttackManager:
    """Test attack manager functionality."""
    
    def test_attack_manager_initialization(self):
        """Test attack manager initialization."""
        manager = AttackManager()
        
        assert manager.current_attack is None
        assert manager.attack_history == []
    
    def test_create_attack_module_http(self, http_attack_config):
        """Test creating HTTP attack module."""
        manager = AttackManager()
        
        module = manager.create_attack_module(http_attack_config)
        
        assert isinstance(module, HTTPFloodAttack)
        assert module.config == http_attack_config
    
    def test_create_attack_module_tcp(self, tcp_attack_config):
        """Test creating TCP SYN attack module."""
        manager = AttackManager()
        
        module = manager.create_attack_module(tcp_attack_config)
        
        assert isinstance(module, TCPSYNFloodAttack)
        assert module.config == tcp_attack_config
    
    def test_create_attack_module_udp(self, udp_attack_config):
        """Test creating UDP attack module."""
        manager = AttackManager()
        
        module = manager.create_attack_module(udp_attack_config)
        
        assert isinstance(module, UDPFloodAttack)
        assert module.config == udp_attack_config
    
    def test_create_attack_module_unknown_type(self):
        """Test creating attack module with unknown type."""
        manager = AttackManager()
        
        # Create config with invalid attack type
        config = AttackConfig(
            attack_id="test-attack",
            attack_type="unknown_type",  # Invalid type
            target_ip="192.168.1.200",
            target_port=80,
            intensity=10,
            duration=5
        )
        
        module = manager.create_attack_module(config)
        assert module is None
    
    @pytest.mark.asyncio
    async def test_start_attack_success(self, http_attack_config):
        """Test successful attack start."""
        manager = AttackManager()
        
        with patch.object(manager, 'create_attack_module') as mock_create:
            mock_attack = AsyncMock()
            mock_attack.start.return_value = True
            mock_create.return_value = mock_attack
            
            success = await manager.start_attack(http_attack_config)
            
            assert success is True
            assert manager.current_attack == mock_attack
            mock_attack.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_attack_failure(self, http_attack_config):
        """Test attack start failure."""
        manager = AttackManager()
        
        with patch.object(manager, 'create_attack_module') as mock_create:
            mock_attack = AsyncMock()
            mock_attack.start.return_value = False
            mock_create.return_value = mock_attack
            
            success = await manager.start_attack(http_attack_config)
            
            assert success is False
            assert manager.current_attack is None
    
    @pytest.mark.asyncio
    async def test_start_attack_no_module(self, http_attack_config):
        """Test attack start when module creation fails."""
        manager = AttackManager()
        
        with patch.object(manager, 'create_attack_module', return_value=None):
            success = await manager.start_attack(http_attack_config)
            
            assert success is False
            assert manager.current_attack is None
    
    @pytest.mark.asyncio
    async def test_stop_attack_success(self, http_attack_config):
        """Test successful attack stop."""
        manager = AttackManager()
        
        # Set up current attack
        mock_attack = AsyncMock()
        mock_attack.get_statistics.return_value = {"test": "stats"}
        mock_attack.stop = AsyncMock()
        manager.current_attack = mock_attack
        
        success = await manager.stop_attack()
        
        assert success is True
        assert manager.current_attack is None
        assert len(manager.attack_history) == 1
        mock_attack.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_attack_no_current(self):
        """Test stop attack when no current attack."""
        manager = AttackManager()
        
        success = await manager.stop_attack()
        
        assert success is False
    
    def test_get_attack_status_with_attack(self):
        """Test getting attack status with active attack."""
        manager = AttackManager()
        
        # Mock current attack
        mock_attack = MagicMock()
        mock_attack.get_statistics.return_value = {"running": True, "requests_sent": 100}
        manager.current_attack = mock_attack
        
        with patch('bot_client.attack_modules.get_system_metrics') as mock_metrics:
            mock_metrics.return_value = {"cpu_percent": 50.0, "memory_percent": 60.0}
            
            status = manager.get_attack_status()
            
            assert status["running"] is True
            assert status["requests_sent"] == 100
            assert "system_metrics" in status
    
    def test_get_attack_status_no_attack(self):
        """Test getting attack status with no active attack."""
        manager = AttackManager()
        
        status = manager.get_attack_status()
        
        assert status["running"] is False
        assert "No active attack" in status["message"]
    
    def test_get_attack_history(self):
        """Test getting attack history."""
        manager = AttackManager()
        
        # Add some history
        manager.attack_history = [
            {"attack_id": "1", "requests_sent": 100},
            {"attack_id": "2", "requests_sent": 200},
            {"attack_id": "3", "requests_sent": 300}
        ]
        
        # Get limited history
        history = manager.get_attack_history(2)
        
        assert len(history) == 2
        assert history[0]["attack_id"] == "2"
        assert history[1]["attack_id"] == "3"
    
    @pytest.mark.asyncio
    async def test_emergency_stop(self):
        """Test emergency stop functionality."""
        manager = AttackManager()
        
        # Set up current attack
        mock_attack = AsyncMock()
        manager.current_attack = mock_attack
        
        await manager.emergency_stop()
        
        assert manager.current_attack is None
        mock_attack.stop.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])