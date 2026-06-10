"""
agent.py — LangGraph + LangChain NL-to-SQL agent for QueryFlow.

Architecture (Enterprise conversational BI pipeline):
  - LangGraph StateGraph manages the 4-step pipeline as a proper state machine
  - Each step is a LangGraph node: generate_sql → validate_sql → execute_query → generate_answer
  - State carries question, sql, rows, answer, error across nodes
  - Groq LLaMA3-8b-8192 (free tier) for both SQL generation and answer streaming
  - ClickHouse Cloud executes the validated SQL
  - SSE streaming sends events to the React frontend

LangGraph gives us:
  - Proper state management between pipeline steps
  - Conditional routing (error → stop, success → continue)
  - Observability of each step (what the LangGraph docs call "checkpointing")
  - Easy extension: add tools, memory, retry logic without rewriting pipeline
"""
import os
import re
import json
import logging
from typing import AsyncGenerator, TypedDict, Optional, List, Any
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# LangGraph imports — the actual state machine
from langgraph.graph import StateGraph, END

from database import get_table_schema, run_query

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# LLM — Groq free tier (fastest open inference)
# ─────────────────────────────────────────────
llm = ChatGroq(
    api_key=os.environ["GROQ_API_KEY"],
    model_name="llama-3.1-8b-instant",  # updated from decommissioned llama3-8b-8192
    temperature=0,                # deterministic SQL generation
    streaming=True,
)


# ─────────────────────────────────────────────
# LangGraph State — shared across all nodes
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    """
    State object passed between LangGraph nodes.
    Each node reads from and writes to this state dict.
    """
    question: str                   # user's NL question
    schema: str                     # ClickHouse schema description
    raw_sql: Optional[str]          # LLM-generated raw SQL (may have fences)
    sql: Optional[str]              # validated, cleaned SQL
    rows: Optional[List[dict]]      # ClickHouse query result rows
    answer: Optional[str]           # final NL answer
    error: Optional[str]            # error message if any step fails
    step: str                       # current step name for UI feedback
    retries: int                    # tracks auto-correction loops


# ─────────────────────────────────────────────
# Prompt Templates
# ─────────────────────────────────────────────
SQL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a ClickHouse SQL expert assistant.
{schema}

CRITICAL RULES:
1. Output ONLY the raw SQL query — no explanation, no markdown, no code fences
2. Only SELECT queries are permitted
3. Always use fully qualified table name: nyc_taxi.mart_trips_daily
4. Use ClickHouse syntax (toDate, toMonth, toDayOfWeek, etc.)
5. Add LIMIT 50 unless the question asks for totals/aggregates
"""),
    ("human", "{question}"),
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a friendly data analyst explaining NYC taxi data insights.
A user asked a question, we ran a SQL query on ClickHouse, and got results.
Write a clear, insightful answer in 2-4 sentences.
- Highlight the most interesting number or trend
- Use commas for large numbers (e.g. 1,234,567)
- Mention USD for revenue figures
- Do NOT repeat the SQL query in your answer
- Do NOT say "the data shows" — be direct and conversational
"""),
    ("human", """User question: {question}
SQL executed: {sql}
Query results (first 10 rows): {results}
Give a clear, insightful answer:"""),
])

sql_chain = SQL_PROMPT | llm | StrOutputParser()


# ─────────────────────────────────────────────
# SQL Safety Validator
# ─────────────────────────────────────────────
BLOCKED = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "EXEC", "EXECUTE"}

def validate_sql(raw: str) -> str:
    """Strip markdown fences, validate safety. Raises ValueError on bad SQL."""
    clean = re.sub(r"```sql\s*|```\s*", "", raw, flags=re.IGNORECASE).strip().strip("\"'`")
    first = clean.split()[0].upper() if clean else ""
    if first != "SELECT":
        raise ValueError(f"Only SELECT queries allowed. Got: '{first}'")
    for kw in BLOCKED:
        if re.search(rf"\b{kw}\b", clean.upper()):
            raise ValueError(f"Blocked keyword in query: {kw}")
    return clean


# ─────────────────────────────────────────────
# LangGraph Nodes — one function per pipeline step
# ─────────────────────────────────────────────

