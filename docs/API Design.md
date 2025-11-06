# API Prototype Design

## Notes

* This is a prototype API design document, not intended for production use.
* Only successful responses are shown.
* JWT Authentication usage is indicated by adding a JWT token to the Authorization header in the request.
* It is subject to change.
* Error messages should not contain a period.

## Authentication

```http
POST    /api/auth/login
POST    /api/auth/logout
POST    /api/auth/register
POST    /api/auth/refresh
GET     /api/auth/whoami
```

### User Login

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

### User Logout

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

### User Registration

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
  "user_id": 1
  "username": "string",
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

### Token Refresh

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

### User Profile

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
  "user_id": 1
  "username": "string",
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

## File System

### File Operations

```http
GET     /api/files/list
GET     /api/files/info
GET     /api/files/search
POST    /api/files/mkdir
POST    /api/files/copy
POST    /api/files/move
POST    /api/files/delete
GET     /api/files/task/{id}
```

## Administration

### User Management

```http
POST    /api/admin/users
GET     /api/admin/users/{id}
GET     /api/admin/users/list
GET     /api/admin/users/search
PATCH   /api/admin/users/{id}
DELETE  /api/admin/users/{id}
```

### Storage Management

```http
POST    /api/admin/storage
GET     /api/admin/storage/{id}
GET     /api/admin/storage/list
GET     /api/admin/storage/search
PATCH   /api/admin/storage/{id}
DELETE  /api/admin/storage/{id}

POST    /api/admin/storage/{id}/enable
POST    /api/admin/storage/{id}/disable
```

### Task Management

```http
GET     /api/admin/tasks
GET     /api/admin/storage/list
GET     /api/admin/storage/search
DELETE  /api/admin/tasks/{id}
PATCH   /api/admin/tasks/{id}
```

## References

* [AList GitHub repository](https://github.com/AlistGo/alist)
* [AList documentation](https://alistgo.com/)
* [Collection of example sites built with AList](https://linux.do/t/topic/63238)
* [Example site built with AList](https://cloud.lilywhite.cc/s/4ZUW)
* [AList API documentation reference](https://alist-public.apifox.cn/)
