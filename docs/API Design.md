# API Prototype Design

## Notes

- This is a prototype API design document, not intended for production use.
- Only successful responses are shown.
- JWT Authentication usage is indicated by adding a JWT token to the Authorization header in the request.
- It is subject to change.
- Error messages should not contain a period.

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

#### List Files

```http
GET   /api/files/list
```

Request:

```json
Authorization: Bearer <access_token>
{
  "path": "/Documents",
  "sort_by": "name | size | created | modified | accessed | type",
  "sort_order": "asc | desc",
  "dir_first": true
}
```

Note: Sort by "type" option stands for sorting by mime type.

Response:

```json
{
  "path": "/Documents",
  "total": 100,
  "items": [
    {
      "name": "photos",
      "path": "/Documents/photos",
      "type": "directory",
      "size": 0, // In bytes.
      "mime_type": null,
      "created_at": "2025-10-25T00:00:00Z",
      "modified_at": "2025-10-25T00:00:00Z",
      "accessed_at": "2025-10-25T00:00:00Z"
    },
    {
      "name": "report.pdf",
      "path": "/Documents/report.pdf",
      "type": "file",
      "size": 2048576, // In bytes.
      "mime_type": "application/pdf",
      "created_at": "2025-10-25T00:00:00Z",
      "modified_at": "2025-10-25T00:00:00Z",
      "accessed_at": "2025-10-25T00:00:00Z"
    }
  ]
}
```

#### Get File Info

```http
GET     /api/files/info
```

Request:

```json
Authorization: Bearer <access_token>
{
  "path": "/Documents/report.pdf"
}
```

Response:

```json
{
  "name": "report.pdf",
  "path": "/Documents/report.pdf",
  "type": "file",
  "size": 2048576, // In bytes.
  "mime_type": "application/pdf",
  "created_at": "2025-10-25T00:00:00Z",
  "modified_at": "2025-10-25T00:00:00Z",
  "accessed_at": "2025-10-25T00:00:00Z"
}
```

#### Search Files

```http
GET    /api/files/search
```

Request:

```json
Authorization: Bearer <access_token>
{
  "keyword": "string",
  "path": "/Documents",
  "recursive": true,
  "type": "file", // Optional: filter by type.
  "mime_type": "application/pdf", // Optional: filter by MIME type.
  "sort_by": "name | size | created | modified | accessed | type",
  "sort_order": "asc | desc",
  "dir_first": true
}
```

Note: Sort by "type" option stands for sorting by mime type.

Response:

```json
{
  "path": "/Documents",
  "total": 100,
  "items": [
    {
      "name": "photos",
      "path": "/Documents/photos",
      "type": "directory",
      "size": 0, // In bytes.
      "mime_type": null,
      "created_at": "2025-10-25T00:00:00Z",
      "modified_at": "2025-10-25T00:00:00Z",
      "accessed_at": "2025-10-25T00:00:00Z"
    },
    {
      "name": "report.pdf",
      "path": "/Documents/report.pdf",
      "type": "file",
      "size": 2048576, // In bytes.
      "mime_type": "application/pdf",
      "created_at": "2025-10-25T00:00:00Z",
      "modified_at": "2025-10-25T00:00:00Z",
      "accessed_at": "2025-10-25T00:00:00Z"
    }
  ]
}
```

#### Create Directory

```http
POST    /api/files/mkdir
```

Request:

```json
Authorization: Bearer <access_token>
{
  "path": "/Documents/Repositories/LilyCloud",
  "parents": false // Whether to create parent directories if missing.
}
```

Response:

```json
{
  "name": "LilyCloud",
  "path": "/Documents/Repositories/LilyCloud",
  "type": "directory",
  "created_at": "2025-10-25T00:00:00Z",
  "modified_at": "2025-10-25T00:00:00Z",
  "accessed_at": "2025-10-25T00:00:00Z"
}
```

#### Copy Files

```http
POST    /api/files/copy
```

Request:

```json
Authorization: Bearer <access_token>
{
  "src_dir": "/Pictures",
  "dst_dir": "/Documents",
  "file_names": ["report.pdf", "presentation.pptx"]
}
```

Response:

```json
{}
```

#### Move Files

```http
POST    /api/files/move
```

Request:

```json
Authorization: Bearer <access_token>
{
  "src_dir": "/Pictures",
  "dst_dir": "/Documents",
  "file_names": ["report.pdf", "presentation.pptx"]
}
```

Response:

```json
{}
```