def node_generate_sql(state: AgentState) -> AgentState:
    """
    LangGraph Node 1: Generate SQL from NL question using Groq LLaMA3.
    Uses LangChain LCEL chain (SQL_PROMPT | llm | StrOutputParser).
    """
    logger.info(f"[LangGraph] node_generate_sql: '{state['question'][:60]}'")
    retries = state.get("retries", 0)
    
    try:
        # Auto-correction: if looping back due to an error, inject it into the prompt
        q = state["question"]
        if state.get("error"):
            retries += 1
            prev_sql = state.get("sql") or state.get("raw_sql")
            q += f"\n\n[AUTO-CORRECTION REQUIRED]\nPrevious SQL generated: {prev_sql}\nClickHouse Error: {state['error']}\nFix the query! Ensure all metrics are properly aggregated with AVG() or SUM() when using GROUP BY."
            logger.warning(f"[LangGraph] Auto-correcting SQL (Retry {retries}/2)")

        raw_sql = sql_chain.invoke({
            "schema": state["schema"],
            "question": q,
        })
        return {**state, "raw_sql": raw_sql, "step": "sql_generated", "error": None, "retries": retries}
    except Exception as e:
        logger.error(f"[LangGraph] node_generate_sql error: {e}")
        return {**state, "error": f"SQL generation failed: {str(e)}", "step": "error", "retries": retries}


def node_validate_sql(state: AgentState) -> AgentState:
    """
    LangGraph Node 2: Validate and sanitize the generated SQL.
    Blocks non-SELECT queries and dangerous keywords.
    """
    logger.info("[LangGraph] node_validate_sql")
    try:
        clean_sql = validate_sql(state["raw_sql"] or "")
        return {**state, "sql": clean_sql, "step": "sql_validated"}
    except ValueError as e:
        logger.warning(f"[LangGraph] node_validate_sql rejected: {e}")
        return {**state, "error": str(e), "step": "error"}


def node_execute_query(state: AgentState) -> AgentState:
    """
    LangGraph Node 3: Execute the validated SQL on ClickHouse Cloud.
    Returns up to 50 result rows as a list of dicts.
    """
    logger.info(f"[LangGraph] node_execute_query: {state['sql'][:80]}")
    try:
        rows = run_query(state["sql"])
        return {**state, "rows": rows, "step": "query_executed", "error": None}
    except Exception as e:
        logger.error(f"[LangGraph] node_execute_query error: {e}")
        return {**state, "error": f"Query execution failed: {str(e)}", "step": "error"}


def node_generate_answer(state: AgentState) -> AgentState:
    """
    LangGraph Node 4: Generate natural language answer from SQL results.
    Uses Groq LLaMA3 to explain the data in plain English.
    Note: Full streaming happens at the SSE level — this node stores answer in state.
    """
    logger.info("[LangGraph] node_generate_answer")
    rows = state.get("rows") or []
    if not rows:
        return {**state, "answer": "The query returned no results. Try rephrasing your question.", "step": "done"}

    try:
        answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
        answer = answer_chain.invoke({
            "question": state["question"],
            "sql": state["sql"],
            "results": str(rows[:10]),
        })
        return {**state, "answer": answer, "step": "done"}
    except Exception as e:
        logger.error(f"[LangGraph] node_generate_answer error: {e}")
        return {**state, "error": f"Answer generation failed: {str(e)}", "step": "error"}


# ─────────────────────────────────────────────
# LangGraph Conditional Routing
# ─────────────────────────────────────────────

def route_after_sql_gen(state: AgentState) -> str:
    """Route: if SQL generation failed → END, else → validate"""
    return "error" if state.get("error") else "validate_sql"

def route_after_validation(state: AgentState) -> str:
    """Route: if validation failed → try auto-correct, else → execute"""
    if state.get("error"):
        return "generate_sql" if state.get("retries", 0) < 2 else "error"
    return "execute_query"

def route_after_execution(state: AgentState) -> str:
    """Route: if execution failed → try auto-correct, else → answer"""
    if state.get("error"):
        return "generate_sql" if state.get("retries", 0) < 2 else "error"
    return "generate_answer"


