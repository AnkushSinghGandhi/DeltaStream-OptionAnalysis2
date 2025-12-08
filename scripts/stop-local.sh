#!/bin/bash
# Stop all services

set -e

echo "Stopping Option ARO services..."
docker-compose down

echo "Services stopped."
