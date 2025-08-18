"""
Unit tests for network safety validation.
"""
import pytest
from unittest.mock import patch, MagicMock

from shared.config import NetworkConfig, SafetyConfig
from shared.models import AttackConfig, AttackType
from bot_client.safety_validator import SafetyValidator


@pytest.fixture
def network_config():
    """Test network configuration."""
    config = NetworkConfig()
    config.allowed_networks = ["192.168.0.0/16", "10.0.0.0/8"]
    config.blocked_networks = ["127.0.0.0/8", "169.254.0.0/16", "224.0.0.0/4"]
    return config


@pytest.fixture
def safety_config():
    """Test safety configuration."""
    config = SafetyConfig()
    config.max_cpu_usage = 80.0
    config.max_memory_usage = 80.0
    config.emergency_stop_cpu = 95.0
    config.emergency_stop_memory = 95.0
    config.max_requests_per_second_per_bot = 100
    config.max_attack_duration = 300
    return config


@pytest.fixture
def safety_validator(network_config, safety_config):
    """Safety validator instance for testing."""
    return SafetyValidator(network_config, safety_config)


@pytest.fixture
def valid_attack_config():
    """Valid attack configuration for testing."""
    return AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="192.168.1.100",
        target_port=80,
        intensity=50,
        duration=60
    )


def test_safety_validator_initialization(safety_validator):
    """Test safety validator initialization."""
    assert safety_validator.network_config is not None
    assert safety_validator.safety_config is not None
    assert safety_validator.safety_violations == []
    assert safety_validator.last_safety_check is None


def test_validate_attack_target_valid(safety_validator, valid_attack_config):
    """Test validation of valid attack target."""
    is_valid, reason = safety_validator.validate_attack_target(valid_attack_config)
    
    assert is_valid is True
    assert "successful" in reason.lower()


def test_validate_attack_target_invalid_ip_format(safety_validator):
    """Test validation with invalid IP format."""
    invalid_config = AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="invalid.ip.address",
        target_port=80,
        intensity=50,
        duration=60
    )
    
    is_valid, reason = safety_validator.validate_attack_target(invalid_config)
    
    assert is_valid is False
    assert "invalid ip address format" in reason.lower()


def test_validate_attack_target_blocked_ip(safety_validator):
    """Test validation with blocked IP address."""
    blocked_config = AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="127.0.0.1",  # Loopback - blocked
        target_port=80,
        intensity=50,
        duration=60
    )
    
    is_valid, reason = safety_validator.validate_attack_target(blocked_config)
    
    assert is_valid is False
    assert "not in allowed networks" in reason.lower()


def test_validate_attack_target_invalid_port(safety_validator, valid_attack_config):
    """Test validation with invalid port number."""
    valid_attack_config.target_port = 70000  # Invalid port
    
    is_valid, reason = safety_validator.validate_attack_target(valid_attack_config)
    
    assert is_valid is False
    assert "invalid port number" in reason.lower()


def test_validate_attack_target_excessive_intensity(safety_validator, valid_attack_config):
    """Test validation with excessive attack intensity."""
    valid_attack_config.intensity = 1000  # Exceeds limit
    
    is_valid, reason = safety_validator.validate_attack_target(valid_attack_config)
    
    assert is_valid is False
    assert "intensity" in reason.lower() and "exceeds" in reason.lower()


def test_validate_attack_target_excessive_duration(safety_validator, valid_attack_config):
    """Test validation with excessive attack duration."""
    valid_attack_config.duration = 1000  # Exceeds limit
    
    is_valid, reason = safety_validator.validate_attack_target(valid_attack_config)
    
    assert is_valid is False
    assert "duration" in reason.lower() and "exceeds" in reason.lower()


@patch('bot_client.safety_validator.get_system_metrics')
def test_check_system_safety_normal(mock_get_metrics, safety_validator):
    """Test system safety check under normal conditions."""
    # Mock normal system metrics
    mock_get_metrics.return_value = {
        "cpu_percent": 30.0,
        "memory_percent": 40.0,
        "disk_percent": 50.0
    }
    
    is_safe, status = safety_validator.check_system_safety()
    
    assert is_safe is True
    assert status["is_safe"] is True
    assert len(status["violations"]) == 0


