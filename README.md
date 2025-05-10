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

#### Test Coverage
```bash
# Run tests with coverage
make test-coverage

# Generate coverage report in terminal
make test-coverage-report

# Generate HTML coverage report
make test-coverage-html
```
The HTML coverage report will be generated in the `htmlcov` directory. Open `htmlcov/index.html` in a browser to view the detailed coverage report.

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
- `POST /api/verify/verify/` - Verify OTP and get user details with tokens

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
- Returns user details and authentication tokens upon successful verification

### Usage Example

#### Generate OTP
```python
from app.verify.models import OTP

# Generate OTP for phone number
result = OTP.generate("+237698765432", channel="sms")
if result['success']:
    otp = result['otp']
    expires_at = result['expires_at']
    next_allowed_at = otp.next_otp_allowed_at  # When the next OTP can be requested
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
result = OTP.generate("user@example.com", channel="email")
```

#### Verify OTP
```python
from app.verify.api.serializers import VerifyOTPSerializer

# Create and validate the serializer
serializer = VerifyOTPSerializer(data={
    "phone_number": "698765432",
    "country_iso_code": "CM",
    "code": "123456"
})

if serializer.is_valid():
    # Verify OTP
    result = serializer.verify_otp()
    if result["success"]:
        # OTP verified successfully
        if "user" in result:
            # User details are available
            user_details = result["user"]
            # Access token for authentication
            access_token = result["tokens"]["access"]
            # Refresh token for getting new access tokens
            refresh_token = result["tokens"]["refresh"]
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
  "expires_at": "2023-03-08T12:34:56Z",
  "next_allowed_at": "2023-03-08T12:35:01Z"
}
```

#### Generate OTP Success (First Request)
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

#### Verify OTP Success (With User Details)
```json
{
  "success": true,
  "message": "OTP verified successfully.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "Test",
    "last_name": "User",
    "phone_number": "+237698765432",
    "account_id": 1
  },
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
}
```

#### Verify OTP Success (No User Found)
```json
{
  "success": true,
  "message": "OTP verified successfully, but no user found with this identifier."
}
```

#### Verify OTP Error
```json
{
  "success": false,
  "message": "Invalid code. 2 attempts remaining."
}
```

## Payment API Guide

The Payment API allows users to manage payment methods and view available payment method types. This guide demonstrates how to use the API with curl commands.

### Authentication Flow

First, you need to authenticate to get a JWT token:

```bash
# Generate an OTP
curl -X POST http://localhost:8000/api/v1/verify/generate/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com"}'

# Verify the OTP to get a JWT token
curl -X POST http://localhost:8000/api/v1/verify/verify/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","code":"YOUR_OTP_CODE"}'
```

The response will include access and refresh tokens:
```json
{
  "success": true,
  "message": "OTP verified successfully.",
  "user": {
    "full_name": "",
    "email": "your-email@example.com",
    "phone_number": null,
    "country": null
  },
  "tokens": {
    "access": "YOUR_ACCESS_TOKEN",
    "refresh": "YOUR_REFRESH_TOKEN"
  }
}
```

### List Payment Method Types

Before creating a payment method, you need to know the available payment method types:

```bash
curl -X GET http://localhost:8000/api/v1/transactions/payment-method-types/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

You can also filter by country:

```bash
curl -X GET "http://localhost:8000/api/v1/transactions/payment-method-types/?country_code=CM" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Create a Card Payment Method

Use the payment method type ID from the previous step:

```bash
curl -X POST http://localhost:8000/api/v1/transactions/payment-methods/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "card",
    "cardholder_name": "John Doe",
    "card_number": "4111111111111111",
    "expiry_date": "12/2025",
    "cvv": "123",
    "billing_address": "123 Main St, City, Country",
    "payment_method_type": 1,
    "default_method": true
  }'
```

Response:
```json
{
  "id": 6,
  "default_method": true,
  "cardholder_name": "John Doe",
  "masked_card_number": "**** **** **** 1111",
  "expiry_date": "12/2025",
  "cvv_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
  "billing_address": "123 Main St, City, Country"
}
```

### Create a Mobile Money Payment Method

