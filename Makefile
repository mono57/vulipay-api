.PHONY: build up down logs shell django-shell migrate makemigrations test clean

# Default target
all: build up

# Build the containers
build:
	docker compose -f local.yml build

# Start the containers
up:
	docker compose -f local.yml up -d

# Stop the containers
down:
	docker compose -f local.yml down

# View logs
logs:
	docker compose -f local.yml logs -f

# Open shell in django container
shell:
	docker compose -f local.yml exec django /bin/bash

# Open Django shell
django-shell:
	docker compose -f local.yml exec django python manage.py shell

# Run migrations
migrate:
	docker compose -f local.yml exec django python manage.py migrate

# Make migrations
makemigrations:
	docker compose -f local.yml exec django python manage.py makemigrations

# Run tests
test:
	docker compose -f local.yml exec django python manage.py test

# Clean up volumes and containers
clean:
	docker compose -f local.yml down -v