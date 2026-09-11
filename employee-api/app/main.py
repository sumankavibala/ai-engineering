import logging
import time
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.context import set_request_id
from app.ai.rate_limiter import ai_rate_limit_middleware
from app.routers.employee import router as employee_router
from app.routers.user import router as user_router
from app.routers.auth import router as auth_router
from app.routers.rag import router as rag_router
from app.exceptions import EmployeeNotFoundError
from app.telemetry_config import setup_opentelemetry

logger = logging.getLogger(__name__)

app = FastAPI(title="Employee AI API")

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    start_time = time.perf_counter()

    try:
        if request.url.path.startswith("/rag"):
            await ai_rate_limit_middleware(request)

        logger.info(
            "agent_request_started",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
        )

        response = await call_next(request)
        total_request_latency = time.perf_counter() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(total_request_latency)

        logger.info(
            "request_latency",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "total_request_latency": total_request_latency,
            },
        )
        return response
    except HTTPException as exc:
        total_request_latency = time.perf_counter() - start_time
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers={
                "X-Request-ID": request_id,
                "X-Process-Time": str(total_request_latency),
            },
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(employee_router)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(rag_router)


@app.exception_handler(EmployeeNotFoundError)
async def employee_not_found_handler(request: Request, exc: EmployeeNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )
