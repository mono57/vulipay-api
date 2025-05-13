# API Response Utilities

This module provides a standardized way to format API responses across the application. It ensures that all API responses follow a consistent structure, making the API more predictable and easier to use for clients.

## Response Structure

All API responses follow this structure:

```json
{
  "message": "Human-readable message",
  "data": {...} | null,
  "error_code": null | "ERROR_CODE",
  "errors": null | {...}
}
```

### Fields

- `message`: A human-readable message describing the result
- `data`: The response data (for successful requests) or null (for errors)
- `error_code`: A string code identifying the error type (null for successful requests)
- `errors`: Detailed validation or other errors (null for successful requests)

## Utilities

### Response Functions

The `responses.py` module provides three main functions:

#### `success_response(message, data=None, status_code=200)`

Creates a standardized success response.

```python
from app.core.utils.responses import success_response

# Basic success response
response = success_response("User created successfully")

# Success response with data
response = success_response(
    message="User created successfully",
    data={"id": user.id, "email": user.email},
    status_code=status.HTTP_201_CREATED
)
```

#### `error_response(message, errors=None, error_code=None, status_code=400)`

Creates a standardized error response.

```python
from app.core.utils.responses import error_response

# Basic error response
response = error_response("User not found")

# Error response with error code
response = error_response(
    message="User does not have permission",
    error_code="PERMISSION_DENIED",
    status_code=status.HTTP_403_FORBIDDEN
)

# Error response with detailed errors
response = error_response(
    message="Invalid request",
    errors={"field1": ["Error message"], "field2": ["Another error"]},
    error_code="INVALID_REQUEST",
    status_code=status.HTTP_400_BAD_REQUEST
)
```

#### `validation_error_response(message="Validation failed", errors=None, status_code=400)`

Creates a standardized validation error response with error_code set to "VALIDATION_ERROR".

```python
from app.core.utils.responses import validation_error_response

# Validation error response
response = validation_error_response(
    message="Validation failed",
    errors=serializer.errors,
    status_code=status.HTTP_400_BAD_REQUEST
)
```

### Exception Handler

The custom exception handler in `exception_handler.py` automatically formats exceptions according to the standard response structure. It handles common DRF exceptions, Django exceptions, and unhandled exceptions.

The exception handler is registered in the Django REST Framework settings in `config/settings/base.py`:

```python
REST_FRAMEWORK = {
    # ... other settings ...
    "EXCEPTION_HANDLER": "app.core.utils.exception_handler.exception_handler",
}
```

## Usage Examples

### In a View

```python
from rest_framework import status
from rest_framework.views import APIView
from app.core.utils.responses import success_response, validation_error_response

class UserCreateView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return success_response(
                message="User created successfully",
                data={"id": user.id, "email": user.email},
                status_code=status.HTTP_201_CREATED
            )
        return validation_error_response(
            message="Invalid user data",
            errors=serializer.errors
        )
```

### With Exception Handler

With the exception handler registered, all exceptions are automatically formatted according to the standard response structure:

```python
# If a user tries to access a resource they don't have permission for,
# the response will look like:
{
  "message": "Permission denied",
  "data": null,
  "error_code": "PERMISSION_DENIED",
  "errors": null
}

# If a validation error occurs, the response will look like:
{
  "message": "Validation failed",
  "data": null,
  "error_code": "VALIDATION_ERROR",
  "errors": {
    "email": ["This field is required"],
    "password": ["This field is required"]
  }
}
```

## Testing

Run the tests for the response utilities and exception handler:

```bash
make test mod=app.core.utils.test_responses
make test mod=app.core.utils.test_exception_handler
```