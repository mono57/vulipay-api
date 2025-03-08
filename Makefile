.PHONY: build up down logs shell django-shell migrate makemigrations test test-coverage test-coverage-html clean create-app

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

# Run tests with coverage
test-coverage:
	docker compose -f local.yml exec django coverage run --source=app manage.py test

# Run tests with coverage report
test-coverage-report:
	docker compose -f local.yml exec django coverage report -m

# Run tests with coverage and generate HTML report
test-coverage-html:
	docker compose -f local.yml exec django coverage run --source=app manage.py test
	docker compose -f local.yml exec django coverage html

# Clean up volumes and containers
clean:
	docker compose -f local.yml down -v

# Create a new Django app
# Usage: make create-app APP_NAME=your_app_name
create-app:
	@if [ -z "$(APP_NAME)" ]; then \
		echo "Error: APP_NAME is required. Usage: make create-app APP_NAME=your_app_name"; \
		exit 1; \
	fi
	docker compose -f local.yml exec django python manage.py startapp $(APP_NAME)
	@echo "Django app '$(APP_NAME)' created successfully."