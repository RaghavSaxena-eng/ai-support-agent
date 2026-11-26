from contextlib import asynccontextmanager
from dataclasses import asdict
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .agent import SupportAgent
from .db import init_db


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str = ""
    chat_model: str = "gemini-3.5-flash"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI Support Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


@lru_cache
def get_agent() -> SupportAgent:
    return SupportAgent(settings.gemini_api_key, settings.chat_model)


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # the frontend keeps the conversation and sends it back each time,
    # so the API itself stays stateless
    history: list[HistoryItem] = Field(default_factory=list, max_length=40)


class StepOut(BaseModel):
    tool: str
    args: dict
    result: dict


class ChatResponse(BaseModel):
    reply: str
    steps: list[StepOut]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest, agent: SupportAgent = Depends(get_agent)):
    result = agent.chat([h.model_dump() for h in body.history], body.message.strip())
    return {"reply": result.reply, "steps": [asdict(s) for s in result.steps]}
