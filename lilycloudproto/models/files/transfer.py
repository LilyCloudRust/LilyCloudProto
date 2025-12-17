from typing import List
from pydantic import BaseModel


class BatchDownloadRequest(BaseModel):
    dir: str
    file_names: List[str]
