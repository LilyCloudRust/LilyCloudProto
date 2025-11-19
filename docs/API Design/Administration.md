# Administration

## User Management

```http
POST    /api/admin/users
GET     /api/admin/users/{user_id}
GET     /api/admin/users
PATCH   /api/admin/users/{user_id}
DELETE  /api/admin/users/{user_id}
```

### Create User

```http
POST    /api/admin/users
```

Request:

```json
Authorization: Bearer <access_token>
{
  "username": "string",
  "password": "string",
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

### Get User

```http
GET     /api/admin/users/{user_id}
```

Request:

```json
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

### List Users

```http
GET     /api/admin/users
```

Request:

```json
Authorization: Bearer <access_token>
{
  "keyword": "string",
  "page": 1,
  "page_size": 20,
  "sort_by": "username | created_at | updated_at",
  "sort_order": "asc | desc"
}
```

Response:

```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "user_id": 1,
      "username": "string",
      "created_at": "2025-10-25T00:00:00Z",
      "updated_at": "2025-10-25T00:00:00Z"
    }
  ]
}
```

### Update User

```http
PATCH   /api/admin/users/{user_id}
```

Request:

```json
Authorization: Bearer <access_token>
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

### Delete User

```http
DELETE  /api/admin/users/{user_id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "message": "User deleted successfully"
}
```

## Storage Management

```http
POST    /api/admin/storages
GET     /api/admin/storages/{storage_id}
GET     /api/admin/storages
PATCH   /api/admin/storages/{storage_id}
DELETE  /api/admin/storages/{storage_id}
```

### Create Storage

```http
POST    /api/admin/storages
```

Request:

```json
Authorization: Bearer <access_token>
{
  "mount_path": "/local",
  "type": "local",
  "config": {
    // Type-specific configuration.
    "root_path": "/var/lib/lilycloud"
  }
}
```

Response:

```json
{
  "storage_id": 1,
  "mount_path": "/local",
  "type": "local",
  "config": {
    // Type-specific configuration.
    "root_path": "/var/lib/lilycloud"
  },
  "enabled": true,
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

### Get Storage

```http
GET     /api/admin/storages/{storage_id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "storage_id": 1,
  "mount_path": "/local",
  "type": "local",
  "config": {
    // Type-specific configuration.
    "root_path": "/var/lib/lilycloud"
  },
  "enabled": true,
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

### List Storages

Request:

```json
Authorization: Bearer <access_token>
{
  "keyword": "local",
  "page": 1,
  "page_size": 20,
  "sort_by": "mount_path | type | created_at | updated_at",
  "sort_order": "asc | desc",
  "enabled_first": true
}
```

Response:

```json
{
  "total_count": 100,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "storage_id": 1,
      "mount_path": "/local",
      "type": "local",
      "config": {
        // Type-specific configuration.
        "root_path": "/var/lib/lilycloud"
      },
      "enabled": true,
      "created_at": "2025-10-25T00:00:00Z",
      "updated_at": "2025-10-25T00:00:00Z"
    }
  ]
}
```

### Update Storage

```http
PATCH   /api/admin/storages/{storage_id}
```

Request:

```json
Authorization: Bearer <access_token>
{
  "mount_path": "/local",
  "type": "local",
  "config": {
    // Type-specific configuration.
    "root_path": "/var/lib/lilycloud"
  },
  "enabled": true
}
```

Response:

```json
{
  "storage_id": 1,
  "mount_path": "/local",
  "type": "local",
  "config": {
    // Type-specific configuration.
    "root_path": "/var/lib/lilycloud"
  },
  "enabled": true,
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

### Delete Storage

```http
DELETE  /api/admin/storages/{storage_id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "message": "Storage deleted successfully"
}
```

## Task Management

```http
GET     /api/admin/tasks
DELETE  /api/admin/tasks/{task_id}
PATCH   /api/admin/tasks/{task_id}
```
