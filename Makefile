.PHONY: build up down logs shell django-shell migrate makemigrations test test-coverage test-coverage-html clean create-app diagram diagram-app diagram-models

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
# Usage:
#   make logs           # View logs for all services
#   make logs srv=<service>  # View logs for a specific service
# Examples:
#   make logs           # View all logs
#   make logs srv=django     # View logs for the django service
#   make logs srv=db         # View logs for the database service
logs:
	@if [ -z "$(srv)" ]; then \
		docker compose -f local.yml logs -f; \
	else \
		docker compose -f local.yml logs -f $(srv); \
	fi

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

# Generate diagram for all models
# Usage:
#   make diagram                               # Generate diagram for all apps in PNG format
#   make diagram format=svg                    # Generate diagram in SVG format
#   make diagram output=custom_models.png      # Specify custom output filename
#   make diagram exclude="admin sessions"      # Exclude specific apps from diagram
diagram:
	@mkdir -p diagrams
	@echo "Generating diagram for all models..."
	@FILENAME=$(if $(output),$(output),models.$(if $(format),$(format),png)); \
	docker compose -f local.yml exec django mkdir -p /app/diagrams; \
	docker compose -f local.yml exec django python manage.py graph_models -a -g \
		$(if $(exclude),-e $(exclude),) \
		-o /app/diagrams/$$FILENAME; \
	docker cp $$(docker compose -f local.yml ps -q django):/app/diagrams/$$FILENAME ./diagrams/$$FILENAME; \
	echo "Generated diagram: diagrams/$$FILENAME"

# Generate diagram for a specific app
# Usage:
#   make diagram-app app=accounts              # Generate diagram for accounts app
#   make diagram-app app=transactions format=svg output=trans.svg  # Custom format and filename
diagram-app:
	@mkdir -p diagrams
	@if [ -z "$(app)" ]; then \
		echo "Error: app parameter is required. Usage: make diagram-app app=your_app_name"; \
		exit 1; \
	fi
	@echo "Generating diagram for app: $(app)..."
	@FILENAME=$(if $(output),$(output),$(app)_models.$(if $(format),$(format),png)); \
	docker compose -f local.yml exec django mkdir -p /app/diagrams; \
	docker compose -f local.yml exec django python manage.py graph_models $(app) \
		-o /app/diagrams/$$FILENAME; \
	docker cp $$(docker compose -f local.yml ps -q django):/app/diagrams/$$FILENAME ./diagrams/$$FILENAME; \
	echo "Generated diagram: diagrams/$$FILENAME"

# Generate diagram for specific models
# Usage:
#   make diagram-models models="accounts.User transactions.Transaction"  # Generate diagram for specific models
#   make diagram-models models="accounts.User" output=user_model.svg format=svg  # Custom format and filename
diagram-models:
	@mkdir -p diagrams
	@if [ -z "$(models)" ]; then \
		echo "Error: models parameter is required. Usage: make diagram-models models=\"app.Model1 app.Model2\""; \
		exit 1; \
	fi
	@echo "Generating diagram for models: $(models)..."
	@FILENAME=$(if $(output),$(output),models_selection.$(if $(format),$(format),png)); \
	docker compose -f local.yml exec django mkdir -p /app/diagrams; \
	docker compose -f local.yml exec django python manage.py graph_models $(models) \
		-o /app/diagrams/$$FILENAME; \
	docker cp $$(docker compose -f local.yml ps -q django):/app/diagrams/$$FILENAME ./diagrams/$$FILENAME; \
	echo "Generated diagram: diagrams/$$FILENAME"