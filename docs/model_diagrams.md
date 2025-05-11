# Model Diagrams

This document explains how to generate visual diagrams from Django models in the Vulipay API project.

## Prerequisites

The diagram generation functionality uses:

1. **django-extensions** - Extended management commands for Django
2. **pydot** - Python interface to Graphviz's dot language
3. **graphviz** - Graph visualization software

These are already included in the project's `requirements/local.txt` and the Graphviz system package is automatically installed in the Docker container via the Dockerfile.

## Generating Diagrams

There are two ways to generate model diagrams:

### 1. Using Makefile Commands (Recommended)

The easiest way is to use the provided Makefile commands:

```bash
# Generate diagram for all models
make diagram

# Generate diagram for a specific app
make diagram-app app=accounts

# Generate diagram for specific models
make diagram-models models="accounts.User transactions.Transaction"

# Generate with custom format
make diagram format=svg

# Generate with custom output filename
make diagram-app app=transactions output=trans_models.png

# Exclude specific apps
make diagram exclude="admin contenttypes sessions"
```

All diagrams will be stored in the `diagrams/` directory, which is ignored by git.

### 2. Using django-extensions Directly

You can also use django-extensions' `graph_models` command directly if needed:

```bash
# Generate diagram for all apps
docker compose -f local.yml exec django python manage.py graph_models -a -g -o /app/diagrams/models.png

# Generate diagram for specific app
docker compose -f local.yml exec django python manage.py graph_models accounts -o /app/diagrams/accounts_models.png

# Generate diagram for specific models
docker compose -f local.yml exec django python manage.py graph_models accounts.User transactions.Transaction -o /app/diagrams/user_transactions.png

# Exclude specific apps
docker compose -f local.yml exec django python manage.py graph_models -a -e contenttypes sessions admin -o /app/diagrams/core_models.png
```

Remember to copy the files from the container to your host machine:

```bash
docker cp $(docker compose -f local.yml ps -q django):/app/diagrams/models.png ./diagrams/models.png
```

## Output Formats

You can generate diagrams in several formats:
- PNG (default)
- SVG
- PDF
- DOT (Graphviz source format)

## Customizing Diagrams

For advanced customization of diagrams, refer to the django-extensions documentation:
https://django-extensions.readthedocs.io/en/latest/graph_models.html

## Viewing the Diagrams

The generated diagram files will be saved in the project's `diagrams/` directory. You can:

1. View them directly in the folder
2. They are automatically copied from the Docker container to your host machine

## Troubleshooting

If you encounter issues generating diagrams:

1. Make sure the container was built with the latest Dockerfile that includes Graphviz
2. Verify django-extensions is added to INSTALLED_APPS in settings
3. Check that the pydot package is installed and working properly

For more detailed errors when using django-extensions directly, add the `-v` (verbosity) flag to your command:

```bash
docker compose -f local.yml exec django python manage.py graph_models -a -v 2
```