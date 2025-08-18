# Phase 4: Windows Victim Setup Commands

This file contains all commands to set up the Windows victim machine for DDoS simulation testing.

## Prerequisites
- Windows 10/11 or Windows Server
- Administrator privileges
- Network connectivity to C2 server and bots
- Static IP address configured (192.168.1.200)

## Step 1: Network Configuration

### Configure Static IP Address

```cmd
# Open Network and Sharing Center
ncpa.cpl

# Or use PowerShell (Run as Administrator)
New-NetIPAddress -InterfaceAlias "Ethernet" -IPAddress 192.168.1.200 -PrefixLength 24 -DefaultGateway 192.168.1.1
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 8.8.8.8,8.8.4.4

# Verify network configuration
ipconfig /all
```

### Test Network Connectivity

```cmd
# Test connectivity to C2 server
ping 192.168.1.100

# Test connectivity to bot machines
ping 192.168.1.101
ping 192.168.1.102

# Check current network connections
netstat -an
```

## Step 2: Install Web Server (IIS)

### Enable IIS on Windows

```cmd
# Enable IIS via DISM (Run as Administrator)
dism /online /enable-feature /featurename:IIS-WebServerRole
dism /online /enable-feature /featurename:IIS-WebServer
dism /online /enable-feature /featurename:IIS-CommonHttpFeatures
dism /online /enable-feature /featurename:IIS-HttpErrors
dism /online /enable-feature /featurename:IIS-HttpLogging
dism /online /enable-feature /featurename:IIS-RequestMonitor

# Or via PowerShell
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer
Enable-WindowsOptionalFeature -Online -FeatureName IIS-CommonHttpFeatures
```

### Configure IIS

```cmd
# Start IIS service
net start w3svc

# Set IIS to start automatically
sc config w3svc start= auto

# Check IIS status
sc query w3svc

# Test web server
curl http://localhost
# Or open browser to http://localhost
```

### Create Test Web Content

```cmd
# Navigate to IIS root directory
cd C:\inetpub\wwwroot

# Create test HTML files
echo ^<html^>^<head^>^<title^>DDoS Test Target^</title^>^</head^>^<body^>^<h1^>DDoS Simulation Target^</h1^>^<p^>This is the target server for DDoS simulation.^</p^>^</body^>^</html^> > index.html

# Create additional test pages
echo ^<html^>^<body^>^<h1^>Login Page^</h1^>^<form^>Username: ^<input type="text"^>^<br^>Password: ^<input type="password"^>^<br^>^<input type="submit"^>^</form^>^</body^>^</html^> > login.html

echo ^<html^>^<body^>^<h1^>Search Page^</h1^>^<form^>^<input type="text" placeholder="Search..."^>^<input type="submit"^>^</form^>^</body^>^</html^> > search.html

# Create large file for bandwidth testing
fsutil file createnew large_file.txt 10485760
```

## Step 3: Install Alternative Web Server (Apache - Optional)

### Download and Install Apache

```cmd
# Download Apache from https://www.apachelounge.com/download/
# Extract to C:\Apache24

# Install Apache as Windows service
cd C:\Apache24\bin
httpd.exe -k install

# Start Apache service
net start Apache2.4

# Set Apache to start automatically
sc config Apache2.4 start= auto
```

### Configure Apache

```cmd
# Edit Apache configuration
notepad C:\Apache24\conf\httpd.conf

# Key settings to verify:
# Listen 80
# ServerRoot "C:/Apache24"
# DocumentRoot "C:/Apache24/htdocs"

# Test Apache configuration
C:\Apache24\bin\httpd.exe -t

# Restart Apache
net stop Apache2.4
net start Apache2.4
```

## Step 4: Setup Monitoring Tools

### Install Performance Monitor

```cmd
# Open Performance Monitor
perfmon

# Create custom performance counter set
# Add counters for:
# - Processor(_Total)\% Processor Time
# - Memory\Available MBytes
# - Network Interface(*)\Bytes Total/sec
# - Web Service(_Total)\Current Connections
```

### Setup Resource Monitor

```cmd
# Open Resource Monitor
resmon

# Monitor:
# - CPU usage
# - Memory usage
# - Network activity
# - Disk activity
```

### Create Monitoring Scripts

