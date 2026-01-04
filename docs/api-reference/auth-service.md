# Auth Service API

> **User authentication and authorization endpoints**

**Base URL**: `http://localhost:8000/api/auth`  
**Port**: 8001 (internal), accessed via API Gateway

---

## 📚 Endpoints

### 1. Register User

**Endpoint**: `POST /auth/register`

**Description**: Create a new user account

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "name": "John Doe"
}
```

**Response** (201 Created):
```json
{
  "message": "User registered successfully",
  "user_id": "507f1f77bcf86cd799439011"
}
```

**Errors**:
- `400`: Email or password missing
- `409`: User already exists

**Example**:
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}'
```

---

### 2. Login

**Endpoint**: `POST /auth/login`

**Description**: Authenticate user and receive JWT token

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response** (200 OK):
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**Errors**:
- `400`: Email or password missing
- `401`: Invalid credentials

**Example**:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

---

### 3. Verify Token

**Endpoint**: `POST /auth/verify`

**Description**: Verify JWT token validity

**Headers**:
```
Authorization: Bearer <token>
```

**Response** (200 OK):
```json
{
  "valid": true,
  "user_id": "507f1f77bcf86cd799439011",
  "email": "user@example.com"
}
```

**Errors**:
- `401`: Invalid or expired token
- `400`: Authorization header missing

**Example**:
```bash
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGci..."
```

---

### 4. Refresh Token

**Endpoint**: `POST /auth/refresh`

**Description**: Get a new JWT token

**Headers**:
```
Authorization: Bearer <old_token>
```

**Response** (200 OK):
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_at": "2025-01-03T15:30:00Z"
}
```

**Errors**:
- `401`: Invalid token

---

## 🔐 JWT Token Structure

**Header**:
```json
{
  "typ": "JWT",
  "alg": "HS256"
}
```

**Payload**:
```json
{
  "user_id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "exp": 1704295800
}
```

**Token Expiry**: 24 hours from issuance

---

## 🔒 Security

- Passwords hashed with **bcrypt** (12 rounds)
- Tokens signed with **HS256** algorithm
- Secret key stored in environment variable
- HTTPS recommended for production

---

## 📊 Common Workflows

### Registration → Login Flow
```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"pass123","name":"New User"}'

# 2. Login (get token)
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"pass123"}' \
  | jq -r '.token')

# 3. Use token for protected endpoints
curl http://localhost:8000/api/data/chains/NIFTY \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🧪 Testing

See [examples/curl-examples.sh](../../examples/curl-examples.sh) for complete test suite.

---

## 📚 Related Docs

- [API Gateway](api-gateway.md) - How requests are routed
- [Tutorial Chapter 4](../tutorials/complete-guide/chapter04.md) - Build this service
