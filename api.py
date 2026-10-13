from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag_pipeline import answer_question

app = FastAPI(
    title="Documentation RAG API",
    summary="Question answering over repository documentation using LangGraph + OpenAI embeddings",
    version="1.0.0",
)


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to answer from the docs")


class QuestionResponse(BaseModel):
    answer: str


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=QuestionResponse)
def ask_question(payload: QuestionRequest) -> QuestionResponse:
    try:
        answer = answer_question(payload.question)
        return QuestionResponse(answer=answer)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