```cmd
# Create CPU monitoring script
echo @echo off > monitor_cpu.bat
echo :loop >> monitor_cpu.bat
echo wmic cpu get loadpercentage /value >> monitor_cpu.bat
echo timeout /t 5 /nobreak ^> nul >> monitor_cpu.bat
echo goto loop >> monitor_cpu.bat

# Create network monitoring script
echo @echo off > monitor_network.bat
echo :loop >> monitor_network.bat
echo netstat -e >> monitor_network.bat
echo echo. >> monitor_network.bat
echo timeout /t 5 /nobreak ^> nul >> monitor_network.bat
echo goto loop >> monitor_network.bat

# Create connection monitoring script
echo @echo off > monitor_connections.bat
echo :loop >> monitor_connections.bat
echo netstat -an ^| find ":80" >> monitor_connections.bat
echo echo. >> monitor_connections.bat
echo timeout /t 2 /nobreak ^> nul >> monitor_connections.bat
echo goto loop >> monitor_connections.bat
```

## Step 5: Configure Windows Firewall

### Allow Web Traffic

```cmd
# Allow HTTP traffic (port 80)
netsh advfirewall firewall add rule name="HTTP Inbound" dir=in action=allow protocol=TCP localport=80

# Allow HTTPS traffic (port 443)
netsh advfirewall firewall add rule name="HTTPS Inbound" dir=in action=allow protocol=TCP localport=443

# Allow ping (ICMP)
netsh advfirewall firewall add rule name="ICMP Allow incoming V4 echo request" protocol=icmpv4:8,any dir=in action=allow

# Check firewall rules
netsh advfirewall firewall show rule name=all | findstr "HTTP"
```

### Configure Firewall for Testing

```cmd
# Temporarily disable Windows Firewall (for testing only)
netsh advfirewall set allprofiles state off

# Re-enable after testing
netsh advfirewall set allprofiles state on

# Or configure specific rules for lab network
netsh advfirewall firewall add rule name="Lab Network" dir=in action=allow remoteip=192.168.1.0/24
```

## Step 6: Setup Logging

### Enable IIS Logging

```cmd
# IIS logs are typically enabled by default
# Location: C:\inetpub\logs\LogFiles\W3SVC1\

# View recent IIS logs
dir C:\inetpub\logs\LogFiles\W3SVC1\ /o-d
type C:\inetpub\logs\LogFiles\W3SVC1\*.log | more
```

### Setup Event Log Monitoring

```cmd
# Open Event Viewer
eventvwr

# Monitor these logs:
# - Windows Logs > System
# - Windows Logs > Security
# - Applications and Services Logs > Microsoft > Windows > IIS-Configuration
```

### Create Log Analysis Script

```cmd
# Create log analysis script
echo @echo off > analyze_logs.bat
echo echo === IIS Access Log Analysis === >> analyze_logs.bat
echo for /f %%i in ('dir C:\inetpub\logs\LogFiles\W3SVC1\*.log /b /o-d ^| head -1') do set LATEST_LOG=%%i >> analyze_logs.bat
echo echo Latest log file: %LATEST_LOG% >> analyze_logs.bat
echo echo. >> analyze_logs.bat
echo echo Top IP addresses: >> analyze_logs.bat
echo findstr /r "^[0-9]" C:\inetpub\logs\LogFiles\W3SVC1\%LATEST_LOG% ^| for /f "tokens=1" %%a in ('more') do echo %%a ^| sort ^| uniq -c ^| sort -nr ^| head -10 >> analyze_logs.bat
```

## Step 7: Performance Baseline

### Establish Baseline Metrics

```cmd
# Create baseline measurement script
echo @echo off > baseline.bat
echo echo === System Baseline Measurement === >> baseline.bat
echo echo Date/Time: %date% %time% >> baseline.bat
echo echo. >> baseline.bat
echo echo CPU Usage: >> baseline.bat
echo wmic cpu get loadpercentage /value >> baseline.bat
echo echo. >> baseline.bat
echo echo Memory Usage: >> baseline.bat
echo wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /value >> baseline.bat
echo echo. >> baseline.bat
echo echo Network Connections: >> baseline.bat
echo netstat -an ^| find ":80" ^| find /c "ESTABLISHED" >> baseline.bat
echo echo. >> baseline.bat
echo echo Disk Usage: >> baseline.bat
echo wmic logicaldisk get size,freespace,caption >> baseline.bat

# Run baseline measurement
baseline.bat > baseline_results.txt
```

### Setup Continuous Monitoring

