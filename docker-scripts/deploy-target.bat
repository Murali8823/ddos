@echo off
REM 🎯 Deploy Target Server on Windows system

echo 🎯 Deploying Target Server...

REM Create target content
if not exist "target-content" mkdir target-content

echo ^<!DOCTYPE html^> > target-content\index.html
echo ^<html^> >> target-content\index.html
echo ^<head^> >> target-content\index.html
echo     ^<title^>🎯 DDoS Target Server^</title^> >> target-content\index.html
echo     ^<style^> >> target-content\index.html
echo         body { font-family: Arial; text-align: center; padding: 50px; } >> target-content\index.html
echo         .status { color: green; font-size: 24px; } >> target-content\index.html
echo         .info { color: blue; margin: 20px; } >> target-content\index.html
echo     ^</style^> >> target-content\index.html
echo ^</head^> >> target-content\index.html
echo ^<body^> >> target-content\index.html
echo     ^<h1^>🎯 DDoS Simulation Target^</h1^> >> target-content\index.html
echo     ^<div class="status"^>✅ Server is running normally^</div^> >> target-content\index.html
echo     ^<div class="info"^> >> target-content\index.html
echo         ^<p^>This server is the target for DDoS simulation attacks.^</p^> >> target-content\index.html
echo         ^<p^>Monitor response times during attacks!^</p^> >> target-content\index.html
echo     ^</div^> >> target-content\index.html
echo ^</body^> >> target-content\index.html
echo ^</html^> >> target-content\index.html

REM Run target server
docker run -d ^
  --name ddos-target-server ^
  --restart unless-stopped ^
  -p 80:80 ^
  -p 8090:80 ^
  -v %cd%\target-content:/usr/share/nginx/html:ro ^
  nginx:alpine

echo.
echo ✅ Target Server deployed!
echo 🌐 Target URL: http://localhost:80
echo 🌐 Alt URL: http://localhost:8090
echo.
echo 📊 Check status: docker logs ddos-target-server
echo 🛑 Stop server: docker stop ddos-target-server

pause