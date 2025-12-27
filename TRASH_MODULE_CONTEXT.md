# Trash Module Implementation Context

> **Purpose**: This document provides context for understanding the current trash module implementation and guides future development.

## 📋 Current Implementation Status

### ✅ Completed Features

1. **POST /api/files/trash** - Move files to trash
   - Location: `lilycloudproto/apis/trash.py`
   - Creates async task via `TaskService`
   - Returns `TaskResponse` immediately

2. **TrashRepository** - Database operations
   - Location: `lilycloudproto/infra/repositories/trash_repository.py`
   - CRUD operations for Trash entities
   - Batch operations support

3. **TaskWorker._handle_trash()** - Async task processing
   - Location: `lilycloudproto/infra/services/task_worker.py`
   - Moves files to trash with directory structure preserved
   - Handles name conflicts
   - Recursive directory processing
   - Error handling with proper task status

4. **StorageService.get_trash_root()** - Trash root calculation
   - Location: `lilycloudproto/infra/services/storage_service.py`
   - Temporarily infers mount point from src_path
   - Returns `{mount_point}/.trash`

### ❌ Pending Features

1. **GET /api/files/trash/{trash_id}** - Get trash entry info
2. **GET /api/files/trash** - List trashed files
3. **POST /api/files/trash/restore** - Restore trashed files
4. **DELETE /api/files/trash** - Delete trashed files permanently

---

## 🏗️ Architecture Overview

### Data Flow

```
Client Request
    ↓
POST /api/files/trash
    ↓
TaskService.add_task() → Creates Task (status=PENDING)
    ↓
TaskWorker Queue → Async processing
    ↓
TaskWorker._handle_trash()
    ├─→ TrashRepository.create() → Database record
    └─→ shutil.move() → File system operation
    ↓
Task.status = COMPLETED/FAILED
```

### Key Components

#### 1. Database Entity (`domain/entities/trash.py`)
```python
class Trash(Base):
    trash_id: int          # Primary key
    user_id: int           # Foreign key to users
    entry_name: str        # Path in trash (e.g., "Documents/report.pdf")
    original_path: str     # Original path for restoration
    deleted_at: datetime   # Deletion timestamp
```

**Design Notes**:
- `entry_name`: Stores relative path from trash root, preserves directory structure
- `original_path`: Full absolute path for restoration
- File metadata (size, mime_type, etc.) is NOT stored - read from file system when needed

#### 2. Models (`models/trash.py`)
- `TrashRequest`: Request model for POST /api/files/trash
- `TrashEntry`: Response model for single entry (includes file metadata from FS)
- `TrashFile`: Response model for list items
- `TrashListQuery`: Query parameters for list endpoint
- `TrashResponse`: Response model for list endpoint
- `RestoreRequest`: Request model for restore endpoint
- `DeleteTrashRequest`: Request model for delete endpoint

#### 3. Repository (`infra/repositories/trash_repository.py`)
- `create()`: Create Trash record
- `get_by_id()`: Get by ID
- `find_by_entry_name()`: Find by entry_name (for conflict checking)
- `find_by_entry_names()`: Batch find (for list optimization)
- `find_by_user_and_path()`: Find by user, dir, and file_names (for restore/delete)
- `delete()`, `delete_by_ids()`, `delete_all_by_user()`: Delete operations

#### 4. Service Layer

**StorageService** (`infra/services/storage_service.py`):
- `get_trash_root(src_path)`: Calculate trash root directory
  - **Current**: Infers from src_path parent directory
  - **Future**: Query Storage table for mount_path
- `get_user_root()`: **Currently returns path as-is (placeholder)**
- `validate_user_path()`: **Currently always returns True (placeholder)**

**TaskWorker** (`infra/services/task_worker.py`):
- `_handle_trash()`: Main handler for TRASH tasks
- `_process_trash_task()`: Core processing logic
- `_trash_single_file()`: Process single file/directory
- `_trash_directory_recursive()`: Recursively process directory contents
- `_calculate_entry_name()`: Calculate entry_name from paths
- `_get_unique_entry_name()`: Handle name conflicts
- `_validate_trash_task_result()`: Validate and handle failures

---

## 🔑 Key Design Decisions

### 1. Directory Structure Preservation

**Decision**: Preserve relative path structure in trash

**Example**:
- Source: `/home/user/test/Documents/report.pdf`
- Trash root: `/home/user/.trash`
- Entry name: `test/Documents/report.pdf`
- Physical location: `/home/user/.trash/test/Documents/report.pdf`