@patch('bot_client.safety_validator.get_system_metrics')
def test_check_system_safety_warning_levels(mock_get_metrics, safety_validator):
    """Test system safety check with warning levels."""
    # Mock high but not critical system metrics
    mock_get_metrics.return_value = {
        "cpu_percent": 85.0,  # Above warning threshold
        "memory_percent": 85.0,  # Above warning threshold
        "disk_percent": 50.0
    }
    
    is_safe, status = safety_validator.check_system_safety()
    
    assert is_safe is True  # Still safe, just warnings
    assert status["is_safe"] is True
    assert len(status["violations"]) == 2  # CPU and memory warnings
    
    # Check violation types
    violation_types = [v["type"] for v in status["violations"]]
    assert "cpu_warning" in violation_types
    assert "memory_warning" in violation_types


@patch('bot_client.safety_validator.get_system_metrics')
def test_check_system_safety_emergency_levels(mock_get_metrics, safety_validator):
    """Test system safety check with emergency levels."""
    # Mock critical system metrics
    mock_get_metrics.return_value = {
        "cpu_percent": 98.0,  # Above emergency threshold
        "memory_percent": 97.0,  # Above emergency threshold
        "disk_percent": 96.0  # Above disk emergency threshold
    }
    
    is_safe, status = safety_validator.check_system_safety()
    
    assert is_safe is False  # Not safe due to emergency levels
    assert status["is_safe"] is False
    assert len(status["violations"]) == 3  # CPU, memory, and disk emergencies
    
    # Check violation types
    violation_types = [v["type"] for v in status["violations"]]
    assert "cpu_emergency" in violation_types
    assert "memory_emergency" in violation_types
    assert "disk_emergency" in violation_types


def test_is_dangerous_ip(safety_validator):
    """Test dangerous IP detection."""
    # Test blocked IPs
    assert safety_validator._is_dangerous_ip("127.0.0.1") is True  # Loopback
    assert safety_validator._is_dangerous_ip("169.254.1.1") is True  # Link-local
    assert safety_validator._is_dangerous_ip("224.0.0.1") is True  # Multicast
    assert safety_validator._is_dangerous_ip("255.255.255.255") is True  # Broadcast
    
    # Test allowed IPs
    assert safety_validator._is_dangerous_ip("192.168.1.100") is False
    assert safety_validator._is_dangerous_ip("10.0.0.1") is False


def test_is_dangerous_port(safety_validator):
    """Test dangerous port detection."""
    # Test dangerous ports
    assert safety_validator._is_dangerous_port(22) is True  # SSH
    assert safety_validator._is_dangerous_port(3389) is True  # RDP
    assert safety_validator._is_dangerous_port(3306) is True  # MySQL
    assert safety_validator._is_dangerous_port(500) is True  # System port < 1024
    
    # Test safe ports
    assert safety_validator._is_dangerous_port(80) is False  # HTTP
    assert safety_validator._is_dangerous_port(443) is False  # HTTPS
    assert safety_validator._is_dangerous_port(8080) is False  # Alt HTTP
    assert safety_validator._is_dangerous_port(9000) is False  # High port


@patch('bot_client.safety_validator.get_network_interfaces')
def test_validate_network_interfaces_valid(mock_get_interfaces, safety_validator):
    """Test network interface validation with valid interfaces."""
    # Mock valid network interfaces
    mock_get_interfaces.return_value = [
        {
            "name": "eth0",
            "addresses": [
                {
                    "family": "IPv4",
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "broadcast": "192.168.1.255"
                }
            ]
        }
    ]
    
    is_valid, interfaces_info = safety_validator.validate_network_interfaces()
    
    assert is_valid is True
    assert len(interfaces_info) == 1
    assert interfaces_info[0]["name"] == "eth0"
    assert interfaces_info[0]["is_valid"] is True
    assert len(interfaces_info[0]["warnings"]) == 0


@patch('bot_client.safety_validator.get_network_interfaces')
def test_validate_network_interfaces_invalid(mock_get_interfaces, safety_validator):
    """Test network interface validation with invalid interfaces."""
    # Mock invalid network interfaces
    mock_get_interfaces.return_value = [
        {
            "name": "lo",
            "addresses": [
                {
                    "family": "IPv4",
                    "address": "127.0.0.1",  # Blocked IP
                    "netmask": "255.0.0.0",
                    "broadcast": None
                }
            ]
        }
    ]
    
    is_valid, interfaces_info = safety_validator.validate_network_interfaces()
    
    assert is_valid is False
    assert len(interfaces_info) == 1
    assert interfaces_info[0]["name"] == "lo"
    assert interfaces_info[0]["is_valid"] is False
    assert len(interfaces_info[0]["warnings"]) > 0


