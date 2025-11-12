# File System

## File Operations

```http
GET     /api/files
GET     /api/files
GET     /api/files
POST    /api/files/directory
POST    /api/files/copy
POST    /api/files/move
DELETE  /api/files
```

### List Files

```http
GET     /api/files
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

### Get File Info

```http
GET     /api/files
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

### Search Files

```http
GET     /api/files
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

### Create Directory

```http
POST    /api/files/directory
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

### Copy Files

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
{
  "task_id": 1,
  "user_id": 1,
  "type": "copy",
  "src_path": "/Pictures",
  "dst_path": "/Documents",
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

### Move Files

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
{
  "task_id": 1,
  "user_id": 1,
  "type": "move",
  "src_path": "/Pictures",
  "dst_path": "/Documents",
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

### Delete Files

```http
DELETE  /api/files
```

Note: This endpoint is used to delete files permanently.

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
{
  "task_id": 1,
  "user_id": 1,
  "type": "delete",
  "src_path": "/Pictures",
  "dst_path": null,
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

## File Transfer

```http
GET     /api/files
PUT     /api/files/upload
```

## Trash Management

```http
POST    /api/files/trash
GET     /api/files/trash/{id}
GET     /api/files/trash
GET     /api/files/trash
POST    /api/files/trash/restore
DELETE  /api/files/trash/{id}
DELETE  /api/files/trash
DELETE  /api/files/trash
```
