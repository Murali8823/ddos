@echo off
REM 🏢 Deploy C2 Server on Windows system

echo 🏢 Deploying C2 Server...

REM Build C2 server image
docker build -f Dockerfile.c2 -t ddos-lab/c2-server .

REM Create data directory
if not exist "data" mkdir data

REM Run C2 server container
docker run -d ^
  --name ddos-c2-server ^
  --restart unless-stopped ^
  -p 8080:8080 ^
  -p 8081:8081 ^
  -v %cd%\data:/app/data ^
  -e PYTHONPATH=/app ^
  -e DATABASE_PATH=/app/data/ddos_lab.db ^
  ddos-lab/c2-server

echo.
echo ✅ C2 Server deployed!
echo 🌐 Dashboard: http://localhost:8080
echo 📡 WebSocket: ws://localhost:8081
echo.
echo 📊 Check status: docker logs ddos-c2-server
echo 🛑 Stop server: docker stop ddos-c2-server

pause