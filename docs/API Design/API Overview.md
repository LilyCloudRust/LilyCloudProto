# API Overview

## Notes

* This is a API design document for prototyping, not intended for production use.
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

## File System

### File Operations

```http
GET     /api/files/list
GET     /api/files/info
GET     /api/files/search
POST    /api/files/directory
POST    /api/files/copy
POST    /api/files/move
DELETE  /api/files
```

### File Transfer

```http
POST    /api/files/upload
GET     /api/files
POST    /api/files/download
GET     /api/files/archive/{task_id}
```

### Trash Management

```http
POST    /api/files/trash
GET     /api/files/trash/{trash_id}
GET     /api/files/trash
POST    /api/files/trash/restore
DELETE  /api/files/trash
```

### File Operations Status

```http
GET     /api/files/tasks/{task_id}
```

## Administration

### User Management

```http
POST    /api/admin/users
GET     /api/admin/users/{user_id}
GET     /api/admin/users
PATCH   /api/admin/users/{user_id}
DELETE  /api/admin/users/{user_id}
```

### Storage Management

```http
POST    /api/admin/storages
GET     /api/admin/storages/{storage_id}
GET     /api/admin/storages
PATCH   /api/admin/storages/{storage_id}
DELETE  /api/admin/storages/{storage_id}
```

### Task Management

```http
GET     /api/admin/tasks
PATCH   /api/admin/tasks/{task_id}
DELETE  /api/admin/tasks/{task_id}
```

## References

* [AList GitHub repository](https://github.com/AlistGo/alist)
* [AList documentation](https://alistgo.com/)
* [Collection of example sites built with AList](https://linux.do/t/topic/63238)
* [Example site built with AList](https://cloud.lilywhite.cc/s/4ZUW)
* [AList API documentation reference](https://alist-public.apifox.cn/)
