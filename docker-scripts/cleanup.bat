@echo off
REM 🧹 Cleanup DDoS Lab Docker Resources

echo 🧹 DDoS Lab Cleanup Script
echo ========================
echo.

echo 🛑 Stopping all containers...
docker-compose down
docker-compose -f docker-compose.scale.yml down

echo.
echo 🗑️ Removing containers...
docker container prune -f

echo.
echo 🖼️ Removing unused images...
docker image prune -f

echo.
echo 📊 Current Docker status:
echo Containers:
docker ps -a | findstr ddos
echo.
echo Images:
docker images | findstr ddos-lab

echo.
echo ✅ Cleanup completed!
echo.
echo 🔄 To restart:
echo   • Basic: run-basic.bat
echo   • Scaled: run-scaled.bat

pause