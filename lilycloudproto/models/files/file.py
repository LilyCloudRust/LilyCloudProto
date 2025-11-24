from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class File:
    name: str
    path: str
    type: Literal["file", "directory"]
    size: int  # In bytes.
    mime_type: str
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