#### Delete Files

```http
POST    /api/files/delete
```

Request:

```json
Authorization: Bearer <access_token>
{
  "dir": "string",
  "file_names": ["report.pdf", "presentation.pptx"]
}
```

Response:

```json
{}
```

### File Transfer

```http
GET     /api/files/download
```

```http
PUT     /api/files/upload
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

#### Create User

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

#### Get User

```http
GET     /api/admin/users/{id}
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

#### List Users

```http
GET     /api/admin/users/list
```

Request:

```json
Authorization: Bearer <access_token>
{
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

#### Search Users

```http
GET     /api/admin/users/search
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

#### Update User

```http
PATCH   /api/admin/users/{id}
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

#### Delete User

```http
DELETE  /api/admin/users/{id}
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

### Storage Management

```http
POST    /api/admin/storage
GET     /api/admin/storage/{id}
GET     /api/admin/storage/list
GET     /api/admin/storage/search
PATCH   /api/admin/storage/{id}
DELETE  /api/admin/storage/{id}
```

#### Create Storage

```http
POST    /api/admin/storage
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

#### Get Storage

```http
GET     /api/admin/storage/{id}
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

#### List Storages

```http
GET     /api/admin/storage/list
```

Request:

```json
Authorization: Bearer <access_token>
{
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

#### Search Storages

```http
GET     /api/admin/storage/search
```

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

#### Update Storage

```http
PATCH   /api/admin/storage/{id}
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

#### Delete Storage

```http
DELETE  /api/admin/storage/{id}
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

### Task Management

```http
GET     /api/admin/tasks
GET     /api/admin/storage/list
GET     /api/admin/storage/search
DELETE  /api/admin/tasks/{id}
PATCH   /api/admin/tasks/{id}
```

## Database Design

### Users Table

- Table name: `users`
- Description: Stores user account information.

| Column            | Type        | Description              |
| ----------------- | ----------- | ------------------------ |
| `user_id`         | `INTEGER`   | Primary key              |
| `username`        | `VARCHAR`   | Unique username          |
| `hashed_password` | `VARCHAR`   | Hashed password          |
| `created_at`      | `TIMESTAMP` | Timestamp of creation    |
| `updated_at`      | `TIMESTAMP` | Timestamp of last update |

### Storage Table

- Table name: `storages`
- Description: Stores information about file storage locations.

| Column       | Type        | Description                             |
| ------------ | ----------- | --------------------------------------- |
| `storage_id` | `INTEGER`   | Primary key                             |
| `mount_path` | `VARCHAR`   | Mount path of the storage               |
| `type`       | `ENUM`      | Type of storage (local, onedrive, etc.) |
| `config`     | `JSON`      | Configuration settings                  |
| `enabled`    | `BOOLEAN`   | Whether the storage is enabled          |
| `created_at` | `TIMESTAMP` | Timestamp of creation                   |
| `updated_at` | `TIMESTAMP` | Timestamp of last update                |

### Tasks Table

- Table name: `tasks`
- Description: Stores file operation task records.

| Column         | Type        | Description                                       |
| -------------- | ----------- | ------------------------------------------------- |
| `task_id`      | `INTEGER`   | Primary key                                       |
| `user_id`      | `INTEGER`   | Foreign key referencing `users`                   |
| `type`         | `ENUM`      | Task type (copy, move, delete)                    |
| `src_path`     | `TEXT`      | Source path                                       |
| `dst_path`     | `TEXT`      | Destination path (for copy/move)                  |
| `file_names`   | `JSON`      | List of file names involved                       |
| `status`       | `ENUM`      | Task status (pending, running, completed, failed) |
| `progress`     | `FLOAT`     | Progress percentage (0.00 - 100.00)               |
| `message`      | `TEXT`      | Additional information or error messages          |
| `created_at`   | `TIMESTAMP` | Timestamp when the task was created               |
| `started_at`   | `TIMESTAMP` | Timestamp when the task started                   |
| `completed_at` | `TIMESTAMP` | Timestamp when the task completed                 |
| `updated_at`   | `TIMESTAMP` | Timestamp when the task was last updated          |

## References

- [AList GitHub repository](https://github.com/AlistGo/alist)
- [AList documentation](https://alistgo.com/)
- [Collection of example sites built with AList](https://linux.do/t/topic/63238)
- [Example site built with AList](https://cloud.lilywhite.cc/s/4ZUW)
- [AList API documentation reference](https://alist-public.apifox.cn/)
