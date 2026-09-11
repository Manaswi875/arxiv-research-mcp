"""Web dashboard for the ArXiv Research Assistant.

Registers plain Starlette routes via @mcp.custom_route, which explicitly bypass
FastMCP's OAuth middleware (confirmed from the library's own docstring - those
routes "will not require authorization"). So this module implements its own
gate: a stateless HMAC-signed session cookie keyed by the same MCP_AUTH_TOKEN
already used for the OAuth login form in oauth_provider.py - no second secret,
no session storage (matches db.get_connection()'s "no persistent state assumed"
design). Fails closed: if MCP_AUTH_TOKEN isn't set, every route 503s rather
than serving the bibliography with no gate at all.

Functions from research_server.py are injected into register_dashboard_routes
rather than imported, so this module never imports research_server (avoids a
circular import - research_server imports this module to call it).
"""

import hashlib
import hmac
import os
import time
import traceback
from collections import Counter
from urllib.parse import quote

from jinja2 import DictLoader, Environment, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from analyze_references import analyze
from generate_network import generate_graph
from research_trends import analyze_trends
import db

COOKIE_NAME = "arxiv_dashboard_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600

BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<title>{% block title %}ArXiv Research Assistant{% endblock %}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
         max-width: 1000px; margin: 0 auto; padding: 24px; color: #1e293b; background: #f8fafc; }
  h1, h2 { color: #1e293b; margin-top: 0; }
  .card { background: white; border: 1px solid #e2e8f0; border-radius: 10px;
          padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 1px 2px rgb(0 0 0 / 0.05); }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; font-size: 14px; vertical-align: top; }
  th { color: #64748b; font-weight: 600; }
  .topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
  .btn { background: #2563eb; color: white; border: none; padding: 8px 16px;
         border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; }
  .btn:hover { background: #1d4ed8; }
  .muted { color: #64748b; font-size: 13px; }
  iframe { border: 1px solid #e2e8f0; border-radius: 8px; width: 100%; height: 500px; }
  img { max-width: 100%; border-radius: 8px; }
  a { color: #2563eb; text-decoration: none; }
  input[type=password] { width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #e2e8f0; border-radius: 6px; box-sizing: border-box; }
  pre { white-space: pre-wrap; font-family: inherit; line-height: 1.5; }
  .topic-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 14px; }
</style>
</head>
<body>
{% block content %}{% endblock %}
</body>
</html>
"""

LOGIN_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<div class="card" style="max-width: 400px; margin: 80px auto;">
  <h2>🎓 ArXiv Research Assistant</h2>
  <p class="muted">Enter the access token to view the dashboard.</p>
  <form method="post" action="/dashboard/login">
    <input type="hidden" name="next" value="{{ next }}">
    <input type="password" name="token" placeholder="Access token" required autofocus>
    <button class="btn" style="width: 100%;" type="submit">Sign in</button>
  </form>
  {% if error %}<p style="color: #dc2626;">{{ error }}</p>{% endif %}
</div>
{% endblock %}
"""

DASHBOARD_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
<div class="topbar">
  <h1>🎓 ArXiv Research Assistant</h1>
  <a href="/dashboard/logout">Sign out</a>
</div>

{% if error %}
<div class="card" style="border-left: 4px solid #dc2626; background: #fef2f2;">
  <strong style="color: #dc2626;">Error:</strong> {{ error }}
</div>
{% endif %}

<div class="card">
  <h2>Bibliography ({{ papers|length }} papers)</h2>
  {% if papers %}
  <table>
    <tr><th>#</th><th>Title</th><th>Authors</th><th>Published</th><th>Topic</th></tr>
    {% for p in papers %}
    <tr>
      <td>{{ loop.index }}</td>
      <td>{{ p.title }}</td>
      <td>{{ p.authors|join(", ") }}</td>
      <td>{{ p.published or "—" }}</td>
      <td>{{ p.topic_label or "—" }}</td>
    </tr>
    {% endfor %}
  </table>
  {% else %}
  <p class="muted">No papers saved yet. Ask your assistant to search ArXiv and save some.</p>
  {% endif %}
</div>

<div class="card">
  <h2>Topic Clusters</h2>
  {% if topic_counts %}
    {% for label, count in topic_counts %}
    <div class="topic-row"><span>{{ label }}</span><span class="muted">{{ count }} paper{{ "s" if count != 1 }}</span></div>
    {% endfor %}
  {% else %}
    <p class="muted">No topics computed yet.</p>
  {% endif %}
  <form method="post" action="/dashboard/api/recompute-topics" style="margin-top: 12px;">
    <button class="btn" type="submit">Recompute Topics</button>
  </form>
</div>

<div class="card">
  <h2>Method Keyword Trends</h2>
  <img src="/dashboard/api/keyword-chart.png" alt="Method keyword chart">
</div>

<div class="card">
  <h2>Research Topics Over Time</h2>
  <img src="/dashboard/api/trends-chart.png" alt="Research trends chart">
</div>

<div class="card">
  <h2>Author Network</h2>
  <iframe src="/dashboard/api/author-network.html"></iframe>
</div>

<div class="card">
  <h2>Literature Review</h2>
  <form method="post" action="/dashboard/api/literature-review">
    <button class="btn" type="submit">{{ "Regenerate" if review else "Generate" }} Review</button>
  </form>
  {% if review %}
    <p class="muted">Generated {{ review.generated_at }} from {{ review.paper_count }} papers.</p>
    <pre>{{ review.content }}</pre>
  {% endif %}
</div>
{% endblock %}
"""

_env = Environment(
    loader=DictLoader({
        "base.html": BASE_TEMPLATE,
        "login.html": LOGIN_TEMPLATE,
        "dashboard.html": DASHBOARD_TEMPLATE,
    }),
    autoescape=select_autoescape(["html"]),
)


def _sign(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _make_session_cookie(secret: str) -> str:
    expiry = str(int(time.time()) + SESSION_TTL_SECONDS)
    return f"{expiry}.{_sign(expiry, secret)}"


def _is_valid_session_cookie(value: str | None, secret: str) -> bool:
    if not value or "." not in value:
        return False
    expiry_str, _, signature = value.partition(".")
    if not expiry_str.isdigit():
        return False
    if int(expiry_str) < time.time():
        return False
    return hmac.compare_digest(_sign(expiry_str, secret), signature)


def _safe_next_path(value: object) -> str:
    """Only allow same-site relative paths - never an open redirect."""
    if isinstance(value, str) and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


def _require_session(request: Request) -> Response | None:
    """Returns a redirect/error Response if the request isn't authenticated, else None."""
    secret = os.environ.get("MCP_AUTH_TOKEN")
    if not secret:
        return PlainTextResponse("Dashboard is not configured (MCP_AUTH_TOKEN not set).", status_code=503)
    if not _is_valid_session_cookie(request.cookies.get(COOKIE_NAME), secret):
        return RedirectResponse(url=f"/dashboard/login?next={request.url.path}", status_code=302)
    return None


def _is_hosted() -> bool:
    return bool(os.environ.get("MCP_SERVER_URL"))


def register_dashboard_routes(mcp, generate_review_fn, recompute_topics_fn) -> None:
    @mcp.custom_route("/", methods=["GET"])
    async def dashboard_home(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        papers = db.fetch_all_papers()
        review = db.get_latest_literature_review()
        topic_counts = Counter(p.get("topic_label") or "Uncategorized" for p in papers if p.get("topic_id") is not None)
        template = _env.get_template("dashboard.html")
        return HTMLResponse(template.render(
            papers=papers, review=review, topic_counts=topic_counts.most_common(),
            error=request.query_params.get("error"),
        ))

    @mcp.custom_route("/dashboard/login", methods=["GET"])
    async def login_page(request: Request) -> Response:
        secret = os.environ.get("MCP_AUTH_TOKEN")
        if not secret:
            return PlainTextResponse("Dashboard is not configured (MCP_AUTH_TOKEN not set).", status_code=503)
        next_path = _safe_next_path(request.query_params.get("next"))
        template = _env.get_template("login.html")
        return HTMLResponse(template.render(next=next_path, error=None))

    @mcp.custom_route("/dashboard/login", methods=["POST"])
    async def login_submit(request: Request) -> Response:
        secret = os.environ.get("MCP_AUTH_TOKEN")
        if not secret:
            return PlainTextResponse("Dashboard is not configured (MCP_AUTH_TOKEN not set).", status_code=503)
        form = await request.form()
        token = form.get("token")
        next_path = _safe_next_path(form.get("next"))
        if token != secret:
            template = _env.get_template("login.html")
            return HTMLResponse(template.render(next=next_path, error="Invalid access token"), status_code=401)
        response = RedirectResponse(url=next_path, status_code=302)
        response.set_cookie(
            COOKIE_NAME, _make_session_cookie(secret),
            httponly=True, samesite="lax", secure=_is_hosted(), max_age=SESSION_TTL_SECONDS,
        )
        return response

    @mcp.custom_route("/dashboard/logout", methods=["GET"])
    async def logout(request: Request) -> Response:
        response = RedirectResponse(url="/dashboard/login", status_code=302)
        response.delete_cookie(COOKIE_NAME)
        return response

    @mcp.custom_route("/dashboard/api/author-network.html", methods=["GET"])
    async def author_network_html(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        result = generate_graph()
        html = result.get("html") or "<p style='font-family:sans-serif'>No bibliography yet.</p>"
        return HTMLResponse(html)

    @mcp.custom_route("/dashboard/api/keyword-chart.png", methods=["GET"])
    async def keyword_chart(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        png = analyze().get("chart_png")
        if not png:
            return PlainTextResponse("No chart available yet.", status_code=404)
        return Response(content=png, media_type="image/png")

    @mcp.custom_route("/dashboard/api/trends-chart.png", methods=["GET"])
    async def trends_chart(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        png = analyze_trends().get("chart_png")
        if not png:
            return PlainTextResponse("No chart available yet.", status_code=404)
        return Response(content=png, media_type="image/png")

    @mcp.custom_route("/dashboard/api/recompute-topics", methods=["POST"])
    async def recompute_topics_route(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        try:
            result = recompute_topics_fn()
            if result.get("topic_labels_error"):
                return RedirectResponse(
                    url=f"/?error={quote(f'Topics computed, but labeling failed: ' + result['topic_labels_error'][:250])}",
                    status_code=303,
                )
        except Exception as e:
            traceback.print_exc()  # visible in Vercel function logs
            return RedirectResponse(url=f"/?error={quote(f'Recompute topics failed: {e}'[:300])}", status_code=303)
        return RedirectResponse(url="/", status_code=303)

    @mcp.custom_route("/dashboard/api/literature-review", methods=["POST"])
    async def literature_review_route(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        try:
            generate_review_fn()
        except Exception as e:
            traceback.print_exc()  # visible in Vercel function logs
            return RedirectResponse(url=f"/?error={quote(f'Literature review failed: {e}'[:300])}", status_code=303)
        return RedirectResponse(url="/", status_code=303)
