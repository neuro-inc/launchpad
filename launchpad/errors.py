from typing import Any

from fastapi import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)


class LaunchpadApiError(HTTPException):
    """
    Base launchpad API Error
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        *args: Any,
        **kwargs: Any,
    ):
        detail = {"message": message}
        super().__init__(status_code=status_code, detail=detail, **kwargs)


class BadRequest(LaunchpadApiError):
    def __init__(self, message: str = "Bad Request", **kwargs: Any):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, message=message, **kwargs)


class Unauthorized(LaunchpadApiError):
    def __init__(self, message: str = "Unathorized", **kwargs: Any):
        super().__init__(status_code=HTTP_401_UNAUTHORIZED, message=message, **kwargs)


class Forbidden(LaunchpadApiError):
    def __init__(self, message: str = "Forbidden", **kwargs: Any):
        super().__init__(status_code=HTTP_403_FORBIDDEN, message=message, **kwargs)


class NotFound(LaunchpadApiError):
    def __init__(self, message: str = "Not Found", **kwargs: Any):
        super().__init__(status_code=HTTP_404_NOT_FOUND, message=message, **kwargs)
