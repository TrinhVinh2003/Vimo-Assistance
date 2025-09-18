import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import Depends

from app.db.dependencies import pg_client
from app.services.prompts import SYSTEM_PROMPT, USER_MESSAGE_TEMPLATE
from app.services.retrieval import RetrievalService
from app.utils.openai_connect import (
    END_OF_STREAM,
    USAGE_CHAR,
    chat_completion_stream,
    embed,
)

DOCUMENT_COLLECTION_NAME = "vimo_documents"

CHAT_COLLECTION_NAME = "vimo_chat_history"


class ChatService:
    def __init__(
        self,
        client: pg_client,
        retrieve_service: RetrievalService = Depends(),
    ) -> None:
        self.top_k = 5
        self.score_threshold = 0.5
        self.retrieve_service = retrieve_service
        self.client = client

    async def clear_sessions(self, session_id: Optional[str] = None) -> None:
        """Delete all sessions or a specific session."""
        collection = await self.client.get_or_create_collection(
            CHAT_COLLECTION_NAME,
            1536,
        )
        if session_id is None:
            # Delete all sessions
            await collection.delete_all()
        else:
            # Delete a specific session
            await collection.delete(session_id)

    async def get_session(self, session_id: str) -> list:
        pass

    async def save_chat_history(self, session_id: str, role: str, content: str) -> None:
        """Save a single message to the chat history with embedding."""
        collection = await self.client.get_or_create_collection(
            CHAT_COLLECTION_NAME,
            1536,
        )

        is_success, embedding, _ = embed([content])
        if not is_success:
            raise ValueError("Embedding failed")

        await collection.upsert(
            id=str(uuid.uuid4()),
            embedding=embedding[0],
            payload={
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def answer(
        self,
        query: str,
        session_id: str,
        model: str,
        dify_response: bool = False,
    ) -> AsyncGenerator:
        """Answer user query using RAG and stream the response as Server-Sent Events (SSE)."""
        search_results = await self.retrieve_service.search(
            query=query,
            collection_name=DOCUMENT_COLLECTION_NAME,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
        )
        content = "\n".join(record.content for record in search_results)

        histories = await self.retrieve_service.get_chat_history(session_id)

        # Create input message
        input_message = USER_MESSAGE_TEMPLATE.format(
            search_results=content,
            question=query,
        )

        # Generate answer
        answer_generator = chat_completion_stream(
            message=input_message,
            model=model,
            system_prompt=SYSTEM_PROMPT,
            histories=histories,
        )

        # Yield answer
        bot_response = ""
        for is_success, chunk, usage in answer_generator:
            if not is_success:
                raise ValueError("Failed to chat completion")
            if dify_response:
                if chunk != END_OF_STREAM and chunk != USAGE_CHAR:  # noqa: PLR1714
                    bot_response += chunk
                    yield chunk
            else:
                event = json.dumps({"text": chunk, "usage": usage}, ensure_ascii=False)
                if chunk != END_OF_STREAM and chunk != USAGE_CHAR:  # noqa: PLR1714
                    bot_response += chunk
                yield event + "\n"

        await self.save_chat_history(session_id, "user", query)
        await self.save_chat_history(session_id, "assistant", bot_response)
