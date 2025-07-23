#!/bin/bash

# Unified Betting App - Docker Deployment Script
echo "🚀 Unified Betting App - Docker Deployment"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose found"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p backend/data backend/logs

# Build and start the application
echo "🔨 Building and starting the application..."
docker-compose up --build -d

# Wait for the application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if the application is running
echo "🔍 Checking application status..."
if curl -f http://localhost:5001/test &> /dev/null; then
    echo "✅ Application is running successfully!"
    echo "🌐 Access the application at: http://localhost:5001"
    echo "📊 API documentation at: http://localhost:5001/docs"
else
    echo "⚠️ Application might still be starting up..."
    echo "🔍 Check logs with: docker-compose logs -f"
fi

echo ""
echo "📋 Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop app: docker-compose down"
echo "  Restart app: docker-compose restart"
echo "  Update app: docker-compose up --build -d" 