from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRouter
from loguru import logger

from app.services.chat import ChatService

router = APIRouter()


@router.get("/answer")
async def answer(
    query: str,
    session_id: str,
    model: str,
    chat_service: ChatService = Depends(),
) -> StreamingResponse:
    try:
        answers = chat_service.answer(query, session_id, model)
        return StreamingResponse(answers, media_type="text/plain")
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get(
    "/answer/dify",
    operation_id="vimo_answer",
    description="Get an answer from the vimo model.",
)
async def answer_dify(
    query: str,
    session_id: str,
    model: str,
    chat_service: ChatService = Depends(),
) -> StreamingResponse:
    try:
        answers = chat_service.answer(query, session_id, model, dify_response=True)
        return StreamingResponse(answers, media_type="text/plain")
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/check_history", response_model=None)
async def check_history(session_id: str, chat_service: ChatService = Depends()) -> list:
    return await chat_service.get_chat_history(session_id)
