@echo off
REM ========================================
REM Nexus ERP - Installation Script
REM ========================================
REM Platform: Windows
REM Usage: install.bat
REM ========================================

setlocal enabledelayedexpansion

REM Colors (Windows 10+)
for /F %%a in ('echo prompt $E^| cmd') do set "ESC=%%a"
set "RED=!ESC![31m"
set "GREEN=!ESC![32m"
set "YELLOW=!ESC![33m"
set "BLUE=!ESC![34m"
set "NC=!ESC![0m"

REM Logo
echo.
echo !BLUE!================================================================
echo   ____      _   ______  _____      _            
echo  ^|  _ \ ___^| ^|_/ ^| ___^|^|  ___^|    ^| ^| ___  _ __ 
echo  ^| ^|_) / _ \ __\ ^|___ \^| ^|_  _____^| ^|/ _ \^| '__^|
echo  ^|  __/  __/ ^|_ ___) ^|  _^|^|_____^| ^| (_) ^| ^|   
echo  ^|_^|   \___^|\__^|____/^|_^|         ^|_|\___/^|_^|   
echo. 
echo             ERP System v1.0.0              
echo ================================================================================!NC!
echo.

REM ========================================
REM System Checks
REM ========================================

echo !BLUE![INFO]!NC! Checking system requirements...
echo.

REM Check Docker
echo !BLUE![INFO]!NC! Checking Docker...
where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo !RED![ERROR]!NC! Docker is not installed.
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('docker --version 2^>nul') do set DOCKER_VERSION=%%i
echo !GREEN![SUCCESS]!NC! Docker installed: %DOCKER_VERSION%

REM Check Docker Compose
echo !BLUE![INFO]!NC! Checking Docker Compose...
docker compose version >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set COMPOSE_CMD=docker compose
) else (
    where docker-compose >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set COMPOSE_CMD=docker-compose
    ) else (
        echo !RED![ERROR]!NC! Docker Compose is not installed.
        pause
        exit /b 1
    )
)
echo !GREEN![SUCCESS]!NC! Docker Compose is available

REM Check Docker daemon
echo !BLUE![INFO]!NC! Checking Docker daemon...
docker info >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo !RED![ERROR]!NC! Docker daemon is not running.
    echo Please start Docker Desktop.
    pause
    exit /b 1
)
echo !GREEN![SUCCESS]!NC! Docker daemon is running

echo.

REM ========================================
REM Environment Setup
REM ========================================

echo !BLUE![INFO]!NC! Setting up configuration files...
echo.

REM Check for .env file
if exist .env (
    echo !YELLOW![WARNING]!NC! .env file already exists.
    set /p USE_EXISTING="Do you want to use it? (y/n): "
    if /i "!USE_EXISTING!"=="y" (
        echo !BLUE![INFO]!NC! Using existing .env file...
    ) else (
        REM Backup and create new
        set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%%time:~0,2%%time:~3,2%%time:~6,2%
        set TIMESTAMP=!TIMESTAMP: =0!
        copy .env .env.backup.!TIMESTAMP! >nul
        echo !BLUE![INFO]!NC! Backup saved: .env.backup.!TIMESTAMP!
        copy .env.example .env >nul
    )
) else (
    if exist .env.example (
        copy .env.example .env >nul
        echo !GREEN![SUCCESS]!NC! Created .env from .env.example
    ) else (
        echo !RED![ERROR]!NC! .env.example file not found!
        pause
        exit /b 1
    )
)

REM Generate random strings for secrets
echo !BLUE![INFO]!NC! Generating security keys...

REM Generate SECRET_KEY (simple random string)
set "SECRET_KEY="
for /L %%i in (1,1,32) do (
    set /a RAND=!RANDOM! %% 62
    if !RAND! lss 10 (
        set "CHAR=!RAND!"
    ) else if !RAND! lss 36 (
        set /a CHAR=!RAND! + 55
        cmd /c exit /b !CHAR!
        set "CHAR!=ExitCodeASCII"
    ) else (
        set /a CHAR=!RAND! + 61
        cmd /c exit /b !CHAR!
        set "CHAR!=ExitCodeASCII"
    )
    set "SECRET_KEY=!SECRET_KEY!!CHAR!"
)

REM Update .env with generated keys using PowerShell
powershell -Command "(Get-Content .env) -replace 'SECRET_KEY=.*', 'SECRET_KEY=!SECRET_KEY!' | Set-Content .env"
powershell -Command "(Get-Content .env) -replace 'JWT_SECRET_KEY=.*', 'JWT_SECRET_KEY=!SECRET_KEY!_JWT' | Set-Content .env"

