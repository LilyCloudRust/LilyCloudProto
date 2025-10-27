# Contributing to Lily Cloud Prototype

This document provides guidelines and instructions for setting up your development environment and contributing to the Lily Cloud Prototype project.

## Prerequisites

Before contributing to the Lily Cloud Prototype, ensure you have the following:

* [Python](https://www.python.org/): Latest version (3.13 or higher).
* [Git](https://git-scm.com/): For version control.
* [uv](https://docs.astral.sh/uv/#installation): A fast Python package manager.

## Getting Started

### 1. Clone the Repository

Via ssh (recommended):

```bash
git clone git@github.com:LilyCloudRust/LilyCloudProto.git
cd LilyCloudProto
```

Via https:

```bash
git clone https://github.com/LilyCloudRust/LilyCloudProto.git
cd LilyCloudProto
```

### 2. Install Dependencies

We use `uv` to manage our Python dependencies. To install the required packages, run:

```bash
uv sync --all-extra
```

This will create a virtual environment located at `.venv/` in the project root and install all necessary packages, including project dependencies and development tools.
You can activate the virtual environment with:

This will set up the hooks to run automatically before each commit.

### 3. Verify the Setup

To verify that everything is set up correctly, activate your virtual environment and check the versions of Python and the installed tools:

```bash
# Linux/MacOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

Then run:

```bash
python --version
black --version
ruff --version
mypy --version
pre-commit --version
```

### 4. Run the Development Server

To start the development server, ensure your virtual environment is activated and run:

```bash
uvicorn lilycloudproto.main:app --reload --host localhost --port 8000
```

Visit [http://localhost:8000/scalar](http://localhost:8000/scalar) to access interactive API client.

### 5. Install Pre-commit Hooks

To ensure code quality and consistency, we use `pre-commit` hooks. After activating your virtual environment, install them by running:

```bash
pre-commit install-hooks
pre-commit install
```

After this, the hooks will run automatically before each commit, you can also run them manually with:

```bash
pre-commit run --all-files
```

## Code Standard

### Project Structure

```plaintext
lilycloudproto/
├── apis/              # Route handlers and endpoints
├── entities/          # Database entity definitions
├── infra/             # Repository and data access layer
├── models/            # Request and response models
├── __init__.py        # Package initializer
├── database.py        # Database configuration
├── error.py           # Custom exceptions and error handler
└── main.py            # FastAPI application setup
```

### Python Style Guide

We follow PEP 8 with tool-enforced standards:

Black: Code formatting (line length: default 88 characters)

```bash
black .
```

Ruff: Linting (strict rules for code quality)

```bash
ruff check .
```

Fix issues with:

```bash
ruff check . --fix
```

Mypy: Type checking (strict mode enabled)

```bash
mypy . --strict
```

Note: Pre-commit hooks will automatically run these tools before each commit, if checks fail, the commit will be aborted. You can run pre-commit manually with:

```bash
pre-commit run --all-files
```

### Naming Conventions

* Modules: `snake_case` (e.g., `user_repository.py`)
* Classes: `PascalCase` (e.g., `UserRepository`)
* Functions: `snake_case` (e.g., `get_user_by_id`)
* Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_UPLOAD_SIZE`)
* Private: Leading underscore (e.g., `_internal_method`)

### Type Hints

All functions must include type hints:

```python
from typing import Optional, List
from fastapi import APIRouter, Depends

async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> Optional[UserResponse]:
    """Get user by ID from database."""
    # Implementation
    pass
```

### Docstrings

Use Google-style docstrings:

```python
async def create_user(data: UserCreate, db: AsyncSession) -> UserResponse:
    """Create a new user.
    
    Args:
        data: User creation request data
        db: Database session dependency
        
    Returns:
        UserResponse: Created user data
        
    Raises:
        ConflictError: If username already exists
        ValidationError: If data is invalid
    """
    # Implementation
    pass
```

### Error Handling

Use custom exceptions from `error.py`:

```python
from lilycloudproto.error import ConflictError, NotFoundError, ValidationError

# Check for duplicate
if existing_user:
    raise ConflictError(f"Username '{username}' already exists")

# Check if resource exists
if not user:
    raise NotFoundError(f"User with ID '{user_id}' not found")
```

Note: Error messages should NOT end with a period.
