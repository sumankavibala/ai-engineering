from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
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
from app.services.inventory import InventoryService
from app.services.ai_agent import AIAgentService
from app.services.order import OrderService

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


@router.post("/ask", response_model=None)
async def ask_question(request: QuestionRequest, db: AsyncSession = Depends(get_db)):
    try:
        service = RAGService(db)
        if request.stream:
            return StreamingResponse(
                service.ask_stream(
                    question=request.question,
                    top_k=request.top_k,
                    department=request.department,
                ),
                media_type="text/event-stream",
            )
        return await service.ask(
            question=request.question,
            top_k=request.top_k,
            department=request.department,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.post("/agent/ask")
async def ask_agent(request: QuestionRequest, db: AsyncSession = Depends(get_db)):
    try:
        inventory_service = InventoryService(db)
        rag_service = RAGService(db)
        order_service = OrderService(db)
        agent = AIAgentService(inventory_service, rag_service, order_service)
        if request.stream:
            return StreamingResponse(
                agent.ask_stream(request.question),
                media_type="text/event-stream",
            )
        answer = await agent.ask(request.question)
        return {"answer": answer}
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
        )


