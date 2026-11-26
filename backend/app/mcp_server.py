"""Expose the support tools over the Model Context Protocol (MCP).

Any MCP client (Claude Desktop, Cursor, MCP Inspector, ...) can connect to this
server and use the same tools the web agent uses.

Run it with:
    python -m app.mcp_server            # stdio, for desktop clients
    python -m app.mcp_server --http     # streamable HTTP on port 8001
"""

import sys

from mcp.server.mcpserver import MCPServer

from .db import init_db
from .tools import TOOLS

server = MCPServer(
    name="acme-support",
    instructions="Tools for Acme Gadgets customer support: order lookup, cancellation, help articles and tickets.",
)

for name, fn in TOOLS.items():
    server.add_tool(fn, name=name, description=(fn.__doc__ or "").strip())


def main() -> None:
    init_db()
    if "--http" in sys.argv:
        server.run(transport="streamable-http", port=8001)
    else:
        server.run()


if __name__ == "__main__":
    main()
