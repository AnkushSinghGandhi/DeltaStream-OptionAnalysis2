# Makefile for DeltaStream - Option Analysis

.PHONY: help build up down restart logs test lint clean

help:
	@echo "DeltaStream - Option Analysis - Available Commands:"
	@echo "  make build       - Build all Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs from all services"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters"
	@echo "  make clean       - Clean up containers and volumes"
	@echo "  make shell-api   - Open shell in api-gateway"
	@echo "  make shell-worker - Open shell in worker"

build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting services..."
	docker-compose up -d
	@echo "Services started! Use 'make logs' to view logs"

down:
	@echo "Stopping services..."
	docker-compose down

restart:
	@echo "Restarting services..."
	docker-compose restart

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api-gateway

logs-worker:
	docker-compose logs -f worker-enricher

logs-feed:
	docker-compose logs -f feed-generator

logs-socket:
	docker-compose logs -f socket-gateway

test:
	@echo "Running tests..."
	pytest tests/ -v

lint:
	@echo "Running linters..."
	flake8 services/ tests/
	black --check services/ tests/

format:
	@echo "Formatting code..."
	black services/ tests/

clean:
	@echo "Cleaning up..."
	docker-compose down -v
	rm -rf logs/*

shell-api:
	docker-compose exec api-gateway /bin/sh

shell-worker:
	docker-compose exec worker-enricher /bin/sh

shell-redis:
	docker-compose exec redis redis-cli

shell-mongo:
	docker-compose exec mongodb mongosh deltastream
