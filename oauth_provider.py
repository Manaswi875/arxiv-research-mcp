"""Minimal single-user OAuth authorization server for the hosted deployment.

Adapted from the MCP Python SDK's reference implementation
(examples/servers/simple-auth/mcp_simple_auth/simple_auth_provider.py), with
two changes: all state is persisted in Postgres via db.oauth_* instead of
in-memory dicts (a serverless invocation can't assume anything survived in
process memory), and the login form asks for the single owner token
(MCP_AUTH_TOKEN) instead of a demo username/password - this is a single-user
tool, not a multi-tenant service.
"""

import os
import secrets
import time

from pydantic import AnyHttpUrl
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

import db

MCP_SCOPE = "user"
STATE_TTL_SECONDS = 600  # 10 min to complete the login form
CODE_TTL_SECONDS = 300  # 5 min to exchange the code for a token
TOKEN_TTL_SECONDS = 3600  # 1 hour access token


class SimpleOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):
    def __init__(self, auth_callback_url: str, server_url: str):
        self.auth_callback_url = auth_callback_url
        self.server_url = server_url

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        data = db.oauth_get("client", client_id)
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if not client_info.client_id:
            raise ValueError("No client_id provided")
        db.oauth_set("client", client_info.client_id, client_info.model_dump(mode="json"))

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        """Redirect straight to our own login form instead of a real IdP."""
        state = params.state or secrets.token_hex(16)
        db.oauth_set(
            "state",
            state,
            {
                "redirect_uri": str(params.redirect_uri),
                "code_challenge": params.code_challenge,
                "redirect_uri_provided_explicitly": str(params.redirect_uri_provided_explicitly),
                "client_id": client.client_id,
                "resource": params.resource,  # RFC 8707
            },
            ttl_seconds=STATE_TTL_SECONDS,
        )
        return f"{self.auth_callback_url}?state={state}&client_id={client.client_id}"

    async def get_login_page(self, state: str) -> HTMLResponse:
        if not state:
            raise HTTPException(400, "Missing state parameter")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ArXiv Research Assistant - Sign in</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 420px; margin: 60px auto; padding: 20px; }}
                input {{ width: 100%; padding: 8px; margin-top: 5px; margin-bottom: 15px; box-sizing: border-box; }}
                button {{ background-color: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; width: 100%; }}
            </style>
        </head>
        <body>
            <h2>ArXiv Research Assistant</h2>
            <p>Enter the owner access token to authorize this app.</p>
            <form action="{self.server_url.rstrip('/')}/login/callback" method="post">
                <input type="hidden" name="state" value="{state}">
                <label>Access Token:</label>
                <input type="password" name="token" required autofocus>
                <button type="submit">Authorize</button>
            </form>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    async def handle_login_callback(self, request: Request) -> Response:
        form = await request.form()
        token = form.get("token")
        state = form.get("state")

        if not token or not state or not isinstance(token, str) or not isinstance(state, str):
            raise HTTPException(400, "Missing or invalid token/state parameter")

        redirect_uri = await self._complete_login(token, state)
        return RedirectResponse(url=redirect_uri, status_code=302)

    async def _complete_login(self, token: str, state: str) -> str:
        state_data = db.oauth_get("state", state)
        if not state_data:
            raise HTTPException(400, "Invalid or expired state parameter - please try again")

        expected_token = os.environ.get("MCP_AUTH_TOKEN")
        if not expected_token or token != expected_token:
            raise HTTPException(401, "Invalid access token")

        redirect_uri = state_data["redirect_uri"]
        code_challenge = state_data["code_challenge"]
        redirect_uri_provided_explicitly = state_data["redirect_uri_provided_explicitly"] == "True"
        client_id = state_data["client_id"]
        resource = state_data.get("resource")  # RFC 8707

        new_code = f"mcp_{secrets.token_hex(16)}"
        auth_code = AuthorizationCode(
            code=new_code,
            client_id=client_id,
            redirect_uri=AnyHttpUrl(redirect_uri),
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            expires_at=time.time() + CODE_TTL_SECONDS,
            scopes=[MCP_SCOPE],
            code_challenge=code_challenge,
            resource=resource,
            subject="owner",
        )
        db.oauth_set("auth_code", new_code, auth_code.model_dump(mode="json"), ttl_seconds=CODE_TTL_SECONDS)
        db.oauth_delete("state", state)

        return construct_redirect_uri(redirect_uri, code=new_code, state=state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        data = db.oauth_get("auth_code", authorization_code)
        return AuthorizationCode.model_validate(data) if data else None

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        if not db.oauth_get("auth_code", authorization_code.code):
            raise ValueError("Invalid authorization code")
        if not client.client_id:
            raise ValueError("No client_id provided")

        mcp_token = f"mcp_{secrets.token_hex(32)}"
        access_token = AccessToken(
            token=mcp_token,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(time.time()) + TOKEN_TTL_SECONDS,
            resource=authorization_code.resource,
            subject=authorization_code.subject,
        )
        db.oauth_set("token", mcp_token, access_token.model_dump(mode="json"), ttl_seconds=TOKEN_TTL_SECONDS)
        db.oauth_delete("auth_code", authorization_code.code)

        return OAuthToken(
            access_token=mcp_token,
            token_type="Bearer",
            expires_in=TOKEN_TTL_SECONDS,
            scope=" ".join(authorization_code.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        data = db.oauth_get("token", token)
        if not data:
            return None
        access_token = AccessToken.model_validate(data)
        if access_token.expires_at and access_token.expires_at < time.time():
            db.oauth_delete("token", token)
            return None
        return access_token

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> RefreshToken | None:
        return None  # not supported

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        raise NotImplementedError("Refresh tokens not supported - re-authorize instead")

    async def revoke_token(self, token: str, token_type_hint: str | None = None) -> None:
        db.oauth_delete("token", token)
