#!/bin/bash

# Production Deployment Script for AV Gym System
echo "🚀 Starting production deployment..."

# Load production environment (filter out comments and empty lines)
export $(cat .env.production | grep -v '^#' | grep -v '^$' | xargs)

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin main

# Build containers
echo "🏗️  Building containers..."
docker-compose build

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Start containers with production config
echo "▶️  Starting containers..."
docker-compose --env-file .env.production up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Run migrations
echo "📊 Running database migrations..."
docker-compose exec web python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose exec web python manage.py collectstatic --noinput

# Check service status
echo "📋 Checking service status..."
docker-compose ps

# Test health endpoint
echo "🏥 Testing health endpoint..."
curl -s http://46.101.193.107:8000/health/ | python3 -m json.tool

echo "✅ Production deployment complete!"
echo "🌐 Frontend: http://46.101.193.107:3000"
echo "🔧 API: http://46.101.193.107:8000"
echo "👤 Login with: leantna33 / 45234523nn"
