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
# Usage:
#   make test                  # Run all tests
#   make test mod=app.module   # Run tests for a specific module/app
#   make test mod=app.module.tests.test_file  # Run tests in a specific file
#   make test mod=app.module.tests.test_file.TestClass  # Run tests in a specific class
#   make test mod=app.module.tests.test_file.TestClass.test_method  # Run a specific test
# Examples:
#   make test mod=app.core.utils  # Run all tests in the core utils module
#   make test mod=app.accounts.api.tests.test_views  # Run all tests in the accounts API views test file
#   make test mod=app.transactions.api.tests.test_payment_method_serializers.MobileMoneyPaymentMethodSerializerTestCase.test_mobile_money_payment_method_serializer_with_payment_method_type  # Run a specific test
test:
	@if [ -z "$(mod)" ]; then \
		docker compose -f local.yml exec django python manage.py test; \
	else \
		docker compose -f local.yml exec django python manage.py test $(mod) -v 2; \
	fi

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