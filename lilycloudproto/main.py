from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from scalar_fastapi import (
    get_scalar_api_reference,  # pyright: ignore[reportUnknownVariableType]
)

from lilycloudproto.apis.admin_storage import router as admin_storage_router
from lilycloudproto.apis.admin_task import router as admin_task_router
from lilycloudproto.apis.admin_user import router as admin_user_router
from lilycloudproto.apis.files import router as files_router
from lilycloudproto.apis.auth import router as auth_router
from lilycloudproto.database import init_db
from lilycloudproto.error import TeapotError, register_error_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    await init_db()
    yield


app = FastAPI(title="Lily Cloud Prototype API", lifespan=lifespan)

# Register error handlers.
register_error_handlers(app)

# Include routers.
app.include_router(admin_user_router)
app.include_router(admin_storage_router)
app.include_router(admin_task_router)
app.include_router(files_router)
app.include_router(auth_router)


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
