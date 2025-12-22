# File Sharing

```http
POST    /api/shares
GET     /api/shares/{share_id}
GET     /api/shares
PATCH   /api/shares/{share_id}
DELETE  /api/shares/{share_id}
GET     /api/shares/{share_token}
```

## Create Share Link

```http
POST    /api/shares
```

Request:

```json
Authorization: Bearer <access_token>
{
  "base_dir": "/Documents",
  "file_names": ["report.pdf", "summary.txt"],
  "permission": "read | download | write | upload",
  "password": "password", // Optional password for access control.
  "expired_at": "2025-10-25T00:00:00Z"
}
```

Response:

```json
{
  "share_id": 1,
  "user_id": 1,
  "token": "uuid", // Randomly generated UUID as the share link token.
  "base_dir": "/Documents",
  "file_names": ["report.pdf", "summary.txt"],
  "permission": "read",
  "requires_password": true,
  "expired_at": "2025-10-25T00:00:00Z",
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

## Get Share Link Info

```http
GET   /api/shares/{share_id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "share_id": 1,
  "user_id": 1,
  "token": "uuid", // Randomly generated UUID as the share link token.
  "base_dir": "/Documents",
  "file_names": ["report.pdf", "summary.txt"],
  "permission": "read",
  "requires_password": true,
  "expired_at": "2025-10-25T00:00:00Z",
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

## List Share Links

```http
GET   /api/shares
```

Request:

```json
Authorization: Bearer <access_token>
{
  "keyword": "docs", // matches base_dir or file_names
  "base_dir": "/Documents",
  "permission": "read | download | write | upload",
  "active_first": true,
  "sort_by": "permission | created | expires | updated",
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
      "share_id": 1,
      "user_id": 1,
      "token": "uuid",
      "base_dir": "/Documents",
      "file_names": ["report.pdf", "summary.txt"],
      "permission": "read",
      "requires_password": true,
      "expired_at": "2025-10-25T00:00:00Z",
      "created_at": "2025-10-25T00:00:00Z",
      "updated_at": "2025-10-25T00:00:00Z"
    }
  ]
}
```

## Update Share Link

```http
PATCH   /api/shares/{share_id}
```

Request:

```json
Authorization: Bearer <access_token>
{
  "base_dir": "/Documents",
  "file_names": ["report.pdf", "summary.txt"],
  "permission": "read | download | write | upload",
  "password": "password", // Optional password for access control.
  "expired_at": "2025-10-25T00:00:00Z"
}
```

Response:

```json
{
  "share_id": 1,
  "user_id": 1,
  "token": "uuid", // Randomly generated UUID as the share link token.
  "base_dir": "/Documents",
  "file_names": ["report.pdf", "summary.txt"],
  "permission": "read",
  "requires_password": true,
  "expired_at": "2025-10-25T00:00:00Z",
  "created_at": "2025-10-25T00:00:00Z",
  "updated_at": "2025-10-25T00:00:00Z"
}
```

## Delete Share Link

```http
DELETE  /api/shares/{share_id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "message": "Share link deleted."
}
```

## Get Link Info via Token

```http
GET     /api/shares/{token}
```

Request: Request body is empty.

Response:

```json
{
  "username": "user",
  "token": "uuid", // Randomly generated UUID as the share link token.
  "file_names": ["report.pdf", "summary.txt"],
  "permission": "read",
  "requires_password": true,
  "expired_at": "2025-10-25T00:00:00Z"
}
```
