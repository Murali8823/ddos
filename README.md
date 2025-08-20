<div align="center">

```
██████╗ ██████╗  ██████╗ ███████╗    ██████╗ ██╗   ██╗    ███╗   ███╗██╗   ██╗██████╗  █████╗ ██╗     ██╗
██╔══██╗██╔══██╗██╔═══██╗██╔════╝    ██╔══██╗╚██╗ ██╔╝    ████╗ ████║██║   ██║██╔══██╗██╔══██╗██║     ██║
██║  ██║██║  ██║██║   ██║███████╗    ██████╔╝ ╚████╔╝     ██╔████╔██║██║   ██║██████╔╝███████║██║     ██║
██║  ██║██║  ██║██║   ██║╚════██║    ██╔══██╗  ╚██╔╝      ██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║██║     ██║
██████╔╝██████╔╝╚██████╔╝███████║    ██████╔╝   ██║       ██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║███████╗██║
╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝    ╚═════╝    ╚═╝       ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝
```

<h1>🛡️ DDoS Simulation Lab 🛡️</h1>
<h3>🎯 Advanced Educational Cybersecurity Framework 🎯</h3>
<h4>💻 Created by <strong>Murali</strong> 💻</h4>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Educational Use](https://img.shields.io/badge/use-educational-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![Author](https://img.shields.io/badge/Author-Murali8823-red.svg)](https://github.com/Murali8823)
[![GitHub](https://img.shields.io/badge/GitHub-Murali8823/ddos-black.svg)](https://github.com/Murali8823/ddos)

</div>

An advanced educational DDoS simulation framework designed for cybersecurity training in controlled laboratory environments. This project provides hands-on experience with distributed denial-of-service attacks, network security concepts, and defensive strategies.

## 🎯 Overview

The DDoS Simulation Lab is a comprehensive educational platform that simulates realistic DDoS attacks in a safe, controlled environment. It consists of a command & control (C2) server, multiple bot clients, and monitoring tools that work together to demonstrate attack coordination, impact assessment, and defensive measures.

### Key Features

- 🐳 **Docker-Ready Deployment**: One-click setup with containerized architecture
- 🎮 **Complete C2 Infrastructure**: Professional-grade command and control system
- 🤖 **Scalable Bot Network**: 3 to 100+ bots with easy scaling commands
- 🛡️ **Built-in Safety Controls**: Multiple layers of protection and monitoring
- 📊 **Real-time Analytics**: Live attack monitoring and performance metrics
- 📚 **Educational Focus**: Designed specifically for learning and research
- ⚡ **High Performance**: Capable of generating significant attack traffic
- 🖥️ **Windows Optimized**: Perfect for Windows development environments

## 🚀 Quick Start - Docker Deployment (Recommended)

### 🐳 **One-Click Setup for Windows**
**The easiest way to get started - everything pre-configured!**

```cmd
# 1. Clone the repository
git clone https://github.com/Murali8823/ddos.git
cd ddos

# 2. Launch interactive menu (easiest option)
docker-scripts\quick-start.bat
```

**Or use direct commands:**
```cmd
# Build Docker images
docker-scripts\build.bat

# Choose your deployment:
docker-scripts\run-basic.bat      # 🎮 Basic Lab (3 bots) - Perfect for learning
docker-scripts\run-scaled.bat     # 🚀 Full Scale (28 bots) - Realistic simulation

# Scale to any number of bots
docker-scripts\scale-bots.bat 50  # Deploy 50 bots

# Monitor in real-time
docker-scripts\monitor.bat live   # Live dashboard

# Clean up everything
docker-scripts\cleanup.bat        # Remove all containers
```

### 🎯 **Access Your Lab**
Once deployed, access these URLs:
- **🌐 C2 Dashboard**: http://localhost:8080
- **🎯 Target Server**: http://localhost:8090
- **📊 Real-time Monitoring**: Built into dashboard

### ✅ **Docker Benefits**
- 🎯 **Zero Configuration**: Everything pre-configured and ready
- 🔒 **Safe Environment**: Isolated Docker containers
- ⚖️ **Easy Scaling**: 3 to 100+ bots with one command
- 🧹 **Clean Removal**: Remove everything instantly
- 🖥️ **Windows Optimized**: Perfect for Windows development
- 📦 **No Dependencies**: No need to install Python, databases, etc.

### 🖥️ **Alternative: Manual Installation**
**For advanced users who want full control**

```bash
# Traditional setup (requires more configuration)
git clone https://github.com/Murali8823/ddos.git
cd ddos
pip install -r requirements.txt
python -m c2_server.main
python -m bot_client.main
```

📚 **See [Docker Deployment Guide](deployment/08_docker_deployment.md) for detailed instructions**

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Lab Network (Isolated)"
        C2[C2 Server<br/>FastAPI + WebSocket]
        T[Windows Target<br/>IIS/Apache]
        
        subgraph "Bot Network"
            B1[Linux Bot 1]
            B2[Linux Bot 2]
            B3[Linux Bot 3]
            BN[... Bot 28]
        end
        
        D[Dashboard<br/>Web Interface]
    end
    
    D --> C2
    C2 -.-> B1
    C2 -.-> B2
    C2 -.-> B3
    C2 -.-> BN
    
    B1 --> T
    B2 --> T
    B3 --> T
    BN --> T
    
    style C2 fill:#e1f5fe
    style T fill:#ffebee
    style D fill:#f3e5f5
```

## 📋 Prerequisites

### 🐳 **For Docker Deployment (Recommended)**
- **Windows 10/11** (Pro, Enterprise, or Education)
- **Docker Desktop** with WSL2 backend
- **8GB RAM minimum** (16GB recommended for full scale)
- **Git** for cloning the repository

### 🖥️ **For Manual Deployment (Advanced)**
- **Development Machine**: Windows 10/11 with Python 3.8+
- **C2 Server**: Linux server (Ubuntu/Debian/CentOS)
- **Bot Clients**: 28 Linux machines
- **Target System**: Windows machine with web server
- **Network**: Isolated lab network (recommended)

## 🎮 Deployment Options

### 🐳 **Option 1: Docker Deployment (Recommended)**
**Perfect for Windows users - everything containerized and isolated**

```cmd
# Quick interactive setup
docker-scripts\quick-start.bat

# Or step by step
docker-scripts\build.bat          # Build images
docker-scripts\run-basic.bat      # Deploy 3-bot lab
docker-scripts\run-scaled.bat     # Deploy 28-bot army
```

**📚 Complete Guide**: [Docker Deployment Guide](deployment/08_docker_deployment.md)

### 🖥️ **Option 2: Manual Deployment (Advanced)**
**For users who want full control over the environment**

1. **Setup Infrastructure**
   - 📋 [Windows Setup](deployment/01_windows_setup.md)
   - 🖥️ [C2 Server Setup](deployment/02_c2_server_setup.md)
   - 🤖 [Bot Deployment](deployment/03_bot_deployment.md)
   - 🎯 [Target Setup](deployment/04_windows_victim_setup.md)

2. **Configure and Deploy**
   ```bash
   git clone https://github.com/Murali8823/ddos.git
   cd ddos
   pip install -r requirements.txt
   # Edit config.json to match your network
   python -m c2_server.main
   ```

## 🎮 Attack Capabilities

### Supported Attack Types

| Attack Type | Description | Max Intensity | Educational Value |
|-------------|-------------|---------------|-------------------|
| **HTTP Flood** | Application layer attack targeting web servers | 2,800 req/sec | Web application security |
| **TCP SYN Flood** | Network layer attack exploiting TCP handshake | High volume | Network protocol security |
| **UDP Flood** | Transport layer attack consuming bandwidth | Configurable | Network resource management |

### Attack Execution

**🐳 Docker Deployment:**
```cmd
# Access the web dashboard
# Navigate to: http://localhost:8080
# Use the GUI to start attacks with point-and-click interface

# Or use API commands
curl -X POST http://localhost:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_type": "http_flood",
    "target_ip": "target-server",
    "target_port": 80,
    "intensity": 50,
    "duration": 60
  }'
```

**🖥️ Manual Deployment:**
```bash
# Start HTTP flood attack
curl -X POST http://192.168.1.100:8080/api/attack/start \
  -H "Content-Type: application/json" \
  -d '{
    "attack_type": "http_flood",
    "target_ip": "192.168.1.200",
    "target_port": 80,
    "intensity": 50,
    "duration": 60
  }'

# Monitor attack progress
curl http://192.168.1.100:8080/api/status

# Emergency stop
curl -X POST http://192.168.1.100:8080/api/emergency-stop
```

## 🛡️ Safety Features

### Multi-Layer Protection

- **Network Boundary Validation**: Ensures attacks remain within lab network
- **Resource Monitoring**: Real-time CPU, memory, and network usage tracking
- **Rate Limiting**: Configurable limits per bot and total system
- **Emergency Controls**: Instant attack termination capabilities
- **Audit Logging**: Comprehensive activity logging for analysis

### Safety Configuration

```json
{
  "safety": {
    "max_cpu_usage": 80.0,
    "max_memory_usage": 80.0,
    "max_requests_per_second_per_bot": 100,
    "emergency_stop_cpu": 95.0,
    "max_bots": 28
  }
}
```

## 📊 Monitoring and Analysis

### Real-time Dashboard

- Live attack statistics and bot status
- Resource usage monitoring
- Network traffic analysis
- Performance metrics visualization

### Educational Reports

- Attack pattern analysis
- System impact assessment
- Learning outcome documentation
- Comprehensive data export

## 🎓 Educational Value

### Learning Objectives

- **DDoS Attack Mechanics**: Understanding how distributed attacks work
- **Network Security**: Protocol analysis and vulnerability assessment
- **System Monitoring**: Resource usage and performance impact
- **Defensive Strategies**: Detection and mitigation techniques
- **Incident Response**: Emergency procedures and recovery

### Practical Skills

- Network security assessment
- System administration and monitoring
- Python programming for cybersecurity
- Distributed system architecture
- Attack simulation and analysis

## 🔧 Technology Stack

### Core Technologies

- **Python 3.8+**: Primary programming language
- **FastAPI**: High-performance web framework for C2 server
- **WebSockets**: Real-time bidirectional communication
- **SQLite**: Lightweight database for logging and analysis
- **asyncio**: Asynchronous programming for high concurrency
- **aiohttp**: HTTP client for attack simulation

### Supporting Tools

- **Raw Sockets**: Low-level packet crafting for TCP/UDP attacks
- **psutil**: System resource monitoring
- **Pydantic**: Data validation and serialization
- **pytest**: Comprehensive testing framework

For detailed technology information, see [TECH_STACK.md](TECH_STACK.md).

## 📁 Project Structure

```
ddos-simulation-lab/
├── 📁 c2_server/              # Command & Control server
│   ├── main.py               # FastAPI application
│   ├── bot_manager.py        # Bot connection management
│   ├── command_handler.py    # Command distribution
│   └── database.py           # Data persistence
├── 📁 bot_client/             # Bot client implementation
│   ├── main.py               # Bot client application
│   ├── attack_modules.py     # Attack implementations
│   ├── websocket_client.py   # C2 communication
│   └── safety_validator.py   # Safety mechanisms
├── 📁 shared/                 # Shared components
│   ├── models.py             # Data models
│   ├── config.py             # Configuration management
│   └── utils.py              # Utility functions
├── 📁 docker-scripts/         # 🐳 Docker deployment scripts
│   ├── quick-start.bat       # Interactive deployment menu
│   ├── build.bat             # Build Docker images
│   ├── run-basic.bat         # Deploy 3-bot lab
│   ├── run-scaled.bat        # Deploy 28-bot army
│   ├── scale-bots.bat        # Scale to any number
│   ├── monitor.bat           # Real-time monitoring
│   └── cleanup.bat           # Clean removal
├── 📁 tests/                  # Test suites
├── 📁 deployment/             # Deployment guides
│   ├── 08_docker_deployment.md # 🐳 Docker guide (recommended)
│   ├── 01_windows_setup.md   # Windows preparation
│   ├── 02_c2_server_setup.md # C2 server installation
│   ├── 03_bot_deployment.md  # Bot client deployment
│   ├── 04_windows_victim_setup.md # Target setup
│   ├── 05_attack_execution.md # Attack scenarios
│   ├── 06_monitoring_analysis.md # Analysis tools
│   └── 07_troubleshooting.md # Problem resolution
├── 🐳 Dockerfile.c2           # C2 server container
├── 🐳 Dockerfile.bot          # Bot client container
├── 🐳 docker-compose.yml      # Basic 3-bot setup
├── 🐳 docker-compose.scale.yml # Scalable bot army
├── 📄 config.json            # Main configuration
├── 📄 requirements.txt       # Python dependencies
├── 📄 HOW_IT_WORKS.md        # 🎬 Animated technical guide
└── 📄 README.md              # This file
```

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_attack_modules.py
python -m pytest tests/test_safety_validator.py
python -m pytest tests/test_websocket_client.py

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Coverage

- Unit tests for all attack modules
- Safety mechanism validation
- WebSocket communication testing
- Database operations testing
- Configuration validation testing

## 🤝 Contributing

We welcome contributions from the cybersecurity education community! Areas for contribution:

- 🛡️ Safety mechanism enhancements
- 📚 Educational content and tutorials
- 🔧 New attack type implementations
- 📊 Monitoring and visualization improvements
- 📖 Documentation and guides
- 🐳 Docker deployment improvements

## 📜 License and Ethics

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Ethical Use Requirements

⚠️ **IMPORTANT**: This software is designed exclusively for educational purposes in controlled laboratory environments.

**Permitted Uses:**
- Educational cybersecurity training
- Academic research and study
- Controlled lab demonstrations
- Security awareness training

**Prohibited Uses:**
- Attacks against systems without explicit permission
- Malicious or illegal activities
- Production network testing without authorization
- Any use outside of controlled lab environments

By using this software, you agree to use it responsibly and ethically for educational purposes only.

## 📞 Support and Documentation

### Documentation

- 🐳 [Docker Deployment Guide](deployment/08_docker_deployment.md) **(Recommended)**
- 📋 [Complete Manual Deployment Guide](deployment/)
- 🎬 [How It Works - Animated Guide](HOW_IT_WORKS.md)
- 🔧 [Technology Stack Details](TECH_STACK.md)
- 📝 [Changelog](CHANGELOG.md)

### Getting Help

- 🐛 **Bug Reports**: [Create an issue](https://github.com/Murali8823/ddos/issues)
- 💡 **Feature Requests**: [Submit a feature request](https://github.com/Murali8823/ddos/issues)
- 📚 **Documentation**: Check the deployment guides
- 🔧 **Technical Issues**: Review troubleshooting guide

## 🏆 Acknowledgments

- Cybersecurity education community for inspiration and feedback
- Open source contributors and maintainers
- Educational institutions supporting hands-on security training
- Security researchers promoting ethical hacking education

## 📈 Project Status

- ✅ **Current Version**: 1.0.0
- 🚀 **Status**: Active development
- 🎯 **Focus**: Educational cybersecurity training
- 🔄 **Updates**: Regular improvements and enhancements

---