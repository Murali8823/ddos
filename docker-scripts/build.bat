@echo off
REM 🐳 Build Docker Images Script for Windows

echo 🚀 Building DDoS Simulation Lab Docker Images...
echo.

REM Build C2 Server
echo 🏢 Building C2 Server image...
docker build -f Dockerfile.c2 -t ddos-lab/c2-server:latest .

REM Build Bot Client
echo 🤖 Building Bot Client image...
docker build -f Dockerfile.bot -t ddos-lab/bot-client:latest .

echo.
echo ✅ Docker images built successfully!
echo.
echo 📋 Available images:
docker images | findstr ddos-lab

echo.
echo 🎯 Next steps:
echo   • Run basic setup: docker-compose up
echo   • Run scaled setup: docker-compose -f docker-compose.scale.yml up
echo   • Scale bots: docker-compose -f docker-compose.scale.yml up --scale bot=28

pause