from research_server import mcp

# Vercel's Python runtime looks for a top-level `app` ASGI/WSGI variable in
# this entrypoint file. FastMCP's Starlette app does its own internal
# routing (to /mcp by default) - see vercel.json for the catch-all rewrite
# that forwards every request here.
app = mcp.streamable_http_app()
