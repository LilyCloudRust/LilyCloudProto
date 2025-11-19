# Authentication

```http
POST    /api/auth/login
POST    /api/auth/logout
POST    /api/auth/register
POST    /api/auth/refresh
GET     /api/auth/whoami
```

## User Login

```http
POST    /api/auth/login
```

Request:

```json
{
  "username": "string",
  "password": "string"
}
```

Response:

```json
{
  "access_token": "string",
  "refresh_token": "string"
}
```

## User Logout

```http
POST    /api/auth/logout
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "message": "Logout successful"
}
```

## User Registration

```http
POST    /api/auth/register
```

Request:

```json
{
  "username": "string",
  "password": "string"
}
```

Response:

```json
{
  "user_id": 1,
  "username": "string",
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

## Token Refresh

```http
POST    /api/auth/refresh
```

Request:

```json
Authorization: Bearer <access_token>
{
  "refresh_token": "string"
}
```

Response:

```json
{
  "access_token": "string"
}
```

## User Profile

```http
GET     /api/auth/whoami
```

Request:

```http
Authorization: Bearer <access_token>
```

Response:

```json
{
  "user_id": 1,
  "username": "string",
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```
