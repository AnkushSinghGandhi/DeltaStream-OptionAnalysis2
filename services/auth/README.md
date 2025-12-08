# Auth Service

## Overview

JWT-based authentication service for user registration, login, and token verification.

## Endpoints

### POST /register
Register new user.

**Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "token": "eyJ...",
  "user": {
    "id": "abc123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### POST /login
Login user.

**Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

### POST /verify
Verify JWT token.

**Headers:**
```
Authorization: Bearer <token>
```

### POST /refresh
Refresh JWT token.

## Security

- Passwords hashed with bcrypt
- JWT tokens with 24-hour expiration
- HTTPS recommended for production
- Change JWT_SECRET in production
