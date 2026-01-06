import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from scalar_fastapi import (
    get_scalar_api_reference,  # pyright: ignore[reportUnknownVariableType]
)

from lilycloudproto.apis.admin.storage import router as admin_storage_router
from lilycloudproto.apis.admin.task import router as admin_task_router
from lilycloudproto.apis.admin.user import router as admin_user_router
from lilycloudproto.apis.auth import router as auth_router
from lilycloudproto.apis.files import router as files_router
from lilycloudproto.apis.share import router as share_router
from lilycloudproto.apis.transfer import router as files_transfer
from lilycloudproto.apis.trash import router as trash_router
from lilycloudproto.apis.webdav import router as webdav_router
from lilycloudproto.config import AuthSettings
from lilycloudproto.error import TeapotError, register_error_handlers
from lilycloudproto.infra.database import AsyncSessionLocal, init_db
from lilycloudproto.infra.repositories.storage_repository import StorageRepository
from lilycloudproto.infra.repositories.task_repository import TaskRepository
from lilycloudproto.infra.seed import seed_admin
from lilycloudproto.infra.services.auth_service import AuthService
from lilycloudproto.infra.services.storage_service import StorageService
from lilycloudproto.infra.services.task_service import TaskService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    await init_db()
    # Create StorageService and TaskWorker singletons.
    session_factory = AsyncSessionLocal
    async with session_factory() as session:
        # Create StorageService singleton.
        storage_repo = StorageRepository(session)
        storage_service = StorageService(storage_repo)
        app.state.storage_service = storage_service

        # Create TaskService singleton.
        task_repo = TaskRepository(session)
        task_service = TaskService(task_repo, AsyncSessionLocal, storage_service)
        app.state.task_service = task_service

        # Create AuthService singleton.
        auth_settings = AuthSettings()
        auth_service = AuthService(settings=auth_settings, db=session)
        app.state.auth_service = auth_service

        # Start background task worker.
        background_task = asyncio.create_task(task_service.start())

        # Seed the admin user.
        await seed_admin(auth_service)

        try:
            yield
        finally:
            await task_service.stop()
            _ = background_task.cancel()


app = FastAPI(title="Lily Cloud Prototype API", lifespan=lifespan)

# Register error handlers.
register_error_handlers(app)

# Include routers.
app.include_router(admin_storage_router)
app.include_router(admin_task_router)
app.include_router(admin_user_router)
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(share_router)
app.include_router(files_transfer)
app.include_router(trash_router)
app.include_router(webdav_router)


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    html = """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>LilyCloud Cloud Prototype API</title>
        <style>
          body { font-family: sans-serif; margin: 2rem; }
          h1 { color: #D2BAED; }
          a { color: #F4ADB9; text-decoration: none; }
        </style>
      </head>
      <body>
        <h1>Lily Cloud Prototype API</h1>
        <p>Quick links:</p>
        <ul>
          <li><a href="/scalar" target="_blank">Scalar API Client (/scalar)</a></li>
        </ul>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/scalar", include_in_schema=False)
async def scalar_html() -> HTMLResponse:
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


@app.get("/api/brewcoffee", include_in_schema=False)
async def brewcoffee(message: str) -> None:
    if message == "Brew coffee!":
        raise TeapotError("I'm a teapot.")
