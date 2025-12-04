from fastapi import APIRouter, Depends, Query

from lilycloudproto.domain.driver import Driver
from lilycloudproto.infra.drivers.local_driver import LocalDriver
from lilycloudproto.models.files.file import File
from lilycloudproto.models.files.list import ListArgs, ListQuery, ListResponse
from lilycloudproto.models.files.search import SearchArgs, SearchQuery, SearchResponse

router = APIRouter(prefix="/api/files", tags=["Files"])


def get_driver() -> Driver:
    return LocalDriver()


@router.get("/list", response_model=ListResponse)
def list_files(
    query: ListQuery = Depends(), driver: Driver = Depends(get_driver)
) -> ListResponse:
    args = ListArgs(
        path=query.path,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        dir_first=query.dir_first,
    )
    files = driver.list_dir(args)
    return ListResponse(path=query.path, total=len(files), items=files)


@router.get("/info", response_model=File)
def info(
    path: str = Query(),
    driver: Driver = Depends(get_driver),
) -> File:
    file = driver.info(path)
    return file


@router.get("/search", response_model=SearchResponse)
def search_files(
    query: SearchQuery = Depends(),
    driver: Driver = Depends(get_driver),
) -> SearchResponse:
    args = SearchArgs(
        keyword=query.keyword,
        path=query.path,
        recursive=query.recursive,
        type=query.type,
        mime_type=query.mime_type,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        dir_first=query.dir_first,
    )
    files = driver.search(args)
    return SearchResponse(path=query.path, total=len(files), items=files)
