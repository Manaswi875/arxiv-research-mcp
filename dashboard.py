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

Pages: Overview (/), Papers (/dashboard/papers[/{id}/edit|/delete]),
Topics (/dashboard/topics[/{id}/rename|/recompute]), Review (/dashboard/review
[/save|/regenerate]). Every mutating route follows the same pattern: try the
operation, on failure log the traceback (visible in Vercel logs) and redirect
back with ?error=<message>; on success redirect with ?ok=<message>.
"""

import hashlib
import hmac
import os
import time
import traceback
from datetime import date
from urllib.parse import quote, urlparse

from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response

from analyze_references import analyze
from dashboard_templates import env
from research_trends import analyze_trends
import db
import demo_limits

COOKIE_NAME = "arxiv_dashboard_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600
GUEST_COOKIE_NAME = "arxiv_dashboard_guest"
GUEST_SCOPE = "guest:"
DEMO_READ_ONLY = "Demo mode is read-only - editing is disabled for guests."


def _sign(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _make_session_cookie(secret: str, scope: str = "") -> str:
    """scope="" is the owner session; scope="guest:" is a read-only demo session.
    The scope is part of the signed message, so a guest cookie can't pass as an owner one."""
    expiry = str(int(time.time()) + SESSION_TTL_SECONDS)
    return f"{expiry}.{_sign(scope + expiry, secret)}"


def _is_valid_session_cookie(value: str | None, secret: str, scope: str = "") -> bool:
    if not value or "." not in value:
        return False
    expiry_str, _, signature = value.partition(".")
    if not expiry_str.isdigit():
        return False
    if int(expiry_str) < time.time():
        return False
    return hmac.compare_digest(_sign(scope + expiry_str, secret), signature)


def _session_role(request: Request) -> str | None:
    secret = os.environ.get("MCP_AUTH_TOKEN")
    if not secret:
        return None
    if _is_valid_session_cookie(request.cookies.get(COOKIE_NAME), secret):
        return "owner"
    if _is_valid_session_cookie(request.cookies.get(GUEST_COOKIE_NAME), secret, GUEST_SCOPE):
        return "guest"
    return None


def _render(request: Request, name: str, **context) -> str:
    context.setdefault("error", request.query_params.get("error"))
    context.setdefault("ok", request.query_params.get("ok"))
    context.setdefault("info", request.query_params.get("info"))
    return env.get_template(name).render(is_guest=_session_role(request) == "guest", **context)


def _safe_next_path(value: object) -> str:
    """Only allow same-site relative paths - never an open redirect."""
    if isinstance(value, str) and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


def _require_session(request: Request, owner_only: bool = False) -> Response | None:
    """Returns a redirect/error Response if the request isn't authenticated, else None.
    Guests pass unless owner_only, in which case they're bounced back with a notice."""
    if not os.environ.get("MCP_AUTH_TOKEN"):
        return PlainTextResponse("Dashboard is not configured (MCP_AUTH_TOKEN not set).", status_code=503)
    role = _session_role(request)
    if role is None:
        return RedirectResponse(url=f"/dashboard/login?next={request.url.path}", status_code=302)
    if owner_only and role != "owner":
        back = _safe_next_path(urlparse(request.headers.get("referer") or "").path or "/")
        return _redirect(back, info=DEMO_READ_ONLY)
    return None


def _run_llm_action(request: Request, action: str, fn, back: str):
    """Runs fn() for an AI button. Guests are metered by demo_limits, and when a cap
    or the API credit runs out they're sent back to the saved results with a notice
    instead of an error. Returns (result, None) or (None, redirect Response)."""
    is_guest = _session_role(request) == "guest"
    if is_guest:
        try:
            demo_limits.spend(action, demo_limits.client_ip(request))
        except demo_limits.LimitReached as e:
            return None, _redirect(back, info=f"{e} Here are the saved sample results instead.")
    try:
        return fn(), None
    except Exception as e:
        if is_guest and demo_limits.is_out_of_credit(e):
            return None, _redirect(back, info="The live AI demo is paused right now. Here are the saved sample results instead.")
        raise


def _is_hosted() -> bool:
    return bool(os.environ.get("MCP_SERVER_URL"))


def _redirect(path: str, error: str | None = None, ok: str | None = None, info: str | None = None) -> RedirectResponse:
    params = []
    if error:
        params.append(f"error={quote(error[:300])}")
    if ok:
        params.append(f"ok={quote(ok[:300])}")
    if info:
        params.append(f"info={quote(info[:300])}")
    url = path + ("?" + "&".join(params) if params else "")
    return RedirectResponse(url=url, status_code=303)


