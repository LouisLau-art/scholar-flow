import time
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# === 结构化日志配置 ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scholarflow")

class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    统一异常捕获中间件
    遵循章程：所有 User Story 必须包含异常处理、结构化日志
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"Method: {request.method} Path: {request.url.path} Status: {response.status_code} Time: {process_time:.4f}s")
            return response
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail, "type": "http_exception"}
            )
        except Exception as e:
            logger.error(f"Unhandled Exception: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "内部系统错误，请联系管理员", "type": "server_error"}
            )
