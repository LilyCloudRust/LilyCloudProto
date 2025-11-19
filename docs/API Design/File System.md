# File System

## File Operations

```http
GET     /api/files/list
GET     /api/files/info
GET     /api/files/search
POST    /api/files/directory
POST    /api/files/copy
POST    /api/files/move
DELETE  /api/files
```

### List Files in Directory

```http
GET     /api/files/list
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

### Search Files

```http
GET     /api/files/search
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

### Delete Files Permanently

```http
DELETE  /api/files
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
POST    /api/files/upload
GET     /api/files
POST    /api/files/download
GET     /api/files/archive/{task_id}
```

### Batch Upload

```http
POST    /api/files/upload
```

Request:

```json
Authorization: Bearer <access_token>
Content-Type: multipart/form-data; boundary=...
{
  "dir": "Documents",
}
```

Response:

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "upload",
  "src_dir": null,
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

### Single File Download

```http
GET     /api/files
```

Request:

```json
Authorization: Bearer <access_token>
{
  "path": "string"
}
```

Response:

```json
Content-Type: application/pdf
Content-Disposition: attachment; filename="report.pdf"
(binary file data)
```

### Batch Download As Archive

```http
POST    /api/files/download
```

Request:

```json
Authorization: Bearer <access_token>
{
  "dir": "string",
  "file_names": ["report.pdf", "presentation.pptx"],
}
```

Response:

```json
{
  "task_id": 1,
  "user_id": 1,
  "type": "download",
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

### Download Archive

```http
GET     /api/files/download/{task_id}
```

Request:

```json
Authorization: Bearer <access_token>
{
  "name": "download"
}
```

Response:

```json
Content-Type: application/zip
Content-Disposition: attachment; filename="download.zip"
(binary file data)
```

## Trash Management

```http
POST    /api/files/trash
GET     /api/files/trash/{trash_id}
GET     /api/files/trash
POST    /api/files/trash/restore
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
GET     /api/files/trash/{trash_id}
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

### Delete Trashed Files

```http
DELETE    /api/files/trash
```

Request:

```json
Authorization: Bearer <access_token>
{
  "empty": false, // Whether to empty the entire trash.
  "trash_ids": [], // List of trash IDs to delete permanently.
  "dir": "string", // Relative path to the trash root.
  "file_names": [] // List of file names to delete permanently.
}
```

Note:

- Pass "empty": true to empty the entire trash.
- Pass "trash_ids" to delete specific trash entries permanently.
- Pass "dir" and "file_names" to delete files in subdirectories of the trash entries.
- If more than one option is provided, the API will return an error.

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

## File Operations Status

```http
GET     /api/files/task/{task_id}
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
