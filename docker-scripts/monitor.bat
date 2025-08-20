@echo off
REM 📊 Monitor DDoS Lab Script for Windows

if "%1"=="status" goto status
if "%1"=="logs" goto logs
if "%1"=="target" goto target
if "%1"=="live" goto live
goto help

:status
echo.
echo 🐳 Container Status:
docker-compose ps
echo.
echo 📈 Resource Usage:
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
goto end

:logs
echo.
echo 📋 Recent Logs (C2 Server):
docker-compose logs --tail=10 c2-server
echo.
echo 📋 Recent Logs (Bots):
docker-compose logs --tail=5 bot-001 bot-002 bot-003
goto end

:target
echo.
echo 🎯 Testing Target Server Response:
echo ==================================
powershell -Command "& {$start = Get-Date; try { $response = Invoke-WebRequest -Uri 'http://localhost:8090' -TimeoutSec 10; $end = Get-Date; $time = ($end - $start).TotalSeconds; Write-Host '✅ Target server responding: HTTP' $response.StatusCode; Write-Host '⏱️  Response time:' $time 's' } catch { $end = Get-Date; $time = ($end - $start).TotalSeconds; Write-Host '❌ Target server issues:' $_.Exception.Message; Write-Host '⏱️  Response time:' $time 's' }}"
goto end

:live
echo 🔄 Starting live monitoring (Ctrl+C to stop)...
:liveloop
cls
echo 📊 DDoS Lab Live Monitor - %date% %time%
echo ==================================
call :status
call :target
timeout /t 5 /nobreak >nul
goto liveloop

:help
echo 📊 DDoS Lab Monitor Commands:
echo.
echo   %0 status  - Show container status and resources
echo   %0 logs    - Show recent logs
echo   %0 target  - Test target server response
echo   %0 live    - Live monitoring (updates every 5s)
echo.
echo 🌐 Quick access:
echo   • C2 Dashboard: http://localhost:8080
echo   • Target Server: http://localhost:8090

:end
pause