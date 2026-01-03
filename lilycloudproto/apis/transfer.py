from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.apis.auth import get_auth_service
from lilycloudproto.database import get_db
from lilycloudproto.domain.entities.user import User
from lilycloudproto.infra.drivers.local_driver import LocalDriver
from lilycloudproto.infra.repositories.storage_repository import StorageRepository
from lilycloudproto.infra.services.auth_service import AuthService
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.transfer_service import TransferService
from lilycloudproto.models.files.transfer import BatchDownloadRequest
from lilycloudproto.models.task import TaskResponse

router = APIRouter(prefix="/api/files", tags=["Files"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _get_transfer_service(
    db: AsyncSession = Depends(get_db),
) -> TransferService:
    driver = LocalDriver()
    storage_repo = StorageRepository(db)
    storage_service = StorageService(storage_repo)
    return TransferService(
        storage_driver=driver, storage_service=storage_service, db=db
    )


async def get_current_user_auth(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    return await auth_service.get_user_from_token(token)


@router.post("/upload", response_model=TaskResponse)
async def batch_upload(
    dir: str = Form(..., description="Target directory"),
    files: list[UploadFile] = File(..., description="Files to upload"),
    user: User = Depends(get_current_user_auth),
    service: TransferService = Depends(_get_transfer_service),
) -> TaskResponse:
    """POST /api/files/upload - Batch Upload (Multipart)"""
    file_names = [f.filename for f in files if f.filename]
    if len(file_names) != len(files):
        raise HTTPException(status_code=400, detail="Invalid filename detected")

    file_contents = []
    for f in files:
        content = await f.read()
        file_contents.append(content)

    task = await service.create_upload_task(
        user_id=user.user_id, dst_dir=dir, file_names=file_names
    )

    await service.process_upload_files(
        task_id=task.task_id, dst_dir=dir, files=file_contents, filenames=file_names
    )
    return task


@router.get("")
async def download_file(
    path: str = Query(..., description="Full path to the file"),
    user: User = Depends(get_current_user_auth),
    service: TransferService = Depends(_get_transfer_service),
) -> Response:
    """
    GET /api/files - Single File Download
    Returns File, Redirect(URL), or Stream based on driver.
    """
    resource = await service.get_download_resource(path)

    if resource.resource_type == "path":
        return FileResponse(
            path=resource.data,
            filename=resource.filename,
            media_type=resource.media_type,
        )
    elif resource.resource_type == "url":
        return RedirectResponse(url=resource.data)
    elif resource.resource_type == "stream":
        return StreamingResponse(
            resource.data,
            media_type=resource.media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{resource.filename}"'
            },
        )
    else:
        raise HTTPException(status_code=500, detail="Unknown resource type")


@router.post("/download", response_model=TaskResponse)
async def request_batch_download(
    request: BatchDownloadRequest,
    user: User = Depends(get_current_user_auth),
    service: TransferService = Depends(_get_transfer_service),
) -> TaskResponse:
    """POST /api/files/download - Create a Task to zip multiple files"""
    task = await service.create_download_task(
        user_id=user.user_id, src_dir=request.dir, file_names=request.file_names
    )
    return task


@router.get("/archive/{task_id}", summary="Download Archive Stream")
async def download_archive(
    task_id: int,
    name: str = Query("download", description="Filename for the zip"),
    user: User = Depends(get_current_user_auth),
    service: TransferService = Depends(_get_transfer_service),
) -> StreamingResponse:
    stream_gen = service.archive_stream_generator(task_id)
    return StreamingResponse(
        stream_gen,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}.zip"'},
    )
