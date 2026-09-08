from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.user import UserCreate, UserResponse
from app.schemas.rag import (
    DocumentIngestRequest,
    DocumentIngestResponse,
    QuestionRequest,
    QuestionResponse,
)
from app.services.user import create_user as create_user_service
from app.services.rag import RAGService

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: AsyncSession = Depends(get_db)):
    try:
        return await create_user_service(session, user)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post("/ingest", response_model=DocumentIngestResponse)
async def ingest_document(
    request: DocumentIngestRequest, db: AsyncSession = Depends(get_db)
):
    try:
        service = RAGService(db)
        return await service.ingest_document(
            text=request.text,
            source=request.source,
            document_type=request.document_type,
            department=request.department,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest, db: AsyncSession = Depends(get_db)):
    try:
        service = RAGService(db)
        return await service.ask(
            question=request.question,
            top_k=request.top_k,
            department=request.department,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

