"""Shared product error envelope and sanitized exception handling."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from backend.models import ErrorDetail, ErrorResponse

ERROR_RESPONSES = {
    status: {"model": ErrorResponse, "description": description}
    for status, description in (
        (404, "Requested resource not found"),
        (422, "Invalid request parameters"),
        (500, "Unexpected backend failure"),
    )
}


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable


def error_response(status: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, retryable=retryable))
    return JSONResponse(status_code=status, content=body.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return error_response(exc.status, exc.code, exc.message, exc.retryable)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        locations = sorted({".".join(map(str, issue["loc"])) for issue in exc.errors()})
        return error_response(422, "VALIDATION_ERROR", "Invalid request parameters: " + ", ".join(locations))

    @app.exception_handler(HTTPException)
    async def http_handler(request: Request, exc: HTTPException):
        code, message = {
            404: ("NOT_FOUND", "Route not found"),
            405: ("METHOD_NOT_ALLOWED", "Method not allowed"),
        }.get(exc.status_code, ("HTTP_ERROR", "Request failed"))
        response = error_response(exc.status_code, code, message)
        if exc.headers:
            response.headers.update(exc.headers)
        return response
