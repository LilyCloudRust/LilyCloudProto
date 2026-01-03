from fastapi import FastAPI, Request, Response
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError


class BadRequestError(Exception):
    """Raised for invalid input or request."""

    pass


class AuthenticationError(Exception):
    """Raised when authentication fails (401)."""

    pass


class NotFoundError(Exception):
    """Raised when a resource is not found."""

    pass


class ConflictError(Exception):
    """Raised when a resource already exists or violates a unique constraint."""

    pass


class UnprocessableEntityError(Exception):
    """Raised when the request is well-formed but has semantic errors."""

    pass


class InternalServerError(Exception):
    """Raised when an internal server error occurs."""

    pass


class TeapotError(Exception):
    """Raised when the server is a teapot and refuses to brew coffee."""

    pass


# pyright: reportUnusedFunction=false
def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        _request: Request, exception: IntegrityError
    ) -> None:
        raise HTTPException(status_code=400, detail=str(exception))

    @app.exception_handler(BadRequestError)
    async def bad_request_handler(
        _request: Request, exception: BadRequestError
    ) -> None:
        raise HTTPException(status_code=400, detail=str(exception))

    @app.exception_handler(AuthenticationError)
    async def authentication_handler(
        _request: Request, exception: AuthenticationError
    ) -> None:
        raise HTTPException(
            status_code=401,
            detail=str(exception),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exception: NotFoundError) -> None:
        raise HTTPException(status_code=404, detail=str(exception))

    @app.exception_handler(ConflictError)
    async def conflict_handler(_request: Request, exception: ConflictError) -> None:
        raise HTTPException(status_code=409, detail=str(exception))

    @app.exception_handler(TeapotError)
    async def teapot_handler(_request: Request, exception: TeapotError) -> None:
        raise HTTPException(status_code=418, detail=str(exception))

    @app.exception_handler(UnprocessableEntityError)
    async def unprocessable_entity_handler(
        _request: Request, exception: UnprocessableEntityError
    ) -> None:
        raise HTTPException(status_code=422, detail=str(exception))

    @app.exception_handler(InternalServerError)
    async def internal_server_error_handler(
        _request: Request, exception: InternalServerError
    ) -> None:
        raise HTTPException(status_code=500, detail=str(exception))

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> Response:
        if str(exc) == "Unauthorized" and request.url.path.startswith("/webdav"):
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="LilyCloud WebDAV"'},
                content="Unauthorized",
            )
        raise HTTPException(status_code=500, detail="Internal Server Error")
