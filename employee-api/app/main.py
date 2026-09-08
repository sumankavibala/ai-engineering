from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers.employee import router as employee_router
from app.routers.user import router as user_router
from app.routers.auth import router as auth_router
from app.routers.rag import router as rag_router
from app.exceptions import EmployeeNotFoundError

app = FastAPI()

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

