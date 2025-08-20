@echo off
REM 🤖 Deploy Bot Client on Windows system

if "%1"=="" (
    echo 🤖 Bot Deployment Script
    echo Usage: %0 ^<C2_SERVER_IP^>
    echo Example: %0 192.168.1.100
    pause
    exit /b 1
)

set C2_SERVER_IP=%1
set BOT_ID=bot-%COMPUTERNAME%

echo 🤖 Deploying Bot Client...
echo Bot ID: %BOT_ID%
echo C2 Server: %C2_SERVER_IP%

REM Build bot client image
docker build -f Dockerfile.bot -t ddos-lab/bot-client .

REM Run bot client container
docker run -d ^
  --name %BOT_ID% ^
  --restart unless-stopped ^
  -e BOT_ID=%BOT_ID% ^
  -e C2_SERVER_HOST=%C2_SERVER_IP% ^
  -e C2_SERVER_PORT=8081 ^
  -e BOT_NAME=%BOT_ID% ^
  -e PYTHONPATH=/app ^
  ddos-lab/bot-client

echo.
echo ✅ Bot %BOT_ID% deployed and connecting to C2 server!
echo 📊 Check status: docker logs %BOT_ID%
echo 🛑 Stop bot: docker stop %BOT_ID%

pause