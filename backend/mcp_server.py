"""
mcp_server.py — Model Context Protocol (MCP) server for QueryFlow.

MCP lets any MCP-compatible AI client (Claude Desktop, Cursor, Windsurf, etc.)
call QueryFlow's ClickHouse tools directly — without the React frontend.

This implements the official MCP Python SDK pattern:
  https://github.com/modelcontextprotocol/python-sdk

Tools exposed via MCP:
  1. run_clickhouse_query(sql)     — execute any SELECT on ClickHouse
  2. nl_to_sql(question)           — convert NL question to ClickHouse SQL
  3. get_schema()                  — return the table schema description
  4. query_insights(question)      — full NL→SQL→execute→answer pipeline

Usage (stdio transport — for Claude Desktop / Cursor integration):
  python mcp_server.py

Usage (HTTP transport — for remote MCP clients):
  python mcp_server.py --transport http --port 8001
"""
import os
import json
import asyncio
import logging
from typing import Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# MCP SDK
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp import types
    import mcp.server.stdio
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not installed. Run: pip install mcp")

# LangChain + ClickHouse
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from database import get_client, get_table_schema, run_query

# ─────────────────────────────────────────────
# LLM for MCP tools
# ─────────────────────────────────────────────
llm = ChatGroq(
    api_key=os.environ["GROQ_API_KEY"],
    model_name="llama-3.1-8b-instant",
    temperature=0,
)

SQL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a ClickHouse SQL expert.
{schema}
Output ONLY the raw SQL SELECT query. No markdown. No explanation."""),
    ("human", "{question}"),
])
sql_chain = SQL_PROMPT | llm | StrOutputParser()


# ─────────────────────────────────────────────
# Tool implementations (framework-agnostic)
# ─────────────────────────────────────────────

def tool_get_schema() -> str:
    """Return ClickHouse table schema description."""
    return get_table_schema()


def tool_run_clickhouse_query(sql: str) -> dict:
    """
    Execute a ClickHouse SELECT query and return results.
    Returns: {"rows": [...], "count": N, "columns": [...]}
    """
    import re
    # Safety check
    clean = sql.strip()
    if not clean.upper().startswith("SELECT"):
        return {"error": "Only SELECT queries are permitted"}
    for kw in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"]:
        if re.search(rf"\b{kw}\b", clean.upper()):
            return {"error": f"Blocked keyword: {kw}"}

    try:
        rows = run_query(clean)
        cols = list(rows[0].keys()) if rows else []
        return {
            "rows": rows[:25],
            "count": len(rows),
            "columns": cols,
            "sql_executed": clean,
        }
    except Exception as e:
        return {"error": str(e)}


def tool_nl_to_sql(question: str) -> dict:
    """Convert a natural language question to ClickHouse SQL."""
    try:
        sql = sql_chain.invoke({
            "schema": get_table_schema(),
            "question": question,
        })
        # Clean SQL
        import re
        sql = re.sub(r"```sql\s*|```\s*", "", sql, flags=re.IGNORECASE).strip().strip("\"'`")
        return {"sql": sql, "question": question}
    except Exception as e:
        return {"error": str(e)}


def tool_query_insights(question: str) -> dict:
    """
    Full pipeline: NL question → SQL → ClickHouse execution → NL answer.
    Returns the complete response with SQL, data, and answer.
    """
    # Step 1: NL → SQL
    sql_result = tool_nl_to_sql(question)
    if "error" in sql_result:
        return sql_result

    sql = sql_result["sql"]

    # Step 2: Execute
    query_result = tool_run_clickhouse_query(sql)
    if "error" in query_result:
        return {**query_result, "sql": sql}

    rows = query_result["rows"]

    # Step 3: Generate answer
    try:
        answer_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a data analyst. Explain the query results in 2-3 sentences."),
            ("human", "Question: {question}\nSQL: {sql}\nResults: {results}\nAnswer:"),
        ])
        answer_chain = answer_prompt | llm | StrOutputParser()
        answer = answer_chain.invoke({
            "question": question,
            "sql": sql,
            "results": str(rows[:5]),
        })
        return {
            "question": question,
            "sql": sql,
            "rows": rows,
            "row_count": len(rows),
            "answer": answer,
        }
    except Exception as e:
        return {
            "question": question,
            "sql": sql,
            "rows": rows,
            "row_count": len(rows),
            "answer": f"Query succeeded ({len(rows)} rows returned)",
        }


# ─────────────────────────────────────────────
# MCP Server Setup
# ─────────────────────────────────────────────

if MCP_AVAILABLE:
    app = Server("queryflow-mcp")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """Declare all tools available via MCP."""
        return [
            types.Tool(
                name="get_schema",
                description="Get the ClickHouse database schema — table name, columns, types, and example queries for the NYC taxi dataset.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            types.Tool(
                name="run_clickhouse_query",
                description="Execute a ClickHouse SQL SELECT query on the NYC taxi dataset. Returns rows as JSON. Only SELECT queries are permitted.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "A valid ClickHouse SELECT query. Table: nyc_taxi.mart_trips_daily",
                        }
                    },
                    "required": ["sql"],
                },
            ),
            types.Tool(
                name="nl_to_sql",
                description="Convert a natural language question to a ClickHouse SQL query using Groq LLaMA3. Returns the SQL without executing it.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Natural language analytics question about NYC taxi data",
                        }
                    },
                    "required": ["question"],
                },
            ),
            types.Tool(
                name="query_insights",
                description="Full pipeline: convert NL question → SQL → execute on ClickHouse → return answer. The highest-level tool for conversational analytics.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "Natural language question about NYC taxi data, e.g. 'What were the top 5 revenue hours on weekdays?'",
                        }
                    },
                    "required": ["question"],
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Route MCP tool calls to the appropriate handler."""
        logger.info(f"[MCP] Tool called: {name} args={arguments}")

        if name == "get_schema":
            result = tool_get_schema()

        elif name == "run_clickhouse_query":
            sql = arguments.get("sql", "")
            result = tool_run_clickhouse_query(sql)

        elif name == "nl_to_sql":
            question = arguments.get("question", "")
            result = tool_nl_to_sql(question)

        elif name == "query_insights":
            question = arguments.get("question", "")
            result = tool_query_insights(question)

        else:
            result = {"error": f"Unknown tool: {name}"}

        # MCP expects TextContent responses
        if isinstance(result, str):
            content = result
        else:
            content = json.dumps(result, indent=2, default=str)

        return [types.TextContent(type="text", text=content)]


    async def run_mcp_server():
        """Start the MCP server with stdio transport (for Claude Desktop / Cursor)."""
        logger.info("[MCP] Starting QueryFlow MCP server (stdio transport)")
        logger.info("[MCP] Tools: get_schema, run_clickhouse_query, nl_to_sql, query_insights")

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="queryflow",
                    server_version="1.0.0",
                    capabilities=app.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if MCP_AVAILABLE:
        asyncio.run(run_mcp_server())
    else:
        print("ERROR: MCP SDK not installed.")
        print("Run: pip install mcp")
        print()
        print("Testing tools without MCP SDK:")
        print(json.dumps(tool_get_schema()[:200] + "...", indent=2))