```bash
curl -X POST http://localhost:8000/api/v1/transactions/payment-methods/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "mobile_money",
    "provider": "MTN Mobile Money",
    "mobile_number": "+237671234567",
    "payment_method_type": 2,
    "default_method": false
  }'
```

Response:
```json
{
  "id": 7,
  "default_method": false,
  "provider": "MTN Mobile Money",
  "mobile_number": "+237671234567"
}
```

Note: The mobile number must be in a valid E.164 format (e.g., +237671234567).

### List All Payment Methods

```bash
curl -X GET http://localhost:8000/api/v1/transactions/payment-methods/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

Response:
```json
[
  {
    "id": 6,
    "type": "card",
    "default_method": true,
    "cardholder_name": "John Doe",
    "masked_card_number": "**** **** **** 1111",
    "expiry_date": "12/2025"
  },
  {
    "id": 7,
    "type": "mobile_money",
    "default_method": false,
    "provider": "MTN Mobile Money",
    "mobile_number": "+237671234567"
  }
]
```

### Get Details of a Specific Payment Method

```bash
curl -X GET http://localhost:8000/api/v1/transactions/payment-methods/6/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "id": 6,
  "type": "card",
  "default_method": true,
  "cardholder_name": "John Doe",
  "masked_card_number": "**** **** **** 1111",
  "expiry_date": "12/2025"
}
```

### Important Notes

1. **Security**: The API properly masks sensitive information like card numbers and securely hashes CVV values.

2. **Required Fields**: Different payment method types have different required fields:
   - Card payments require: cardholder_name, card_number, expiry_date, cvv, billing_address
   - Mobile money payments require: provider, mobile_number

3. **Phone Number Format**: Mobile numbers must be in E.164 format (e.g., +237671234567)

4. **Authentication**: All endpoints except the OTP generation and verification require a valid JWT token.

5. **Default Method**: You can set a payment method as the default by setting `default_method: true`. Only one payment method can be the default.

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

## Wallet Currencies

Wallets in the system now support currency assignment. This feature allows each wallet to be associated with a specific currency, which is normally determined by the user's country.

### How It Works

- When a new user is created, the system automatically creates a main wallet for them and assigns a currency based on the user's country.
- When a new wallet is created, the system attempts to assign a currency to it based on the user's country.
- The currency is stored as a simple text field (e.g., "USD", "EUR", "XAF").
- The system determines the currency in the following priority:
  1. If the country has a currency field set, that value is used
  2. If not, the system uses a built-in mapping of common country codes to their currency codes:
     - Cameroon (CM) → XAF (CFA Franc)
     - United States (US) → USD (US Dollar)
     - United Kingdom (GB) → GBP (British Pound)
     - European Union (EU) → EUR (Euro)
     - And many others
  3. If the country code doesn't match any known currency code, the system falls back to a default format: "{COUNTRY_CODE} Currency"
- If no country is set for the user, the wallet's currency remains null.
- You can also explicitly set a currency when creating a wallet, which will override the automatic assignment.

### Country Currency Configuration

Each country in the system can have a default currency assigned to it by setting the `currency` field in the `AvailableCountry` model. This allows for fine-grained control over which currency is used for each country, without needing to rely on the built-in mappings.

### API Interaction

When creating or updating wallets via API, the currency field can be specified explicitly as a string. If not provided, the system will try to set it automatically based on the user's country as described above.

## Admin Authentication Token Feature

The Django admin interface includes a feature to generate and copy authentication tokens for users. This is useful for testing and debugging API endpoints.

### How to use:

1. Log in to the Django admin interface with admin credentials
2. In the top-right corner of the admin interface, you'll see a "Get Auth Token" link next to the "Log out" link
3. Click on "Get Auth Token" to open the token generation modal
4. Select a user from the dropdown (if you're a superuser, you'll see all users)
5. Click "Generate Token" to create a new token for the selected user
6. Use the "Copy" button to copy the access token or refresh token
7. Use the token in your API requests with the Bearer authentication scheme: `Authorization: Bearer <token>`

This feature is only available to admin users and is intended for development and testing purposes.