def test_attack_type_specific_validation_http_flood(safety_validator):
    """Test attack type specific validation for HTTP flood."""
    # Valid HTTP flood
    http_config = AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.HTTP_FLOOD,
        target_ip="192.168.1.100",
        target_port=80,  # Appropriate for HTTP
        intensity=50,
        duration=60
    )
    
    is_valid, reason = safety_validator._validate_attack_type_specific(http_config)
    assert is_valid is True
    
    # HTTP flood on inappropriate port
    http_config.target_port = 22  # SSH port
    is_valid, reason = safety_validator._validate_attack_type_specific(http_config)
    assert is_valid is False
    assert "not be appropriate" in reason


def test_attack_type_specific_validation_tcp_syn(safety_validator):
    """Test attack type specific validation for TCP SYN flood."""
    # Valid TCP SYN flood
    tcp_config = AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.TCP_SYN,
        target_ip="192.168.1.100",
        target_port=80,
        intensity=30,  # Lower intensity for SYN flood
        duration=60
    )
    
    is_valid, reason = safety_validator._validate_attack_type_specific(tcp_config)
    assert is_valid is True
    
    # TCP SYN flood with excessive intensity
    tcp_config.intensity = 100  # Too high for SYN flood
    is_valid, reason = safety_validator._validate_attack_type_specific(tcp_config)
    assert is_valid is False
    assert "too high" in reason


def test_attack_type_specific_validation_udp_flood(safety_validator):
    """Test attack type specific validation for UDP flood."""
    # Valid UDP flood
    udp_config = AttackConfig(
        attack_id="test-attack",
        attack_type=AttackType.UDP_FLOOD,
        target_ip="192.168.1.100",
        target_port=9999,  # Safe UDP port
        intensity=50,
        duration=60
    )
    
    is_valid, reason = safety_validator._validate_attack_type_specific(udp_config)
    assert is_valid is True
    
    # UDP flood on dangerous port (DNS)
    udp_config.target_port = 53  # DNS port - amplification risk
    is_valid, reason = safety_validator._validate_attack_type_specific(udp_config)
    assert is_valid is False
    assert "amplification" in reason


@patch('bot_client.safety_validator.get_system_metrics')
@patch('bot_client.safety_validator.get_network_interfaces')
def test_validate_before_attack_comprehensive(mock_get_interfaces, mock_get_metrics, safety_validator, valid_attack_config):
    """Test comprehensive pre-attack validation."""
    # Mock normal system conditions
    mock_get_metrics.return_value = {
        "cpu_percent": 30.0,
        "memory_percent": 40.0,
        "disk_percent": 50.0
    }
    
    mock_get_interfaces.return_value = [
        {
            "name": "eth0",
            "addresses": [
                {
                    "family": "IPv4",
                    "address": "192.168.1.50",
                    "netmask": "255.255.255.0",
                    "broadcast": "192.168.1.255"
                }
            ]
        }
    ]
    
    is_valid, report = safety_validator.validate_before_attack(valid_attack_config)
    
    assert is_valid is True
    assert report["is_valid"] is True
    assert len(report["errors"]) == 0
    assert "target_validation" in report["checks"]
    assert "system_safety" in report["checks"]
    assert "network_interfaces" in report["checks"]


def test_safety_violations_tracking(safety_validator):
    """Test safety violations tracking."""
    # Initially no violations
    assert len(safety_validator.get_safety_violations()) == 0
    
    # Mock a system check that generates violations
    with patch('bot_client.safety_validator.get_system_metrics') as mock_metrics:
        mock_metrics.return_value = {
            "cpu_percent": 85.0,  # Warning level
            "memory_percent": 40.0,
            "disk_percent": 50.0
        }
        
        is_safe, status = safety_validator.check_system_safety()
        
        # Should have violations now
        violations = safety_validator.get_safety_violations()
        assert len(violations) == 1
        assert violations[0]["type"] == "cpu_warning"
    
    # Clear violations
    safety_validator.clear_safety_violations()
    assert len(safety_validator.get_safety_violations()) == 0


if __name__ == "__main__":
    pytest.main([__file__])