"""FastMCP server instance and tool registration."""

from __future__ import annotations

from fastmcp import FastMCP

from app.mcp.tools_private import (
    ask_private_member_question,
    get_order_status,
    search_member_catalog,
)
from app.mcp.tools_public import ask_public_product_question, search_public_catalog

mcp = FastMCP(
    "Shopping Assistant MCP",
    instructions=(
        "Shopping assistant for a retail site. "
        "Use public tools for catalog and policies; use private tools for orders and member-only content. "
        "If a private tool returns requires_auth, guide the user to auth_url and ask them to retry with their bearer token."
    ),
)

mcp.tool(search_public_catalog)
mcp.tool(ask_public_product_question)
mcp.tool(get_order_status)
mcp.tool(search_member_catalog)
mcp.tool(ask_private_member_question)
