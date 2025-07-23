@echo off
REM Unified Betting App - Docker Deployment Script (Windows)
echo 🚀 Unified Betting App - Docker Deployment
echo ==========================================

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

echo ✅ Docker and Docker Compose found

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist "backend\data" mkdir backend\data
if not exist "backend\logs" mkdir backend\logs

REM Build and start the application
echo 🔨 Building and starting the application...
docker-compose up --build -d

REM Wait for the application to start
echo ⏳ Waiting for application to start...
timeout /t 10 /nobreak >nul

REM Check if the application is running
echo 🔍 Checking application status...
curl -f http://localhost:5001/test >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Application might still be starting up...
    echo 🔍 Check logs with: docker-compose logs -f
) else (
    echo ✅ Application is running successfully!
    echo 🌐 Access the application at: http://localhost:5001
    echo 📊 API documentation at: http://localhost:5001/docs
)

echo.
echo 📋 Useful commands:
echo   View logs: docker-compose logs -f
echo   Stop app: docker-compose down
echo   Restart app: docker-compose restart
echo   Update app: docker-compose up --build -d

pause 