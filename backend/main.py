"""
main.py — FastAPI application for QueryFlow.

Endpoints:
  GET  /health         — ClickHouse connectivity check
  POST /api/chat       — SSE streaming NL-to-SQL agent
  GET  /api/suggestions — example questions for the UI
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from schemas import ChatRequest, HealthResponse
from agent import run_agent
from database import health_check

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# App lifecycle
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 QueryFlow API starting up...")
    ch = health_check()
    if ch.get("clickhouse") == "connected":
        logger.info("✅ ClickHouse Cloud connected")
    else:
        logger.warning(f"⚠️  ClickHouse connection issue: {ch}")
    yield
    logger.info("QueryFlow API shutting down.")


# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────
app = FastAPI(
    title="QueryFlow API",
    description="Conversational Analytics Agent — NL → SQL → ClickHouse",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict to your Vercel domain in production
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health() -> dict:
    """Health check — verifies ClickHouse connectivity."""
    ch = health_check()
    return {
        "status": "ok" if ch.get("clickhouse") == "connected" else "degraded",
        "clickhouse": ch.get("clickhouse"),
        "version": "1.0.0",
    }


@app.get("/api/suggestions", tags=["Chat"])
def get_suggestions() -> dict:
    """Return example questions for the chat UI suggestion chips."""
    return {
        "suggestions": [
            "What were the top 5 revenue hours on weekdays?",
            "Which payment method is most popular?",
            "Show me average trip distance by day of week",
            "What day had the most trips in January 2015?",
            "Compare credit card vs cash tip amounts",
            "What is the busiest hour on Sundays?",
            "Show total revenue by payment method",
            "Which day of the week has the longest average trips?",
        ]
    }


@app.post("/api/chat", tags=["Chat"])
async def chat(req: ChatRequest, request: Request):
    """
    SSE streaming endpoint — runs the full NL-to-SQL-to-answer pipeline.
    
    Streams events of types: thinking | sql | data | token | done | error
    """
    logger.info(f"[/api/chat] question='{req.question[:80]}'")

    async def event_generator():
        try:
            async for event in run_agent(req.question):
                # Honour client disconnect
                if await request.is_disconnected():
                    logger.info("[/api/chat] Client disconnected early")
                    break
                yield event
        except Exception as e:
            import json
            logger.error(f"[/api/chat] Unhandled error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': 'Internal server error'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",     # disables Nginx buffering on Render
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────
# Dev entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
