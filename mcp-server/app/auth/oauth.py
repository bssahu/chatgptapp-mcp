"""Mock OAuth2 Authorization Code flow (POC)."""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.auth import session_store
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _base() -> str:
    return settings.public_base_url.rstrip("/")


HTML_LOGIN = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Shopping MCP — Sign in</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 520px; margin: 2rem auto; padding: 0 1rem; }}
    label {{ display: block; margin: 0.75rem 0 0.25rem; }}
    select, button {{ width: 100%; padding: 0.6rem; font-size: 1rem; }}
    .hint {{ color: #444; font-size: 0.9rem; margin-top: 1rem; }}
    code {{ background: #f4f4f4; padding: 0.1rem 0.3rem; }}
  </style>
</head>
<body>
  <h1>Mock OAuth2 Login</h1>
  <p>This POC simulates an OAuth2 authorization server. Pick a demo user to obtain tokens stored in MongoDB.</p>
  <form method="post" action="{base}/auth/authorize">
    <input type="hidden" name="client_id" value="{client_id}"/>
    <input type="hidden" name="redirect_uri" value="{redirect_uri}"/>
    <input type="hidden" name="state" value="{state}"/>
    <label for="user_id">Demo user</label>
    <select name="user_id" id="user_id">
      <option value="user-001">user-001 (Alex)</option>
      <option value="user-002">user-002 (Sam)</option>
    </select>
    <p class="hint">After login you will receive an access token to pass as <code>Authorization: Bearer &lt;token&gt;</code> to MCP (or use the token query shown on the success page).</p>
    <button type="submit">Authorize</button>
  </form>
</body>
</html>
"""


@router.get("/login", response_class=HTMLResponse)
async def auth_login(
    client_id: str | None = Query(default=None),
    redirect_uri: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> HTMLResponse:
    """OAuth2-style authorize screen (mock)."""
    cid = client_id or settings.mock_oauth_client_id
    redir = redirect_uri or f"{_base()}/auth/callback"
    st = state or secrets.token_urlsafe(16)
    html = HTML_LOGIN.format(base=_base(), client_id=cid, redirect_uri=redir, state=st)
    return HTMLResponse(html)


@router.post("/authorize")
async def auth_authorize(
    user_id: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    state: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """Issue authorization code and redirect to redirect_uri or local callback."""
    code = secrets.token_urlsafe(32)
    await session_store.store_oauth_code(
        code=code,
        user_id=user_id.strip(),
        redirect_uri=redirect_uri.strip(),
        client_id=client_id.strip(),
    )
    sep = "&" if "?" in redirect_uri else "?"
    location = f"{redirect_uri}{sep}code={code}&state={state}"
    return RedirectResponse(location, status_code=302)


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    format: str | None = Query(default=None, alias="format"),
) -> Response:
    """
    OAuth redirect_uri target: exchange code for session + bearer token.
    Returns HTML by default with copyable token; use ?format=json for JSON.
    """
    if not code:
        raise HTTPException(status_code=400, detail="missing code")
    doc = await session_store.consume_oauth_code(code)
    if not doc:
        raise HTTPException(status_code=400, detail="invalid or expired code")
    user_id = str(doc["user_id"])
    session_id, access_token, expires_at = await session_store.create_session(user_id=user_id)

    if format == "json":
        return JSONResponse(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_at": expires_at.isoformat(),
                "session_id": session_id,
                "user_id": user_id,
                "state": state,
            }
        )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Authorized</title></head>
<body style="font-family:system-ui;max-width:720px;margin:2rem auto;">
<h1>Authenticated</h1>
<p>User: <strong>{user_id}</strong></p>
<p>Copy this bearer token into your ChatGPT App / MCP client configuration:</p>
<p style="word-break:break-all;background:#f4f4f4;padding:1rem;"><code>{access_token}</code></p>
<p>Send header: <code>Authorization: Bearer {access_token}</code></p>
<p><a href="{_base()}/auth/status?access_token={access_token}">Check status (JSON)</a></p>
</body></html>"""
    resp = HTMLResponse(html)
    resp.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return resp


@router.post("/token")
async def auth_token(
    grant_type: Annotated[str, Form()],
    code: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str, Form()],
) -> JSONResponse:
    """OAuth2 token endpoint (authorization_code)."""
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported grant_type")
    if client_id != settings.mock_oauth_client_id:
        raise HTTPException(status_code=401, detail="invalid client")
    if client_secret != settings.mock_oauth_client_secret:
        raise HTTPException(status_code=401, detail="invalid client")
    doc = await session_store.consume_oauth_code(code)
    if not doc:
        raise HTTPException(status_code=400, detail="invalid or expired code")
    if doc.get("redirect_uri") != redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri mismatch")
    if doc.get("client_id") != client_id:
        raise HTTPException(status_code=400, detail="client_id mismatch")
    user_id = str(doc["user_id"])
    _session_id, access_token, expires_at = await session_store.create_session(user_id=user_id)
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": int((expires_at - datetime.now(tz=UTC)).total_seconds()),
        }
    )


@router.get("/status")
async def auth_status(
    request: Request,
    access_token: str | None = Query(default=None),
) -> JSONResponse:
    """Return whether the bearer token or session cookie is valid."""
    token = access_token
    if not token:
        sid = request.cookies.get(settings.session_cookie_name)
        if sid:
            sess = await session_store.get_session_by_session_id(sid)
            if sess:
                token = str(sess.get("access_token"))
    if not token:
        return JSONResponse({"authenticated": False})
    sess = await session_store.get_session_by_access_token(token)
    if not sess:
        return JSONResponse({"authenticated": False})
    return JSONResponse(
        {
            "authenticated": True,
            "user_id": sess.get("user_id"),
            "expires_at": sess.get("expires_at").isoformat()
            if sess.get("expires_at")
            else None,
        }
    )


@router.post("/logout")
async def auth_logout(
    request: Request,
    access_token: Annotated[str | None, Form()] = None,
) -> JSONResponse:
    """Revoke session by bearer token or cookie."""
    tok = access_token
    if not tok:
        sid = request.cookies.get(settings.session_cookie_name)
        if sid:
            sess = await session_store.get_session_by_session_id(sid)
            if sess:
                tok = str(sess.get("access_token"))
    if tok:
        await session_store.delete_session_by_access_token(tok)
    resp = JSONResponse({"logged_out": True})
    resp.delete_cookie(settings.session_cookie_name)
    return resp
