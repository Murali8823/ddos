@echo off
REM 🎯 Scale Bot Army Script for Windows

if "%1"=="" (
    echo 🤖 Bot Army Scaling Script
    echo.
    echo Usage: %0 ^<number_of_bots^>
    echo.
    echo Examples:
    echo   %0 5    # Scale to 5 bots
    echo   %0 28   # Scale to 28 bots (full army)
    echo   %0 50   # Scale to 50 bots (mega army!)
    echo.
    echo Current bot count:
    docker-compose -f docker-compose.scale.yml ps bot | find /c "Up"
    pause
    exit /b 1
)

set BOT_COUNT=%1

echo 🚀 Scaling bot army to %BOT_COUNT% bots...

REM Scale the bot service
docker-compose -f docker-compose.scale.yml up --scale bot=%BOT_COUNT% -d

echo.
echo ✅ Bot army scaled to %BOT_COUNT% bots!
echo.
echo 📊 Current status:
docker-compose -f docker-compose.scale.yml ps

echo.
set /a ATTACK_CAPACITY=%BOT_COUNT% * 100
echo 🎯 Attack capacity: ~%ATTACK_CAPACITY% requests/second
echo.
echo 📈 Monitor with:
echo   • docker-compose -f docker-compose.scale.yml logs -f bot
echo   • docker stats

pause