# ─────────────────────────────────────────────
# Build the LangGraph State Machine
# ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Constructs the LangGraph StateGraph pipeline.

    Flow:
      START → generate_sql → [conditional] → validate_sql
                                           → generate_answer
                                           → execute_query
                                           → END
                                           → error → END (at any stage)
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("generate_sql", node_generate_sql)
    graph.add_node("validate_sql", node_validate_sql)
    graph.add_node("execute_query", node_execute_query)
    graph.add_node("generate_answer", node_generate_answer)

    # Error is just a passthrough node that leads to END
    graph.add_node("error", lambda state: state)

    # Entry point
    graph.set_entry_point("generate_sql")

    # Conditional edges — route based on error state
    graph.add_conditional_edges(
        "generate_sql",
        route_after_sql_gen,
        {"validate_sql": "validate_sql", "error": "error"}
    )
    graph.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {"execute_query": "execute_query", "error": "error", "generate_sql": "generate_sql"}
    )
    graph.add_conditional_edges(
        "execute_query",
        route_after_execution,
        {"generate_answer": "generate_answer", "error": "error", "generate_sql": "generate_sql"}
    )

    # Terminal edges
    graph.add_edge("generate_answer", END)
    graph.add_edge("error", END)

    return graph.compile()


# Compile once at startup (expensive operation)
compiled_graph = build_graph()
logger.info("[LangGraph] StateGraph compiled: generate_sql → validate_sql → execute_query → generate_answer")


# ─────────────────────────────────────────────
# Main SSE Generator — runs graph + streams events
# ─────────────────────────────────────────────

async def run_agent(question: str) -> AsyncGenerator[str, None]:
    """
    Execute the LangGraph pipeline and stream SSE events to the React frontend.

    Event types:
      {"type": "thinking"}                      — pipeline started
      {"type": "step", "content": "..."}        — current LangGraph node name
      {"type": "sql", "content": "SELECT..."}   — validated SQL query
      {"type": "data", "content": [...]}         — ClickHouse result rows
      {"type": "token", "content": "..."}        — streaming answer token
      {"type": "done"}                           — stream complete
      {"type": "error", "content": "..."}        — pipeline error
    """
    def sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    yield sse({"type": "thinking"})

    # Build initial state for LangGraph
    initial_state: AgentState = {
        "question": question,
        "schema": get_table_schema(),
        "raw_sql": None,
        "sql": None,
        "rows": None,
        "answer": None,
        "error": None,
        "step": "start",
        "retries": 0,
    }

    # ── Run LangGraph pipeline (step-by-step with streaming) ──
    # LangGraph's stream() yields state snapshots after each node
    final_state = None
    try:
        for state_snapshot in compiled_graph.stream(initial_state):
            # state_snapshot is a dict: {node_name: AgentState}
            for node_name, node_state in state_snapshot.items():
                step = node_state.get("step", "")
                logger.info(f"[LangGraph] Node completed: {node_name} → step={step}")

                # Stream step progress event
                yield sse({"type": "step", "content": node_name.replace("_", " ").title()})

                # If SQL was just validated — send it to frontend
                if node_name == "validate_sql" and node_state.get("sql"):
                    yield sse({"type": "sql", "content": node_state["sql"]})

                # If query was just executed — send rows to frontend
                if node_name == "execute_query" and node_state.get("rows") is not None:
                    yield sse({"type": "data", "content": node_state["rows"]})

                # If there's an error — stream it and stop
                if node_state.get("error"):
                    yield sse({"type": "error", "content": node_state["error"]})
                    yield sse({"type": "done"})
                    return

                final_state = node_state

    except Exception as e:
        logger.error(f"[LangGraph] Graph execution failed: {e}", exc_info=True)
        yield sse({"type": "error", "content": f"Agent pipeline failed: {str(e)}"})
        yield sse({"type": "done"})
        return

    # ── Stream the answer token-by-token for real-time feel ──
    if final_state and final_state.get("answer"):
        answer = final_state["answer"]
        rows = final_state.get("rows") or []

        # Stream answer word by word (simulate streaming since graph ran sync)
        # For true streaming: run answer_chain.astream directly here
        answer_chain = ANSWER_PROMPT | llm
        try:
            async for chunk in answer_chain.astream({
                "question": question,
                "sql": final_state.get("sql", ""),
                "results": str(rows[:10]),
            }):
                if chunk.content:
                    yield sse({"type": "token", "content": chunk.content})
        except Exception as e:
            # Fallback: send the answer from graph state as single token
            logger.warning(f"[LangGraph] Streaming fallback: {e}")
            yield sse({"type": "token", "content": answer})

    yield sse({"type": "done"})
    logger.info("[LangGraph] run_agent complete")
