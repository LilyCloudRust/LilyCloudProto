# API Prototype Design

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
