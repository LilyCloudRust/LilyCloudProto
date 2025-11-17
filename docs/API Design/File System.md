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
  "src_dir": "/Pictures",
  "dst_dirs": [],
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

### Trash Files

```http
POST    /api/files/trash
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
{
  "task_id": 1,
  "user_id": 1,
  "type": "trash",
  "src_dir": "/Pictures",
  "dst_dirs": [],
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

### Get Trash Entry Info

```http
GET     /api/files/trash/{id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "trash_id": 1,
  "user_id": 1,
  "entry_name": "report.pdf",
  "original_path": "/Documents/report.pdf",
  "type": "file",
  "size": 2048576, // In bytes.
  "mime_type": "application/pdf",
  "deleted_at": "2025-10-25T00:00:00Z",
  "created_at": "2025-10-25T00:00:00Z",
  "modified_at": "2025-10-25T00:00:00Z",
  "accessed_at": "2025-10-25T00:00:00Z"
}
```

### List Trashed Files

```http
GET     /api/files/trash
```

Request:

```json
Authorization: Bearer <access_token>
{
  "path": "/Documents",  // Relative path to the trash root.
  "sort_by": "name | path | size | deleted | created | modified | accessed | type",
  "sort_order": "asc | desc",
  "dir_first": true
}
```

Response:

```json
{
  "path": "/Documents",
  "total": 100,
  "items": [
    {
      "trash_id": 1,
      "user_id": 1,
      "entry_name": "photos",
      "original_path": "/Documents/photos",
      "type": "directory",
      "size": 0, // In bytes.
      "mime_type": null,
      "deleted_at": "2025-10-25T00:00:00Z",
      "created_at": "2025-10-25T00:00:00Z",
      "modified_at": "2025-10-25T00:00:00Z",
      "accessed_at": "2025-10-25T00:00:00Z"
    },
    {
      "trash_id": 2,
      "user_id": 1,
      "entry_name": "report.pdf",
      "original_path": "/Documents/report.pdf",
      "type": "file",
      "size": 2048576, // In bytes.
      "mime_type": "application/pdf",
      "deleted_at": "2025-10-25T00:00:00Z",
      "created_at": "2025-10-25T00:00:00Z",
      "modified_at": "2025-10-25T00:00:00Z",
      "accessed_at": "2025-10-25T00:00:00Z"
    }
  ]
}
```

### Search Trashed Files

```http
GET     /api/files/trash
```

Request:

```json
{
  "keyword": "string",
  "path": "/Documents", // Relative path to the trash root.
  "recursive": true,
  "type": "file", // Optional: filter by type.
  "mime_type": "application/pdf", // Optional: filter by MIME type.
  "sort_by": "name | path | size | deleted | created | modified | accessed | type",
  "sort_order": "asc | desc",
  "dir_first": true
}
```

Response

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

### Restore Trashed Files

```http
POST    /api/files/trash/restore
```

Request:

```json
Authorization: Bearer <access_token>
{
  "dir": "string", // Relative path to the trash root.
  "file_names": ["report.pdf", "presentation.pptx"]
}
```

Response

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "restore",
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

### Delete Trash Entry

```http
DELETE    /api/files/trash/{id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "delete",
  "src_dir": "/Documents",
  "dst_dirs": [],
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

### Delete Trashed Files

```http
DELETE    /api/files/trash
```

Request:

```json
Authorization: Bearer <access_token>
{
  "dir": "string", // Relative path to the trash root.
  "file_names": ["report.pdf", "presentation.pptx"]
}
```

Response:

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "delete",
  "src_dir": "/Documents",
  "dst_dirs": [],
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

### Clear Trash

```http
DELETE    /api/files/trash
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "delete",
  "src_dir": "/",
  "dst_dirs": [],
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

## File Operations Status

```http
GET     /api/files/task/{id}
```

Request:

```json
Authorization: Bearer <access_token>
```

Response:

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "copy",
  "src_dir": "/Pictures",
  "dst_dirs": ["/Documents"],
  "file_names": ["report.pdf", "presentation.pptx"],
  "status": "running",
  "progress": 0.0,
  "message": "",
  "created_at": "2025-10-25T00:00:00Z",
  "started_at": "2025-10-25T00:00:00Z",
  "completed_at": null,
  "updated_at": "2025-10-25T00:00:00Z"
}
```
