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
  "sort_by": "username | created | updated",
  "sort_order": "asc | desc",
  "page": 1,
  "page_size": 20
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
  "message": "User deleted successfully."
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
  "sort_by": "mount_path | type | created | updated",
  "sort_order": "asc | desc",
  "enabled_first": true,
  "page": 1,
  "page_size": 20
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
  "message": "Storage deleted successfully."
}
```

## Task Management

```http
POST    /api/admin/tasks
GET     /api/admin/tasks
PATCH   /api/admin/tasks/{task_id}
DELETE  /api/admin/tasks/{task_id}
```

Note: CUD operations on tasks are not allowed, as tasks are managed by the system and should not be modified directly, these endpoints are provided for testing and debugging purposes.

## Create Task

```http
POST    /api/admin/tasks
```

Request:

```json
Authorization: Bearer <access_token>
{
  "type": "copy",
  "src_dir": "/Pictures",
  "dst_dirs": ["/Documents"],
  "file_names": ["report.pdf", "presentation.pptx"],
  "status": "pending",
  "progress": 0.0,
  "message": "",
}
```

Response

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "copy",
  "src_dir": "/Pictures",
  "dst_dirs": ["/Documents"],
  "file_names": ["report.pdf", "presentation.pptx"],
  "status": "pending",
  "progress": 0.0,
  "message": "",
  "created_at": "2025-10-25T00:00:00Z",
  "started_at": null,
  "completed_at": null,
  "updated_at": "2025-10-25T00:00:00Z"
}
```

## List Tasks

```http
GET     /api/admin/tasks
```

Request:

```json
Authorization: Bearer <access_token>
{
  "keyword": "string",
  "user_id": 1,
  "type": "copy",
  "status": "pending",
  "sort_by": "type | src | status | created | started | completed | updated",
  "sort_order": "asc | desc",
  "page": 1,
  "page_size": 20
}
```

## Response

```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "task_id": 1,
      "user_id": 1,
      "type": "copy",
      "src_dir": "/Pictures",
      "dst_dirs": ["/Documents"],
      "file_names": ["report.pdf", "presentation.pptx"],
      "status": "pending",
      "progress": 0.0,
      "message": "",
      "created_at": "2025-10-25T00:00:00Z",
      "started_at": null,
      "completed_at": null,
      "updated_at": "2025-10-25T00:00:00Z"
    }
  ]
}
```

## Update Task

```http
PATCH   /api/admin/tasks/{task_id}
```

Request:

```json
Authorization: Bearer <access_token>
{
  "user_id": 1,
  "type": "copy",
  "src_dir": "/Pictures",
  "dst_dirs": ["/Documents"],
  "file_names": ["report.pdf", "presentation.pptx"],
  "status": "pending",
  "progress": 0.0,
  "message": "",
  "started_at": "2025-10-25T00:00:00Z",
  "completed_at": "2025-10-25T00:00:00Z"
}
```

Response

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "copy",
  "src_dir": "/Pictures",
  "dst_dirs": ["/Documents"],
  "file_names": ["report.pdf", "presentation.pptx"],
  "status": "pending",
  "progress": 0.0,
  "message": "",
  "created_at": "2025-10-25T00:00:00Z",
  "started_at": "2025-10-25T00:00:00Z",
  "completed_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

## Delete Task

```http
DELETE  /api/admin/tasks/{task_id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "message": "Task deleted successfully."
}
```