```cmd
# Create continuous monitoring script
echo @echo off > continuous_monitor.bat
echo :loop >> continuous_monitor.bat
echo echo %date% %time% >> monitor_log.txt >> continuous_monitor.bat
echo wmic cpu get loadpercentage /value ^| findstr LoadPercentage >> monitor_log.txt >> continuous_monitor.bat
echo netstat -an ^| find ":80" ^| find /c "ESTABLISHED" >> monitor_log.txt >> continuous_monitor.bat
echo echo. >> monitor_log.txt >> continuous_monitor.bat
echo timeout /t 10 /nobreak ^> nul >> continuous_monitor.bat
echo goto loop >> continuous_monitor.bat
```

## Step 8: Test Target Services

### Test Web Server Accessibility

```cmd
# Test from local machine
curl http://192.168.1.200
curl http://192.168.1.200/login.html
curl http://192.168.1.200/search.html

# Test from C2 server (run on C2 server)
curl http://192.168.1.200
wget http://192.168.1.200/large_file.txt
```

### Test Different Ports

```cmd
# Setup additional services for testing
# Install Node.js simple HTTP server on port 3000
npm install -g http-server
http-server -p 3000

# Or use Python simple server
python -m http.server 8000

# Test additional ports
curl http://192.168.1.200:3000
curl http://192.168.1.200:8000
```

## Step 9: Create Attack Response Procedures

### Emergency Stop Procedures

```cmd
# Create emergency stop script
echo @echo off > emergency_stop.bat
echo echo === EMERGENCY STOP PROCEDURES === >> emergency_stop.bat
echo echo Stopping web services... >> emergency_stop.bat
echo net stop w3svc >> emergency_stop.bat
echo net stop Apache2.4 >> emergency_stop.bat
echo echo. >> emergency_stop.bat
echo echo Blocking attack traffic... >> emergency_stop.bat
echo netsh advfirewall firewall add rule name="Block Lab Network" dir=in action=block remoteip=192.168.1.0/24 >> emergency_stop.bat
echo echo. >> emergency_stop.bat
echo echo Emergency stop completed! >> emergency_stop.bat
```

### Recovery Procedures

```cmd
# Create recovery script
echo @echo off > recovery.bat
echo echo === RECOVERY PROCEDURES === >> recovery.bat
echo echo Removing emergency blocks... >> recovery.bat
echo netsh advfirewall firewall delete rule name="Block Lab Network" >> recovery.bat
echo echo. >> recovery.bat
echo echo Restarting web services... >> recovery.bat
echo net start w3svc >> recovery.bat
echo net start Apache2.4 >> recovery.bat
echo echo. >> recovery.bat
echo echo Recovery completed! >> recovery.bat
```

## Verification Commands

### System Status Check

```cmd
# Check all services
sc query w3svc
sc query Apache2.4

# Check network listeners
netstat -an | findstr :80
netstat -an | findstr :443

# Check firewall status
netsh advfirewall show allprofiles state

# Test web accessibility
curl http://192.168.1.200
```

### Performance Check

```cmd
# Check system resources
wmic cpu get loadpercentage /value
wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value

# Check network statistics
netstat -e

# Check active connections
netstat -an | find ":80" | find /c "ESTABLISHED"
```

## Troubleshooting

### Web Server Issues

```cmd
# Check IIS status
sc query w3svc

# Check IIS logs
type C:\inetpub\logs\LogFiles\W3SVC1\*.log | findstr "500\|404\|403"

# Restart IIS
iisreset

# Check Apache status (if using Apache)
sc query Apache2.4
C:\Apache24\bin\httpd.exe -t
```

### Network Issues

```cmd
# Check IP configuration
ipconfig /all

# Test connectivity
ping 192.168.1.100
telnet 192.168.1.100 8080

# Check routing
route print

# Flush DNS
ipconfig /flushdns
```

### Performance Issues

```cmd
# Check running processes
tasklist /svc

# Check system resources
wmic process get processid,percentprocessortime,workingsetsize

# Check disk space
dir C:\ /-c
```

## Next Steps

After completing this phase:
1. Verify web server is accessible from bot machines
2. Confirm monitoring tools are working
3. Proceed to Phase 5: Attack Execution

## Important Notes

- Target IP: `192.168.1.200`
- Web server ports: `80, 443, 3000, 8000`
- Log locations: `C:\inetpub\logs\LogFiles\W3SVC1\`
- Emergency procedures available in created scripts
- Baseline measurements saved for comparison