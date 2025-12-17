import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from lilycloudproto.config import AuthSettings
from lilycloudproto.database import get_db
from lilycloudproto.domain.entities.user import User
from lilycloudproto.infra.drivers.local_driver import LocalDriver
from lilycloudproto.infra.repositories.user_repository import UserRepository
from lilycloudproto.infra.services.auth_service import AuthService
from lilycloudproto.infra.services.file_transfer_service import FileTransferService
from lilycloudproto.models.files.transfer import BatchDownloadRequest
from lilycloudproto.models.task import TaskResponse

router = APIRouter(prefix="/api/files", tags=["Files"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    settings = AuthSettings()
    user_repo = UserRepository(session)
    return AuthService(user_repo=user_repo, settings=settings)


def get_file_transfer_service(
    db: AsyncSession = Depends(get_db),
) -> FileTransferService:
    driver = LocalDriver()
    return FileTransferService(storage_driver=driver, db=db)


async def get_current_user_auth(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    return await auth_service.get_user_from_token(token)


@router.get("", summary="Single File Download")
async def download_file(
    path: str = Query(..., description="Full path to the file"),
    user: User = Depends(get_current_user_auth),
    service: FileTransferService = Depends(get_file_transfer_service),
) -> FileResponse:
    real_path = service.get_file_path_for_download(path)
    filename = os.path.basename(real_path)

    return FileResponse(
        path=real_path, filename=filename, media_type="application/octet-stream"
    )


@router.post("/upload", response_model=TaskResponse, summary="Batch Upload")
async def batch_upload(
    dir: str = Form(...),
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user_auth),
    service: FileTransferService = Depends(get_file_transfer_service),
) -> TaskResponse:
    file_names: list[str] = [f.filename for f in files if f.filename]

    if len(file_names) != len(files):
        raise HTTPException(status_code=400, detail="Invalid filename detected")

    file_contents = []
    for f in files:
        content = await f.read()
        file_contents.append(content)

    task = await service.create_upload_task(
        user_id=user.user_id,
        dst_dir=dir,
        file_names=file_names,
    )

    await service.process_upload_files(
        task_id=task.task_id, dst_dir=dir, files=file_contents, filenames=file_names
    )

    return task


@router.post("/download", response_model=TaskResponse, summary="Batch Download Request")
async def request_batch_download(
    request: BatchDownloadRequest,
    user: User = Depends(get_current_user_auth),
    service: FileTransferService = Depends(get_file_transfer_service),
) -> TaskResponse:
    task = await service.create_download_task(
        user_id=user.user_id, src_dir=request.dir, file_names=request.file_names
    )
    return task


@router.get("/archive/{task_id}", summary="Download Archive Stream")
async def download_archive(
    task_id: int,
    name: str = Query("download", description="Filename for the zip"),
    user: User = Depends(get_current_user_auth),
    service: FileTransferService = Depends(get_file_transfer_service),
) -> StreamingResponse:
    stream_gen = service.archive_stream_generator(task_id)
    return StreamingResponse(
        stream_gen,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}.zip"'},
    )