**Implementation**:
- `_calculate_entry_name()` calculates relative path from mount point
- Directory structure is maintained in `entry_name`

### 2. Name Conflict Handling

**Decision**: Generate unique names when conflicts occur

**Pattern**: `file.txt` → `file(1).txt` → `file(2).txt`

**Implementation**:
- Check both file system and database for conflicts
- `_get_unique_entry_name()` handles this

### 3. Recursive Directory Processing

**Decision**: Create database records for all files in deleted directories

**Behavior**:
- When a directory is deleted, all files inside get individual Trash records
- Each file's `entry_name` preserves its relative path
- Each file's `original_path` is the full absolute path

### 4. Error Handling Strategy

**Decision**: Partial failure tolerance with proper status reporting

**Rules**:
- If **all files fail** → Task status = `FAILED`, raise exception
- If **some files fail** → Task status = `COMPLETED`, log warning
- If **all files succeed** → Task status = `COMPLETED`

**Implementation**:
- `_validate_trash_task_result()` enforces this logic

### 5. Path Calculation Location

**Decision**: Path calculations in TaskWorker, not StorageService

**Current State**:
- `_calculate_entry_name()` is in `TaskWorker`
- `get_trash_root()` is in `StorageService`
- **Note**: User requested moving path calculations to StorageService, but current implementation keeps it in TaskWorker

---

## 📝 Implementation Details

### Entry Name Calculation

**Current Implementation** (`TaskWorker._calculate_entry_name()`):
```python
def _calculate_entry_name(self, src_dir: str, file_name: str, trash_root: str) -> str:
    src_path = os.path.join(src_dir, file_name)
    # Get relative path from trash_root
    relative_path = os.path.relpath(src_path, trash_root)
    return relative_path.replace(os.sep, "/")
```

**Example**:
- `src_dir = "/home/c10h15n/test/"`
- `file_name = "Pictures"`
- `trash_root = "/home/c10h15n/.trash"`
- Result: `"test/Pictures"`

**Note**: This calculates relative to `trash_root`, which may not be correct. Should be relative to mount point.

### Trash Root Calculation

**Current Implementation** (`StorageService.get_trash_root()`):
```python
def get_trash_root(self, src_path: str) -> str:
    user_root = self.get_user_root(0, src_path)  # Returns path as-is
    mount_point = os.path.dirname(user_root)
    if not mount_point or mount_point == os.sep:
        mount_point = user_root
    return os.path.join(mount_point, ".trash")
```

**Example**:
- `src_path = "/home/c10h15n/test/"`
- `user_root = "/home/c10h15n/test/"` (from `get_user_root`)
- `mount_point = "/home/c10h15n"`
- Result: `"/home/c10h15n/.trash"`

### File Movement Process

1. Validate source file exists
2. Calculate `entry_name` (preserve structure)
3. Generate unique `entry_name` (handle conflicts)
4. Create Trash database record
5. Move file to trash (with rollback on failure)
6. If directory, recursively process contents

---

## 🚧 Known Issues & Limitations

### 1. Path Calculation Issue

**Problem**: `_calculate_entry_name()` uses `trash_root` as base, but should use mount point

**Current**:
- `entry_name = relpath(src_path, trash_root)` → `"../test/Pictures"` (wrong)

**Should be**:
- `entry_name = relpath(src_path, mount_point)` → `"test/Pictures"` (correct)

**Fix Needed**: Update `_calculate_entry_name()` to use mount point instead of trash_root

### 2. Empty Directory Handling

**Problem**: Empty directories are moved but no database record is created

**Current Behavior**:
- Directory moved to trash ✓
- No Trash record created ✗
- Directory appears in file system but not in database queries

**Fix Needed**: Create Trash record for directory itself, even if empty

### 3. Placeholder Functions

**Functions marked as "temporarily" or "placeholder"**:
- `StorageService.get_user_root()`: Returns path as-is
- `StorageService.validate_user_path()`: Always returns True

**Future**: These should query Storage table and implement proper validation

### 4. Task Status for Non-existent Files

**Fixed**: Now properly marks task as FAILED when all files don't exist

---

## 📋 Pending API Implementations

### 1. GET /api/files/trash/{trash_id}

**Requirements**:
- Return `TrashEntry` with file metadata from file system
- Use `Driver.info()` to get file metadata
- Combine database record with file system metadata

