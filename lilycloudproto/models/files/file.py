from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Type(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"


@dataclass
class File:
    name: str
    path: str
    type: Type
    size: int  # In bytes.
    mime_type: str
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
