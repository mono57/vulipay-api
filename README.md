# Vulipay API

## Overview
Vulipay API is a Django-based backend service for the Vulipay payment platform. It provides a secure and scalable infrastructure for handling payment processing, user authentication, and transaction management.

## Features
- User account management and authentication
- OTP-based verification via SMS, email, and WhatsApp
- Payment transaction processing and history
- Internationalization support
- RESTful API endpoints

## Technology Stack
- **Framework**: Django 5.1.6
- **Database**: PostgreSQL
- **Containerization**: Docker & Docker Compose
- **API**: Django REST Framework
- **Authentication**: JWT (JSON Web Tokens)

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Make (optional, for using Makefile commands)

### Getting Started
1. Clone the repository
   ```bash
   git clone <repository-url>
   cd vulipay-api
   ```

2. Build the Docker containers
   ```bash
   docker-compose -f local.yml build
   ```

3. Start the development server
   ```bash
   docker-compose -f local.yml up
   ```

4. Run migrations
   ```bash
   docker-compose -f local.yml run --rm django python manage.py migrate
   ```

5. Create a superuser (optional)
   ```bash
   docker-compose -f local.yml run --rm django python manage.py createsuperuser
   ```

### Common Commands

#### Running Tests
```bash
docker-compose -f local.yml run --rm django python manage.py test
```

#### Creating a New Django App
```bash
make create-app APP_NAME=your_app_name
```

#### Accessing the Django Shell
```bash
docker-compose -f local.yml run --rm django python manage.py shell
```

#### Database Migrations
```bash
# Make migrations
docker-compose -f local.yml run --rm django python manage.py makemigrations

# Apply migrations
docker-compose -f local.yml run --rm django python manage.py migrate
```

## Project Structure

### Main Directories
- `app/` - Main application directory
  - `accounts/` - User account management
  - `transactions/` - Payment transaction handling
  - `verify/` - User verification with OTP
- `config/` - Django project settings
- `compose/` - Docker Compose configuration
- `requirements/` - Python dependencies

### Key Files
- `local.yml` - Docker Compose configuration for local development
- `production.yml` - Docker Compose configuration for production
- `Makefile` - Utility commands for development
- `manage.py` - Django management script

## API Endpoints

### Authentication
- `POST /api/accounts/login/` - User login
- `POST /api/accounts/register/` - User registration

### Verification
- `POST /api/verify/generate/` - Generate OTP
- `POST /api/verify/verify/` - Verify OTP

### Transactions
- `GET /api/transactions/` - List transactions
- `POST /api/transactions/` - Create transaction
- `GET /api/transactions/{id}/` - Get transaction details

## Verify App

The `verify` app handles user verification through one-time passwords (OTPs). It supports multiple delivery channels:

### Features
- Generate and send OTPs via SMS, email, or WhatsApp
- Configurable OTP expiration time (default: 10 minutes)
- Limited verification attempts (default: 3)
- Automatic expiration of previous OTPs when generating new ones
- Progressive waiting periods between OTP requests to prevent abuse:
  - First request: No waiting period
  - Second request: 5 seconds
  - Third request: 30 seconds
  - Fourth request: 5 minutes
  - Fifth request: 30 minutes
  - Sixth request and beyond: 1 hour

### Usage Example

#### Generate OTP
```python
from app.verify.services import OTPService

# Generate OTP for phone number
result = OTPService.generate_otp("+237698765432", channel="sms")
if result['success']:
    otp = result['otp']
    expires_at = result['expires_at']
else:
    # Handle error
    if 'waiting_seconds' in result:
        # User needs to wait before requesting another OTP
        waiting_seconds = result['waiting_seconds']
        next_allowed_at = result['next_allowed_at']
        error_message = result['message']  # "Please wait X seconds before requesting a new OTP"
    else:
        # Other error
        error_message = result['message']

# Generate OTP for email
result = OTPService.generate_otp("user@example.com", channel="email")
```

#### Verify OTP
```python
from app.verify.services import OTPService

# Verify OTP
result = OTPService.verify_otp("+237698765432", "123456")
if result["success"]:
    # OTP verified successfully
    pass
else:
    # OTP verification failed
    error_message = result["message"]
```

### API Response Examples

#### Generate OTP Success
```json
{
  "success": true,
  "message": "Verification code sent to +237698765432 via sms.",
  "expires_at": "2023-03-08T12:34:56Z"
}
```

#### Generate OTP Waiting Period Error
```json
{
  "success": false,
  "message": "Please wait 30 seconds before requesting a new OTP.",
  "waiting_seconds": 30,
  "next_allowed_at": "2023-03-08T12:35:26Z"
}
```

#### Verify OTP Success
```json
{
  "success": true,
  "message": "OTP verified successfully."
}
```

#### Verify OTP Error
```json
{
  "success": false,
  "message": "Invalid code. 2 attempts remaining."
}
```

## Environment Variables

The application uses environment variables for configuration. Key variables include:

- `DATABASE_URL` - PostgreSQL connection string
- `DJANGO_SECRET_KEY` - Django secret key
- `DJANGO_ALLOWED_HOSTS` - Allowed hosts for production
- `DJANGO_DEBUG` - Debug mode (True/False)
- `OTP_EXPIRY_MINUTES` - Minutes until OTP expires (default: 10)
- `OTP_MAX_ATTEMPTS` - Maximum verification attempts (default: 3)
- `OTP_WAITING_PERIODS` - List of waiting periods in seconds (default: [0, 5, 30, 300, 1800, 3600])

## Deployment

### Production Setup
1. Configure environment variables in `.envs/.production/`
2. Build and start the production containers:
   ```bash
   docker-compose -f production.yml build
   docker-compose -f production.yml up -d
   ```

### Maintenance
- Database backups are stored in `backups/`
- Logs are available via Docker:
  ```bash
  docker-compose -f production.yml logs -f django
  ```

## Contributing

1. Create a feature branch from `develop`
2. Make your changes
3. Run tests to ensure everything works
4. Submit a pull request

## License

[Specify the license here]