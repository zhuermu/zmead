"""Error handling middleware to intercept ALL exceptions before they reach Starlette's error handler."""

import logging
import traceback
from typing import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches ALL exceptions and prevents stack traces from being exposed.

    This middleware runs BEFORE FastAPI's debug mode error handler, ensuring
    that no technical details are leaked to the frontend, even in development.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        """Intercept all requests and catch any exceptions."""
        try:
            # Try to process the request
            response = await call_next(request)
            return response

        except Exception as exc:
            # Log the full error with traceback for debugging
            logger.error(
                f"❌ Exception caught by GlobalErrorHandlerMiddleware",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
                exc_info=True,  # This logs the full traceback
            )

            # Determine error type and appropriate user message
            error_code = "INTERNAL_ERROR"
            error_message = "An unexpected error occurred. Please try again later."
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            exception_name = type(exc).__name__.lower()
            exception_str = str(exc).lower()

            # JSON decode/parsing errors
            if "json" in exception_name or "json" in exception_str:
                error_code = "DATA_FORMAT_ERROR"
                error_message = "Invalid data format in database. Please contact support."
                logger.error(f"🔴 JSON decode error: {str(exc)}")

            # Database errors
            elif "sql" in exception_name or "database" in exception_str:
                error_code = "DATABASE_ERROR"
                error_message = "A database error occurred. Please try again later."
                logger.error(f"🔴 Database error: {str(exc)}")

            # Connection/timeout errors
            elif "connection" in exception_name or "timeout" in exception_name:
                error_code = "SERVICE_UNAVAILABLE"
                error_message = "Service temporarily unavailable. Please try again later."
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                logger.error(f"🔴 Connection error: {str(exc)}")

            # Permission errors
            elif "permission" in exception_name or "forbidden" in exception_name:
                error_code = "PERMISSION_DENIED"
                error_message = "You do not have permission to perform this action."
                status_code = status.HTTP_403_FORBIDDEN
                logger.error(f"🔴 Permission error: {str(exc)}")

            # Return sanitized error response
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": {
                        "message": error_message,
                        "code": error_code,
                    }
                },
            )
