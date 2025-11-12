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

| Column         | Type        | Description                                                |
| -------------- | ----------- | ---------------------------------------------------------- |
| `task_id`      | `INTEGER`   | Primary key                                                |
| `user_id`      | `INTEGER`   | User who issued the task (Foreign key referencing `users`) |
| `type`         | `ENUM`      | Task type (copy, move, trash, delete)                      |
| `src_path`     | `TEXT`      | Source path                                                |
| `dst_path`     | `TEXT`      | Destination path (for copy/move)                           |
| `file_names`   | `JSON`      | List of file names involved                                |
| `status`       | `ENUM`      | Task status (pending, running, completed, failed)          |
| `progress`     | `FLOAT`     | Progress percentage (0.00 - 100.00)                        |
| `message`      | `TEXT`      | Additional information or error messages                   |
| `created_at`   | `TIMESTAMP` | Timestamp when the task was created                        |
| `started_at`   | `TIMESTAMP` | Timestamp when the task started                            |
| `completed_at` | `TIMESTAMP` | Timestamp when the task completed                          |
| `updated_at`   | `TIMESTAMP` | Timestamp when the task was last updated                   |

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
