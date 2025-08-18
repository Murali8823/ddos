@echo off
REM DDoS Simulation Lab - Git Setup and Push Script (Windows)
REM This script initializes the Git repository and pushes to GitHub

echo 🚀 DDoS Simulation Lab - Git Setup
echo ==================================

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git is not installed. Please install Git first.
    echo Download from: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Initialize git repository if not already initialized
if not exist ".git" (
    echo 📁 Initializing Git repository...
    git init
) else (
    echo 📁 Git repository already initialized
)

REM Configure git user
echo 👤 Configuring Git user...
git config user.name "Murali8823"
git config user.email "murali8823@users.noreply.github.com"

REM Add remote origin
echo 🔗 Adding remote origin...
git remote remove origin 2>nul
git remote add origin https://github.com/Murali8823/ddos.git

REM Create and switch to main branch
echo 🌿 Setting up main branch...
git branch -M main

REM Add all files to staging
echo 📦 Adding files to staging...
git add .

REM Check what will be committed
echo 📋 Files to be committed:
git status --short

REM Create initial commit
echo 💾 Creating initial commit...
git commit -m "feat: initial release of DDoS Simulation Lab v1.0.0

🎯 Complete educational DDoS simulation framework featuring:

✨ Features:
- FastAPI-based C2 server with WebSocket communication
- 28 Linux bot clients with multiple attack types
- HTTP flood, TCP SYN flood, and UDP flood attacks
- Comprehensive safety mechanisms and network validation
- Real-time monitoring and educational analytics
- Automated deployment scripts for complete lab setup

🛡️ Safety Features:
- Network boundary checking and IP validation
- Resource monitoring with emergency stop capabilities
- Rate limiting and safety thresholds
- Comprehensive audit logging and analysis

📚 Educational Value:
- Complete deployment guides and documentation
- Step-by-step setup instructions
- Troubleshooting guides and best practices
- Technology stack documentation
- Hands-on cybersecurity learning platform

🔧 Technical Stack:
- Python 3.8+ with asyncio for high concurrency
- FastAPI for REST API and WebSocket endpoints
- SQLite database with SQLAlchemy ORM
- Raw sockets for low-level packet crafting
- Comprehensive testing suite with pytest

📁 Project Structure:
- c2_server/: Command & control server implementation
- bot_client/: Linux bot client with attack modules
- shared/: Common models, config, and utilities
- tests/: Comprehensive unit and integration tests
- deployment/: Complete setup and operation guides

⚠️ Educational Use Only:
This software is designed exclusively for educational purposes
in controlled laboratory environments. Includes comprehensive
safety mechanisms and ethical use guidelines.

🎓 Perfect for:
- Cybersecurity education and training
- Network security research and analysis
- Hands-on DDoS attack and defense learning
- Academic cybersecurity curriculum

Co-authored-by: AI Assistant <assistant@kiro.ai>"

REM Push to GitHub
echo 🚀 Pushing to GitHub...
git push -u origin main

if errorlevel 1 (
    echo ❌ Push failed. Please check your GitHub credentials and try again.
    echo You may need to:
    echo 1. Set up GitHub authentication (Personal Access Token)
    echo 2. Configure Git credentials
    echo 3. Check repository permissions
    pause
    exit /b 1
)

echo.
echo ✅ Successfully pushed DDoS Simulation Lab to GitHub!
echo 🔗 Repository URL: https://github.com/Murali8823/ddos
echo.
echo 📋 Next Steps:
echo 1. Visit the repository on GitHub
echo 2. Review the README.md for setup instructions
echo 3. Check the deployment/ folder for detailed guides
echo 4. Start with deployment/01_windows_setup.md
echo.
echo 🛡️ Remember: Use responsibly for educational purposes only!
echo.
pause