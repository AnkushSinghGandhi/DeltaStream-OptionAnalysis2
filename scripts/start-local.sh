#!/bin/bash
# Start all services locally using docker-compose

set -e

echo "Starting Option ARO services..."

# Build images
echo "Building Docker images..."
docker-compose build

# Start services
echo "Starting services..."
docker-compose up -d

echo ""
echo "Services started!"
echo ""
echo "Service URLs:"
echo "  API Gateway:    http://localhost:8000"
echo "  Auth:           http://localhost:8001"
echo "  Socket Gateway: http://localhost:8002"
echo "  Storage:        http://localhost:8003"
echo "  Analytics:      http://localhost:8004"
echo "  Logging:        http://localhost:8005"
echo ""
echo "Infrastructure:"
echo "  Redis:          localhost:6379"
echo "  MongoDB:        localhost:27017"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop services: ./scripts/stop-local.sh"
