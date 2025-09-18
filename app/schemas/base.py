from pydantic import BaseModel


class BaseRequest(BaseModel):
    session_id: str
    llm_model: str = "gpt-4o-mini"
    language: str = "vi"
