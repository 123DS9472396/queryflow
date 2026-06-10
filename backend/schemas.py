"""
schemas.py — Pydantic request/response models for QueryFlow FastAPI.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any


class ChatRequest(BaseModel):
    """Incoming chat message from the frontend."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language question about NYC taxi data",
        example="What were the top 5 revenue hours on weekdays?"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"question": "What were the top 5 revenue hours on weekdays?"},
                {"question": "Which payment method is most popular?"},
                {"question": "Show me average trip distance by day of week"},
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    clickhouse: str
    version: str


class SSEEvent(BaseModel):
    """
    Server-Sent Event payload types streamed from /api/chat.
    
    type: "sql"    → generated SQL query string
    type: "data"   → list of result rows (dicts)
    type: "token"  → LLM answer token (streamed one-by-one)
    type: "done"   → stream finished signal
    type: "error"  → error message string
    """
    type: str  # "sql" | "data" | "token" | "done" | "error"
    content: Optional[Any] = None
