@echo off
REM 🚀 Quick Start DDoS Lab for Windows

echo.
echo  ██████╗ ██████╗  ██████╗ ███████╗    ██╗      █████╗ ██████╗ 
echo  ██╔══██╗██╔══██╗██╔═══██╗██╔════╝    ██║     ██╔══██╗██╔══██╗
echo  ██║  ██║██║  ██║██║   ██║███████╗    ██║     ███████║██████╔╝
echo  ██║  ██║██║  ██║██║   ██║╚════██║    ██║     ██╔══██║██╔══██╗
echo  ██████╔╝██████╔╝╚██████╔╝███████║    ███████╗██║  ██║██████╔╝
echo  ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝    ╚══════╝╚═╝  ╚═╝╚═════╝ 
echo.
echo                    🎮 Docker Edition 🐳
echo.

:menu
echo ═══════════════════════════════════════════════════════════════
echo                    🎯 DDoS Simulation Lab Menu
echo ═══════════════════════════════════════════════════════════════
echo.
echo  1. 🏗️  Build Docker Images
echo  2. 🎮 Start Basic Lab (3 bots)
echo  3. 🚀 Start Full Scale Lab (28 bots)
echo  4. 📊 Monitor Lab Status
echo  5. 🎯 Scale Bot Army
echo  6. 🧹 Cleanup Everything
echo  7. ❌ Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto build
if "%choice%"=="2" goto basic
if "%choice%"=="3" goto scaled
if "%choice%"=="4" goto monitor
if "%choice%"=="5" goto scale
if "%choice%"=="6" goto cleanup
if "%choice%"=="7" goto exit
echo Invalid choice! Please try again.
goto menu

:build
echo.
echo 🏗️ Building Docker images...
call build.bat
goto menu

:basic
echo.
echo 🎮 Starting basic lab...
call run-basic.bat
goto menu

:scaled
echo.
echo 🚀 Starting full scale lab...
call run-scaled.bat
goto menu

:monitor
echo.
echo 📊 Choose monitoring option:
echo  1. Status
echo  2. Logs
echo  3. Target Test
echo  4. Live Monitor
set /p mon_choice="Enter choice (1-4): "
if "%mon_choice%"=="1" call monitor.bat status
if "%mon_choice%"=="2" call monitor.bat logs
if "%mon_choice%"=="3" call monitor.bat target
if "%mon_choice%"=="4" call monitor.bat live
goto menu

:scale
echo.
set /p bot_count="Enter number of bots (1-100): "
call scale-bots.bat %bot_count%
goto menu

:cleanup
echo.
echo 🧹 Cleaning up...
call cleanup.bat
goto menu

:exit
echo.
echo 👋 Thanks for using DDoS Simulation Lab!
echo    Remember: Use for educational purposes only! 🎓
pause
exit