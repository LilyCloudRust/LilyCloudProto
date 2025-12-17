from pydantic import BaseModel


class BatchDownloadRequest(BaseModel):
    dir: str
    file_names: list[str]