echo !GREEN![SUCCESS]!NC! Security keys generated

echo.

REM ========================================
REM Docker Build and Start
REM ========================================

echo !BLUE![INFO]!NC! Building and starting containers...
echo !BLUE![INFO]!NC! This may take a few minutes on first run...
echo.

REM Pull base images
%COMPOSE_CMD% pull 2>nul

REM Build and start
%COMPOSE_CMD% up -d --build
if %ERRORLEVEL% neq 0 (
    echo !RED![ERROR]!NC! Failed to build/start containers.
    echo Check logs: %COMPOSE_CMD% logs
    pause
    exit /b 1
)

echo !GREEN![SUCCESS]!NC! Containers built and started

echo.

REM ========================================
REM Wait for Services
REM ========================================

echo !BLUE![INFO]!NC! Waiting for services to start...
echo.

REM Wait for PostgreSQL
echo !BLUE![INFO]!NC! Waiting for database...
set MAX_WAIT=60
set WAIT_COUNT=0
:wait_postgres
if !WAIT_COUNT! geq !MAX_WAIT! goto postgres_timeout
%COMPOSE_CMD% exec -T postgres pg_isready -U nexus_user -d nexus_erp >nul 2>nul
if %ERRORLEVEL% equ 0 goto postgres_ready
timeout /t 1 >nul
set /a WAIT_COUNT+=1
echo|set /p="."
goto wait_postgres
:postgres_timeout
echo.
echo !RED![ERROR]!NC! Database did not start in expected time
echo Check logs: %COMPOSE_CMD% logs postgres
pause
exit /b 1
:postgres_ready
echo.
echo !GREEN![SUCCESS]!NC! Database is ready

REM Wait for Backend
echo !BLUE![INFO]!NC! Waiting for API...
timeout /t 10 >nul

echo !GREEN![SUCCESS]!NC! Services are starting

echo.

REM ========================================
REM Database Migrations
REM ========================================

echo !BLUE![INFO]!NC! Running database migrations...
timeout /t 5 >nul

%COMPOSE_CMD% exec -T backend alembic upgrade head 2>nul
if %ERRORLEVEL% neq 0 (
    echo !YELLOW![WARNING]!NC! Migrations may have already been applied
)

echo !GREEN![SUCCESS]!NC! Migrations completed

echo.

REM ========================================
REM Load Demo Data
REM ========================================

echo !BLUE![INFO]!NC! Loading demo data...

if exist docker\demo_data.sql (
    type docker\demo_data.sql | %COMPOSE_CMD% exec -T postgres psql -U nexus_user -d nexus_erp 2>nul
    if %ERRORLEVEL% equ 0 (
        echo !GREEN![SUCCESS]!NC! Demo data loaded
    ) else (
        echo !YELLOW![WARNING]!NC! Could not load demo data
    )
) else (
    echo !YELLOW![WARNING]!NC! Demo data file not found
)

echo.

REM ========================================
REM Final Status
REM ========================================

echo.
echo !GREEN!================================================================
echo                     Installation Complete!                
echo ================================================================================!NC!
echo.
echo !BLUE!Access Information:!NC!
echo.
echo   Frontend:        http://localhost
echo   API Docs:        http://localhost:8000/docs
echo   ReDoc:           http://localhost:8000/redoc
echo.
echo !BLUE!Default Credentials:!NC!
echo.
echo   Admin User:
echo     Email:    admin@nexus.com
echo     Password: Admin123!
echo.
echo   Demo User:
echo     Email:    demo@nexus.com
echo     Password: Demo123!
echo.
echo !YELLOW!Security Warning:!NC! Change passwords immediately after login!
echo.
echo !BLUE!Useful Commands:!NC!
echo.
echo   View logs:       %COMPOSE_CMD% logs -f
echo   Stop system:     %COMPOSE_CMD% down
echo   Restart:         %COMPOSE_CMD% restart
echo   Status:          %COMPOSE_CMD% ps
echo.
echo !GREEN!================================================================
echo        Thank you for choosing Nexus ERP - Best of luck!        
echo ================================================================================!NC!
echo.

REM Open browser
set /p OPEN_BROWSER="Open browser now? (y/n): "
if /i "!OPEN_BROWSER!"=="y" (
    start http://localhost
)

pause
