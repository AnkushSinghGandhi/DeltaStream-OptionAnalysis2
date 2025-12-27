#!/bin/bash
# Stop all services

set -e

echo "Stopping DeltaStream services..."
docker-compose down

echo "Services stopped."