def register_dashboard_routes(mcp, generate_review_fn, recompute_topics_fn) -> None:

    # --- Auth ---

    @mcp.custom_route("/dashboard/login", methods=["GET"])
    async def login_page(request: Request) -> Response:
        secret = os.environ.get("MCP_AUTH_TOKEN")
        if not secret:
            return PlainTextResponse("Dashboard is not configured (MCP_AUTH_TOKEN not set).", status_code=503)
        next_path = _safe_next_path(request.query_params.get("next"))
        return HTMLResponse(_render(request, "login.html", next=next_path, error=None))

    @mcp.custom_route("/dashboard/login", methods=["POST"])
    async def login_submit(request: Request) -> Response:
        secret = os.environ.get("MCP_AUTH_TOKEN")
        if not secret:
            return PlainTextResponse("Dashboard is not configured (MCP_AUTH_TOKEN not set).", status_code=503)
        form = await request.form()
        token = form.get("token")
        next_path = _safe_next_path(form.get("next"))
        if token != secret:
            return HTMLResponse(
                _render(request, "login.html", next=next_path, error="Invalid access token"),
                status_code=401,
            )
        response = RedirectResponse(url=next_path, status_code=302)
        response.set_cookie(
            COOKIE_NAME, _make_session_cookie(secret),
            httponly=True, samesite="lax", secure=_is_hosted(), max_age=SESSION_TTL_SECONDS,
        )
        return response

    @mcp.custom_route("/dashboard/demo", methods=["POST"])
    async def demo_login(request: Request) -> Response:
        secret = os.environ.get("MCP_AUTH_TOKEN")
        if not secret:
            return PlainTextResponse("Dashboard is not configured (MCP_AUTH_TOKEN not set).", status_code=503)
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            GUEST_COOKIE_NAME, _make_session_cookie(secret, GUEST_SCOPE),
            httponly=True, samesite="lax", secure=_is_hosted(), max_age=SESSION_TTL_SECONDS,
        )
        return response

    @mcp.custom_route("/dashboard/logout", methods=["GET"])
    async def logout(request: Request) -> Response:
        response = RedirectResponse(url="/dashboard/login", status_code=302)
        response.delete_cookie(COOKIE_NAME)
        response.delete_cookie(GUEST_COOKIE_NAME)
        return response

    # --- Overview ---

    @mcp.custom_route("/", methods=["GET"])
    async def overview_page(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        papers = db.fetch_all_papers()
        review = db.get_latest_literature_review()
        topic_count = len({p["topic_id"] for p in papers if p.get("topic_id") is not None})
        review_status = "Not yet generated"
        if review:
            review_status = (review.get("generated_at") or "")[:10] or "Draft"
        recent_papers = list(reversed(papers[-5:]))
        return HTMLResponse(_render(request, "overview.html",
            active="overview", paper_count=len(papers), topic_count=topic_count,
            review_status=review_status, recent_papers=recent_papers,
            error=request.query_params.get("error"), ok=request.query_params.get("ok"),
        ))

    # --- Papers ---

    @mcp.custom_route("/dashboard/papers", methods=["GET"])
    async def papers_page(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        q = (request.query_params.get("q") or "").strip()
        sort = request.query_params.get("sort") or "id"
        papers = db.fetch_all_papers()

        if q:
            needle = q.lower()
            def matches(p):
                haystack = " ".join([
                    p.get("title") or "", " ".join(p.get("authors") or []),
                    p.get("problem") or "", p.get("method") or "", p.get("result") or "",
                ]).lower()
                return needle in haystack
            papers = [p for p in papers if matches(p)]

        if sort == "title":
            papers.sort(key=lambda p: (p.get("title") or "").lower())
        elif sort == "published":
            papers.sort(key=lambda p: p.get("published") or date.min)
        elif sort == "topic":
            papers.sort(key=lambda p: p.get("topic_label") or "")
        else:
            papers.sort(key=lambda p: p["id"], reverse=True)

        return HTMLResponse(_render(request, "papers.html",
            active="papers", papers=papers, q=q, sort=sort,
            error=request.query_params.get("error"), ok=request.query_params.get("ok"),
        ))

    @mcp.custom_route("/dashboard/papers/{paper_id:int}/edit", methods=["GET"])
    async def paper_edit_page(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        paper_id = request.path_params["paper_id"]
        paper = db.get_paper(paper_id)
        if not paper:
            return _redirect("/dashboard/papers", error=f"No paper with id {paper_id}.")
        return HTMLResponse(_render(request, "paper_edit.html",
            active="papers", paper=paper,
            error=request.query_params.get("error"), ok=request.query_params.get("ok"),
        ))

    @mcp.custom_route("/dashboard/papers/{paper_id:int}/edit", methods=["POST"])
    async def paper_edit_submit(request: Request) -> Response:
        redirect = _require_session(request, owner_only=True)
        if redirect:
            return redirect
        paper_id = request.path_params["paper_id"]
        form = await request.form()
        title = (form.get("title") or "").strip()
        authors = [line.strip() for line in (form.get("authors") or "").splitlines() if line.strip()]
        published_raw = (form.get("published") or "").strip()
        problem = form.get("problem") or ""
        method = form.get("method") or ""
        result = form.get("result") or ""

        published = None
        if published_raw:
            try:
                published = date.fromisoformat(published_raw)
            except ValueError:
                existing = db.get_paper(paper_id) or {"id": paper_id, "topic_label": None}
                submitted = {**existing, "title": title, "authors": authors, "published": published_raw,
                             "problem": problem, "method": method, "result": result}
                return HTMLResponse(
                    _render(request, "paper_edit.html",
                        active="papers", paper=submitted,
                        error=f"Invalid date '{published_raw}' - expected YYYY-MM-DD.", ok=None,
                    ),
                    status_code=400,
                )

        try:
            db.update_paper(paper_id, {
                "title": title, "authors": authors, "published": published,
                "problem": problem, "method": method, "result": result,
            })
        except Exception as e:
            traceback.print_exc()
            return _redirect(f"/dashboard/papers/{paper_id}/edit", error=f"Update failed: {e}")
        return _redirect(f"/dashboard/papers/{paper_id}/edit", ok="Paper updated.")

    @mcp.custom_route("/dashboard/papers/{paper_id:int}/delete", methods=["POST"])
    async def paper_delete(request: Request) -> Response:
        redirect = _require_session(request, owner_only=True)
        if redirect:
            return redirect
        paper_id = request.path_params["paper_id"]
        try:
            db.delete_paper(paper_id)
        except Exception as e:
            traceback.print_exc()
            return _redirect(f"/dashboard/papers/{paper_id}/edit", error=f"Delete failed: {e}")
        return _redirect("/dashboard/papers", ok="Paper deleted.")

    # --- Topics ---

    @mcp.custom_route("/dashboard/topics", methods=["GET"])
    async def topics_page(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        papers = db.fetch_all_papers()
        groups: dict[int, dict] = {}
        for p in papers:
            topic_id = p.get("topic_id")
            if topic_id is None:
                continue
            g = groups.setdefault(topic_id, {
                "topic_id": topic_id,
                "topic_label": p.get("topic_label") or "(unlabeled)",
                "topic_keywords": p.get("topic_keywords") or "",
                "count": 0,
            })
            g["count"] += 1
        topics = sorted(groups.values(), key=lambda g: -g["count"])
        return HTMLResponse(_render(request, "topics.html",
            active="topics", topics=topics,
            error=request.query_params.get("error"), ok=request.query_params.get("ok"),
        ))

    @mcp.custom_route("/dashboard/topics/{topic_id:int}/rename", methods=["POST"])
    async def topic_rename(request: Request) -> Response:
        redirect = _require_session(request, owner_only=True)
        if redirect:
            return redirect
        topic_id = request.path_params["topic_id"]
        form = await request.form()
        label = (form.get("label") or "").strip()
        if not label:
            return _redirect("/dashboard/topics", error="Label cannot be empty.")
        try:
            db.rename_topic(topic_id, label)
        except Exception as e:
            traceback.print_exc()
            return _redirect("/dashboard/topics", error=f"Rename failed: {e}")
        return _redirect("/dashboard/topics", ok="Topic renamed.")

    @mcp.custom_route("/dashboard/topics/recompute", methods=["POST"])
    async def recompute_topics_route(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        try:
            result, limited = _run_llm_action(request, "topics", recompute_topics_fn, "/dashboard/topics")
            if limited:
                return limited
            if result.get("error"):
                return _redirect("/dashboard/topics", error=result["error"])
            if result.get("topic_labels_error") and _session_role(request) == "guest":
                return _redirect("/dashboard/topics", info="Topics recomputed, but the live AI labeling is paused right now.")
            if result.get("topic_labels_error"):
                return _redirect("/dashboard/topics", error=f"Topics computed, but labeling failed: {result['topic_labels_error']}")
        except Exception as e:
            traceback.print_exc()
            return _redirect("/dashboard/topics", error=f"Recompute topics failed: {e}")
        return _redirect("/dashboard/topics", ok="Topics recomputed.")

    # --- Review ---

    @mcp.custom_route("/dashboard/review", methods=["GET"])
    async def review_page(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        review = db.get_latest_literature_review()
        return HTMLResponse(_render(request, "review.html",
            active="review", review=review,
            error=request.query_params.get("error"), ok=request.query_params.get("ok"),
        ))

    @mcp.custom_route("/dashboard/review/save", methods=["POST"])
    async def review_save(request: Request) -> Response:
        redirect = _require_session(request, owner_only=True)
        if redirect:
            return redirect
        form = await request.form()
        content = form.get("content") or ""
        try:
            db.update_literature_review_content(content)
        except Exception as e:
            traceback.print_exc()
            return _redirect("/dashboard/review", error=f"Save failed: {e}")
        return _redirect("/dashboard/review", ok="Review saved.")

    @mcp.custom_route("/dashboard/review/regenerate", methods=["POST"])
    async def review_regenerate(request: Request) -> Response:
        redirect = _require_session(request)
        if redirect:
            return redirect
        try:
            _, limited = _run_llm_action(request, "review", generate_review_fn, "/dashboard/review")
            if limited:
                return limited
        except Exception as e:
            traceback.print_exc()
            return _redirect("/dashboard/review", error=f"Literature review failed: {e}")
        return _redirect("/dashboard/review", ok="Review regenerated.")

    # --- Chart image endpoints (shared by Overview) ---

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