**Implementation Notes**:
- Query Trash by ID
- Verify `user_id` matches current user
- Read file from `trash_root/entry_name`
- Use `Driver.info()` to get metadata
- Return `TrashEntry` model

### 2. GET /api/files/trash

**Requirements**:
- List files in trash with filtering and sorting
- Support directory browsing (`path` parameter)
- Support recursive search
- Use file system traversal + database validation

**Implementation Strategy** (Recommended: File System First):
1. Use `Driver.list_dir()` or `Driver.search()` to traverse file system
2. For each file, query database by `entry_name`
3. Filter by `user_id` (only show current user's files)
4. Apply filters (keyword, type, mime_type)
5. Sort and paginate
6. Combine file system metadata with database `deleted_at`

**Key Models**:
- Request: `TrashListQuery` (query parameters)
- Response: `TrashResponse` (path, total, items)

### 3. POST /api/files/trash/restore

**Requirements**:
- Restore files from trash to original_path
- Create async task (type=RESTORE)
- Validate original_path doesn't exist (throw error if exists)
- Move file back and delete Trash record

**Implementation Notes**:
- Find Trash records by `dir` and `file_names`
- Verify `user_id` matches
- Check if `original_path` exists → throw ConflictError
- Create RESTORE task
- TaskWorker should handle RESTORE type

### 4. DELETE /api/files/trash

**Requirements**:
- Three modes: empty, trash_ids, dir+file_names
- Create async task (type=DELETE)
- Permanently delete files and Trash records

**Implementation Notes**:
- Validate only one mode is used
- Create DELETE task
- TaskWorker should handle DELETE type (different from regular DELETE)

---

## 🔧 TaskWorker Extensions Needed

### 1. _handle_restore()

**Signature**:
```python
async def _handle_restore(
    self,
    task: Task,
    progress_callback: Callable[[int, int], Awaitable[None]],
) -> None
```

**Logic**:
1. Query TrashRepository for entries matching task parameters
2. For each entry:
   - Check if `original_path` exists → ConflictError
   - Move file from `trash_root/entry_name` to `original_path`
   - Delete Trash record
3. Handle errors (partial failure tolerance)

### 2. _handle_delete_trash()

**Signature**:
```python
async def _handle_delete_trash(
    self,
    task: Task,
    progress_callback: Callable[[int, int], Awaitable[None]],
) -> None
```

**Logic**:
1. Determine deletion mode from task parameters
2. Query TrashRepository for entries to delete
3. Delete physical files
4. Delete Trash records
5. Handle errors

---

## 📊 Database Schema

### Trash Table

```sql
CREATE TABLE trash (
    trash_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    entry_name VARCHAR NOT NULL,      -- Relative path in trash
    original_path VARCHAR NOT NULL,   -- Full path for restoration
    deleted_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

**Indexes Needed** (future optimization):
- `(user_id, entry_name)` - For user queries and conflict checking
- `(user_id, deleted_at)` - For sorting by deletion time

---

## 🎯 Code Quality Requirements

All code must pass:
- `black .` - Code formatting
- `ruff check . --fix` - Linting
- `mypy . --strict` - Type checking

**Common Issues to Avoid**:
- Functions with >50 statements (PLR0915)
- Functions with >5 parameters (PLR0913)
- Unused variables (F841)
- Lines >88 characters (E501)

---

## 🔄 Future Improvements

1. **Storage Integration**: Query Storage table for mount_path
2. **User Isolation**: Implement proper user root directory calculation
3. **Path Validation**: Implement `validate_user_path()` properly
4. **Empty Directory Records**: Create Trash records for empty directories
5. **Batch Operations**: Optimize database queries for bulk operations
6. **Consistency Checks**: Background task to verify file system ↔ database consistency

---

## 📚 Related Files Reference

- **API Routes**: `lilycloudproto/apis/trash.py`
- **Models**: `lilycloudproto/models/trash.py`
- **Repository**: `lilycloudproto/infra/repositories/trash_repository.py`
- **Task Worker**: `lilycloudproto/infra/services/task_worker.py`
- **Storage Service**: `lilycloudproto/infra/services/storage_service.py`
- **Domain Entity**: `lilycloudproto/domain/entities/trash.py`
- **Domain Values**: `lilycloudproto/domain/values/trash.py`

---

**Last Updated**: 2025-12-27  
**Status**: POST /api/files/trash implemented, other endpoints pending

