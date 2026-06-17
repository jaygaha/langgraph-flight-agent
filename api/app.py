"""
This file creates the FastAPI instance, registers the router, and adds a health check. It's the entry point
uvicorn will point at.
"""
import logging
from fastapi import FastAPI
from api.routes.flights import router
from src.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
  title="Flight Search Agent",
  description="LangGraph powered flight search with human-in-the-loop booking approval",
  version="0.1.0",
)

app.include_router(router)

@app.get("/health", tags=["system"])
def health():
  return {
      "status": "ok",
      "llm_provider": settings.llm_provider,
      "llm_model": settings.llm_model,
  }