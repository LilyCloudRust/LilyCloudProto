from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel


class BatchDownloadRequest(BaseModel):
    dir: str
    file_names: list[str]


@dataclass
class DownloadResource:

    resource_type: Literal["path", "url", "stream"]
    data: Any
    filename: str
    media_type: str = "application/octet-stream"
