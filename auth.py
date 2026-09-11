import os

from mcp.server.auth.provider import AccessToken, TokenVerifier


class StaticTokenVerifier(TokenVerifier):
    """Gates the hosted server behind a single static bearer token.

    This is a single-user personal tool, not a multi-tenant service - a plain
    shared-secret compare is proportionate. The client must send
    `Authorization: Bearer <MCP_AUTH_TOKEN>`.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        expected = os.environ.get("MCP_AUTH_TOKEN")
        if expected and token == expected:
            return AccessToken(token=token, client_id="owner", scopes=[])
        return None
