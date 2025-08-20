@echo off
REM 🚀 Run Scaled DDoS Lab Setup (28 bots) for Windows

echo 🚀 Starting DDoS Simulation Lab - FULL SCALE...
echo 📊 This will start:
echo   • 1 C2 Server
echo   • 28 Bot clients (scalable)
echo   • 1 Target server (Nginx)
echo.

REM Create data directory
if not exist "data" mkdir data
if not exist "target-content" mkdir target-content

REM Create target content
echo ^<!DOCTYPE html^> > target-content\index.html
echo ^<html^> >> target-content\index.html
echo ^<head^> >> target-content\index.html
echo     ^<title^>🎯 DDoS Target Server - Full Scale Test^</title^> >> target-content\index.html
echo     ^<style^> >> target-content\index.html
echo         body { font-family: Arial; text-align: center; padding: 50px; } >> target-content\index.html
echo         .status { color: green; font-size: 24px; } >> target-content\index.html
echo         .warning { color: orange; font-size: 18px; } >> target-content\index.html
echo     ^</style^> >> target-content\index.html
echo ^</head^> >> target-content\index.html
echo ^<body^> >> target-content\index.html
echo     ^<h1^>🎯 DDoS Simulation Target - FULL SCALE^</h1^> >> target-content\index.html
echo     ^<div class="status"^>✅ Server is running normally^</div^> >> target-content\index.html
echo     ^<div class="warning"^>⚠️ This server will be attacked by 28 bots!^</div^> >> target-content\index.html
echo     ^<p^>Monitor response times and server performance during the attack.^</p^> >> target-content\index.html
echo     ^<p^>Expected load: ~2,800 requests per second^</p^> >> target-content\index.html
echo ^</body^> >> target-content\index.html
echo ^</html^> >> target-content\index.html

REM Start with scaled bot army
echo 🤖 Deploying 28-bot army...
docker-compose -f docker-compose.scale.yml up -d
docker-compose -f docker-compose.scale.yml up --scale bot=28 -d

echo.
echo ✅ Full-scale DDoS Lab is deployed!
echo.
echo 🌐 Access points:
echo   • C2 Dashboard: http://localhost:8080
echo   • Target Server: http://localhost:8090
echo.
echo 📊 Monitor the army:
echo   • docker-compose -f docker-compose.scale.yml ps
echo   • docker-compose -f docker-compose.scale.yml logs -f bot
echo.
echo 🛑 Stop the army:
echo   • docker-compose -f docker-compose.scale.yml down

pause