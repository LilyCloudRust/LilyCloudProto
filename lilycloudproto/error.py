from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError


class BadRequestError(Exception):
    """Raised for invalid input or request."""

    pass


class NotFoundError(Exception):
    """Raised when a resource is not found."""

    pass


class ConflictError(Exception):
    """Raised when a resource already exists or violates a unique constraint."""

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

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exception: NotFoundError) -> None:
        raise HTTPException(status_code=404, detail=str(exception))

    @app.exception_handler(ConflictError)
    async def conflict_handler(_request: Request, exception: ConflictError) -> None:
        raise HTTPException(status_code=409, detail=str(exception))

    @app.exception_handler(TeapotError)
    async def teapot_handler(_request: Request, exception: TeapotError) -> None:
        raise HTTPException(status_code=418, detail=str(exception))
