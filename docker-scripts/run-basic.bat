@echo off
REM 🎮 Run Basic DDoS Lab Setup (3 bots) - Windows

echo 🚀 Starting DDoS Simulation Lab - Basic Setup...
echo 📊 This will start:
echo   • 1 C2 Server
echo   • 3 Bot clients
echo   • 1 Target server (Nginx)
echo.

REM Create data directory
if not exist "data" mkdir data
if not exist "target-content" mkdir target-content

REM Create simple target content
echo ^<!DOCTYPE html^> > target-content\index.html
echo ^<html^> >> target-content\index.html
echo ^<head^> >> target-content\index.html
echo     ^<title^>🎯 DDoS Target Server^</title^> >> target-content\index.html
echo     ^<style^> >> target-content\index.html
echo         body { font-family: Arial; text-align: center; padding: 50px; } >> target-content\index.html
echo         .status { color: green; font-size: 24px; } >> target-content\index.html
echo     ^</style^> >> target-content\index.html
echo ^</head^> >> target-content\index.html
echo ^<body^> >> target-content\index.html
echo     ^<h1^>🎯 DDoS Simulation Target^</h1^> >> target-content\index.html
echo     ^<div class="status"^>✅ Server is running normally^</div^> >> target-content\index.html
echo     ^<p^>This server is the target for DDoS simulation attacks.^</p^> >> target-content\index.html
echo     ^<p^>Monitor response times during attacks!^</p^> >> target-content\index.html
echo ^</body^> >> target-content\index.html
echo ^</html^> >> target-content\index.html

REM Start the lab
docker-compose up -d

echo.
echo ✅ DDoS Lab is starting up!
echo.
echo 🌐 Access points:
echo   • C2 Dashboard: http://localhost:8080
echo   • Target Server: http://localhost:8090
echo.
echo 📊 Monitor with:
echo   • docker-compose logs -f
echo   • docker-compose ps
echo.
echo 🛑 Stop with:
echo   • docker-compose down

pause