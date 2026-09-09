import logging
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers.employee import router as employee_router
from app.routers.user import router as user_router
from app.routers.auth import router as auth_router
from app.routers.rag import router as rag_router
from app.exceptions import EmployeeNotFoundError

logger = logging.getLogger(__name__)

app = FastAPI()

@app.middleware("http")
async def add_latency_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    total_request_latency = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(total_request_latency)
    logger.info(
        "request_latency",
        extra={
            "path": request.url.path,
            "method": request.method,
            "total_request_latency": total_request_latency,
        },
    )
    return response

app.include_router(employee_router)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(rag_router)

@app.exception_handler(EmployeeNotFoundError)
async def employee_not_found_handler(request: Request, exc: EmployeeNotFoundError):
  return JSONResponse(
    status_code=404,
    content={"detail": str(exc)}
  )


