"""
Network safety validation for bot clients.
"""
import ipaddress
import logging
import psutil
import socket
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from shared.config import NetworkConfig, SafetyConfig
from shared.models import AttackConfig
from shared.utils import get_network_interfaces, get_system_metrics


class SafetyValidator:
    """Validates network operations and system safety for bot clients."""
    
    def __init__(self, network_config: NetworkConfig, safety_config: SafetyConfig):
        self.network_config = network_config
        self.safety_config = safety_config
        self.logger = logging.getLogger(__name__)
        
        # Cache network interfaces
        self._network_interfaces: Optional[List[Dict[str, Any]]] = None
        self._last_interface_check: Optional[datetime] = None
        
        # Safety violation tracking
        self.safety_violations: List[Dict[str, Any]] = []
        self.last_safety_check: Optional[datetime] = None
        
        self.logger.info("Safety validator initialized")
    
    def validate_attack_target(self, attack_config: AttackConfig) -> Tuple[bool, str]:
        """
        Validate that an attack target is safe and allowed.
        Returns (is_valid, reason).
        """
        try:
            target_ip = attack_config.target_ip
            target_port = attack_config.target_port
            
            # Basic IP format validation
            try:
                ip_obj = ipaddress.ip_address(target_ip)
            except ValueError:
                return False, f"Invalid IP address format: {target_ip}"
            
            # Check if IP is in allowed networks
            if not self.network_config.is_ip_allowed(target_ip):
                return False, f"Target IP {target_ip} is not in allowed networks"
            
            # Check for blocked/dangerous IPs
            if self._is_dangerous_ip(target_ip):
                return False, f"Target IP {target_ip} is in blocked/dangerous range"
            
            # Validate port range
            if not (1 <= target_port <= 65535):
                return False, f"Invalid port number: {target_port}"
            
            # Check for dangerous ports
            if self._is_dangerous_port(target_port):
                return False, f"Target port {target_port} is considered dangerous"
            
            # Validate attack intensity
            if attack_config.intensity > self.safety_config.max_requests_per_second_per_bot:
                return False, f"Attack intensity {attack_config.intensity} exceeds safety limit"
            
            # Validate attack duration
            if attack_config.duration > self.safety_config.max_attack_duration:
                return False, f"Attack duration {attack_config.duration} exceeds safety limit"
            
            # Check if target is on same machine (prevent self-attack)
            if self._is_local_ip(target_ip):
                return False, "Cannot attack local machine"
            
            # Additional safety checks based on attack type
            type_check_result = self._validate_attack_type_specific(attack_config)
            if not type_check_result[0]:
                return type_check_result
            
            self.logger.info(f"Attack target validation passed: {target_ip}:{target_port}")
            return True, "Target validation successful"
        
        except Exception as e:
            self.logger.error(f"Error validating attack target: {e}")
            return False, f"Validation error: {str(e)}"
    
    def check_system_safety(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check current system safety status.
        Returns (is_safe, metrics).
        """
        try:
            metrics = get_system_metrics()
            self.last_safety_check = datetime.now()
            
            safety_status = {
                "is_safe": True,
                "violations": [],
                "metrics": metrics,
                "timestamp": self.last_safety_check.isoformat()
            }
            
            # Check CPU usage
            cpu_percent = metrics.get("cpu_percent", 0.0)
            if cpu_percent > self.safety_config.emergency_stop_cpu:
                safety_status["is_safe"] = False
                safety_status["violations"].append({
                    "type": "cpu_emergency",
                    "value": cpu_percent,
                    "threshold": self.safety_config.emergency_stop_cpu,
                    "message": f"CPU usage {cpu_percent}% exceeds emergency threshold"
                })
            elif cpu_percent > self.safety_config.max_cpu_usage:
                safety_status["violations"].append({
                    "type": "cpu_warning",
                    "value": cpu_percent,
                    "threshold": self.safety_config.max_cpu_usage,
                    "message": f"CPU usage {cpu_percent}% exceeds warning threshold"
                })
            
            # Check memory usage
            memory_percent = metrics.get("memory_percent", 0.0)
            if memory_percent > self.safety_config.emergency_stop_memory:
                safety_status["is_safe"] = False
                safety_status["violations"].append({
                    "type": "memory_emergency",
                    "value": memory_percent,
                    "threshold": self.safety_config.emergency_stop_memory,
                    "message": f"Memory usage {memory_percent}% exceeds emergency threshold"
                })
            elif memory_percent > self.safety_config.max_memory_usage:
                safety_status["violations"].append({
                    "type": "memory_warning",
                    "value": memory_percent,
                    "threshold": self.safety_config.max_memory_usage,
                    "message": f"Memory usage {memory_percent}% exceeds warning threshold"
                })
            
            # Check disk usage
            disk_percent = metrics.get("disk_percent", 0.0)
            if disk_percent > 95.0:  # Hard limit for disk
                safety_status["is_safe"] = False
                safety_status["violations"].append({
                    "type": "disk_emergency",
                    "value": disk_percent,
                    "threshold": 95.0,
                    "message": f"Disk usage {disk_percent}% is critically high"
                })
            
            # Log violations
            if safety_status["violations"]:
                for violation in safety_status["violations"]:
                    self.safety_violations.append({
                        **violation,
                        "timestamp": self.last_safety_check.isoformat()
                    })
                    
                    if violation["type"].endswith("_emergency"):
                        self.logger.critical(violation["message"])
                    else:
                        self.logger.warning(violation["message"])
            
            return safety_status["is_safe"], safety_status
        
        except Exception as e:
            self.logger.error(f"Error checking system safety: {e}")
            return False, {
                "is_safe": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def validate_network_interfaces(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate network interfaces and check for safety.
        Returns (is_valid, interfaces_info).
        """
        try:
            # Refresh interface cache if needed
            now = datetime.now()
            if (not self._network_interfaces or 
                not self._last_interface_check or 
                (now - self._last_interface_check).seconds > 60):
                
                self._network_interfaces = get_network_interfaces()
                self._last_interface_check = now
            
            interfaces_info = []
            all_valid = True
            
            for interface in self._network_interfaces:
                interface_info = {
                    "name": interface["name"],
                    "addresses": interface["addresses"],
                    "is_valid": True,
                    "warnings": []
                }
                
                # Check each address
                for addr_info in interface["addresses"]:
                    if addr_info["family"] == "IPv4":
                        ip = addr_info["address"]
                        
                        # Check if IP is in allowed networks
                        if not self.network_config.is_ip_allowed(ip):
                            interface_info["is_valid"] = False
                            interface_info["warnings"].append(
                                f"IP {ip} is not in allowed networks"
                            )
                            all_valid = False
                        
                        # Check for dangerous IPs
                        if self._is_dangerous_ip(ip):
                            interface_info["warnings"].append(
                                f"IP {ip} is in a dangerous range"
                            )
                
                interfaces_info.append(interface_info)
            
            return all_valid, interfaces_info
        
        except Exception as e:
            self.logger.error(f"Error validating network interfaces: {e}")
            return False, [{"error": str(e)}]
    
    def get_allowed_target_networks(self) -> List[str]:
        """Get list of allowed target networks for attacks."""
        return self.network_config.allowed_networks.copy()
    
    def get_blocked_networks(self) -> List[str]:
        """Get list of blocked networks."""
        return self.network_config.blocked_networks.copy()
    
    def get_safety_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent safety violations."""
        return self.safety_violations[-limit:] if self.safety_violations else []
    
    def clear_safety_violations(self):
        """Clear safety violation history."""
        self.safety_violations.clear()
        self.logger.info("Safety violation history cleared")
    
    def _is_dangerous_ip(self, ip: str) -> bool:
        """Check if an IP address is in a dangerous range."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Check against blocked networks
            for blocked_network in self.network_config.blocked_networks:
                if ip_obj in ipaddress.ip_network(blocked_network, strict=False):
                    return True
            
            # Additional dangerous IP checks
            dangerous_ranges = [
                "0.0.0.0/8",        # "This" network
                "127.0.0.0/8",      # Loopback
                "169.254.0.0/16",   # Link-local
                "224.0.0.0/4",      # Multicast
                "240.0.0.0/4",      # Reserved
                "255.255.255.255/32" # Broadcast
            ]
            
            for dangerous_range in dangerous_ranges:
                if ip_obj in ipaddress.ip_network(dangerous_range, strict=False):
                    return True
            
            return False
        
        except Exception:
            # If we can't parse the IP, consider it dangerous
            return True
    
    def _is_dangerous_port(self, port: int) -> bool:
        """Check if a port is considered dangerous to attack."""
        # System/privileged ports that should generally not be attacked
        dangerous_ports = {
            22,    # SSH
            23,    # Telnet
            25,    # SMTP
            53,    # DNS
            110,   # POP3
            143,   # IMAP
            993,   # IMAPS
            995,   # POP3S
            465,   # SMTPS
            587,   # SMTP submission
            3389,  # RDP
            5432,  # PostgreSQL
            3306,  # MySQL
            1433,  # SQL Server
            5984,  # CouchDB
            6379,  # Redis
            27017, # MongoDB
            9200,  # Elasticsearch
            5601,  # Kibana
        }
        
        # Don't attack well-known system ports below 1024 unless specifically allowed
        if port < 1024 and port not in {80, 443, 8080, 8443}:
            return True
        
        return port in dangerous_ports
    
    def _is_local_ip(self, ip: str) -> bool:
        """Check if an IP address is local to this machine."""
        try:
            # Get all local IP addresses
            local_ips = set()
            
            # Add loopback
            local_ips.add("127.0.0.1")
            local_ips.add("::1")
            
            # Add all interface IPs
            if self._network_interfaces:
                for interface in self._network_interfaces:
                    for addr_info in interface["addresses"]:
                        if addr_info["family"] == "IPv4":
                            local_ips.add(addr_info["address"])
            
            return ip in local_ips
        
        except Exception as e:
            self.logger.error(f"Error checking if IP is local: {e}")
            # If we can't determine, assume it's local for safety
            return True
    
    def _validate_attack_type_specific(self, attack_config: AttackConfig) -> Tuple[bool, str]:
        """Perform attack-type-specific validation."""
        try:
            attack_type = attack_config.attack_type
            target_port = attack_config.target_port
            
            # HTTP flood specific checks
            if attack_type.value == "http_flood":
                if target_port not in {80, 443, 8080, 8443, 8000, 3000, 5000}:
                    return False, f"HTTP flood on port {target_port} may not be appropriate"
            
            # TCP SYN flood specific checks
            elif attack_type.value == "tcp_syn":
                # TCP SYN floods can be more dangerous, add extra checks
                if attack_config.intensity > 50:  # Lower limit for SYN floods
                    return False, f"TCP SYN flood intensity {attack_config.intensity} is too high"
            
            # UDP flood specific checks
            elif attack_type.value == "udp_flood":
                # Check for dangerous UDP ports
                dangerous_udp_ports = {53, 123, 161, 1900, 5353}
                if target_port in dangerous_udp_ports:
                    return False, f"UDP flood on port {target_port} could cause amplification attacks"
            
            return True, "Attack type validation passed"
        
        except Exception as e:
            self.logger.error(f"Error in attack type validation: {e}")
            return False, f"Attack type validation error: {str(e)}"
    
    def validate_before_attack(self, attack_config: AttackConfig) -> Tuple[bool, Dict[str, Any]]:
        """
        Comprehensive validation before starting an attack.
        Returns (is_valid, validation_report).
        """
        validation_report = {
            "is_valid": True,
            "checks": {},
            "warnings": [],
            "errors": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 1. Validate attack target
            target_valid, target_reason = self.validate_attack_target(attack_config)
            validation_report["checks"]["target_validation"] = {
                "passed": target_valid,
                "reason": target_reason
            }
            
            if not target_valid:
                validation_report["is_valid"] = False
                validation_report["errors"].append(f"Target validation failed: {target_reason}")
            
            # 2. Check system safety
            system_safe, system_status = self.check_system_safety()
            validation_report["checks"]["system_safety"] = system_status
            
            if not system_safe:
                validation_report["is_valid"] = False
                validation_report["errors"].append("System safety check failed")
            
            # Add warnings for non-critical violations
            for violation in system_status.get("violations", []):
                if violation["type"].endswith("_warning"):
                    validation_report["warnings"].append(violation["message"])
            
            # 3. Validate network interfaces
            interfaces_valid, interfaces_info = self.validate_network_interfaces()
            validation_report["checks"]["network_interfaces"] = {
                "passed": interfaces_valid,
                "interfaces": interfaces_info
            }
            
            if not interfaces_valid:
                validation_report["warnings"].append("Some network interfaces have issues")
            
            # 4. Final safety assessment
            if validation_report["is_valid"]:
                self.logger.info(f"Pre-attack validation passed for {attack_config.target_ip}:{attack_config.target_port}")
            else:
                self.logger.error(f"Pre-attack validation failed: {validation_report['errors']}")
            
            return validation_report["is_valid"], validation_report
        
        except Exception as e:
            self.logger.error(f"Error in pre-attack validation: {e}")
            validation_report["is_valid"] = False
            validation_report["errors"].append(f"Validation error: {str(e)}")
            return False, validation_report