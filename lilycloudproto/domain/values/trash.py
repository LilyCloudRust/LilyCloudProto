from enum import Enum


class TrashSortBy(str, Enum):
    NAME = "name"
    PATH = "path"
    SIZE = "size"
    TYPE = "type"
    DELETED = "deleted"
    CREATED = "created"
    MODIFIED = "modified"
    ACCESSED = "accessed"


class TrashSortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"
