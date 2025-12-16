from pydantic import BaseModel


class CopyCommand(BaseModel):
    src_dir: str
    dst_dir: str
    file_names: list[str]


class MoveCommand(BaseModel):
    src_dir: str
    dst_dir: str
    file_names: list[str]


class DeleteCommand(BaseModel):
    dir: str
    file_names: list[str]
