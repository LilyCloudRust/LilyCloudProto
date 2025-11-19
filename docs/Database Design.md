# Database Design

## Users Table

- Table name: `users`
- Description: Stores user account information.

| Column            | Type        | Description              |
| ----------------- | ----------- | ------------------------ |
| `user_id`         | `INTEGER`   | Primary key              |
| `username`        | `VARCHAR`   | Unique username          |
| `hashed_password` | `VARCHAR`   | Hashed password          |
| `created_at`      | `TIMESTAMP` | Timestamp of creation    |
| `updated_at`      | `TIMESTAMP` | Timestamp of last update |

## Storage Table

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

## Tasks Table

- Table name: `tasks`
- Description: Stores file operation task records.
- Notes: This table violates the first normal form (1NF) because it contains JSON array fields (`dst_dirs` and `file_names`), whether to split them into separate tables should be considered more carefully.

| Column         | Type        | Description                                                      |
| -------------- | ----------- | ---------------------------------------------------------------- |
| `task_id`      | `INTEGER`   | Primary key                                                      |
| `user_id`      | `INTEGER`   | User who issued the task (Foreign key referencing `users`)       |
| `type`         | `ENUM`      | Task type (copy, move, trash, restore, delete, upload, download) |
| `src_dir`      | `TEXT`      | Parent directory of the source files                             |
| `dst_dirs`\*   | `JSON`      | Destination directories                                          |
| `file_names`   | `JSON`      | List of file names involved                                      |
| `status`       | `ENUM`      | Task status (pending, archiving, running, completed, failed)     |
| `progress`     | `FLOAT`     | Progress percentage (0.00 - 100.00)                              |
| `message`      | `TEXT`      | Additional information or error messages                         |
| `created_at`   | `TIMESTAMP` | Timestamp when the task was created                              |
| `started_at`   | `TIMESTAMP` | Timestamp when the task started                                  |
| `completed_at` | `TIMESTAMP` | Timestamp when the task completed                                |
| `updated_at`   | `TIMESTAMP` | Timestamp when the task was last updated                         |

\* : `dst_dirs` is a JSON array because when restoring files from trash, there could be multiple destination directories.

## Trash Information Table

- Table name: `trash`
- Description: Stores information about files in the recycle bin.

| Column          | Type        | Description                                                     |
| --------------- | ----------- | --------------------------------------------------------------- |
| `trash_id`      | `INTEGER`   | Primary key                                                     |
| `user_id`       | `INTEGER`   | User who deleted the file/dir (Foreign key referencing `users`) |
| `entry_name`    | `TEXT`      | Name of the file/dir entry in the trash                         |
| `original_path` | `TEXT`      | Original file/dir path                                          |
| `deleted_at`    | `TIMESTAMP` | Timestamp when the file/dir was moved to the trash              |
