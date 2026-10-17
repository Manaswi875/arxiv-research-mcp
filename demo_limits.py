"""Spend caps for public guest visitors of the dashboard ("Explore the demo").

Only guests are metered - the owner (signed in with MCP_AUTH_TOKEN) and MCP tool
calls (behind OAuth) are never limited here. Counters live in db's oauth_store
table keyed by UTC date, so they reset daily with no cron and no new table.

Costs are in "units", sized from claude-haiku-4-5 pricing: a topic-labeling call
is ~$0.001 (1 unit), a literature review is up to ~$0.045 (40 units). The global
cap of 50 units/day keeps worst-case spend around $1.50/month.
"""

from datetime import datetime, timezone

import anthropic

import db

GLOBAL_DAILY_UNITS = 50

ACTIONS = {
    # action: (unit cost, per-IP daily limit on number of calls)
    "topics": (1, 5),
    "review": (40, 1),
}


class LimitReached(Exception):
    pass


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def spend(action: str, ip: str) -> None:
    """Atomically charge one call against both the per-IP and global caps, or
    raise LimitReached (charging neither)."""
    cost, ip_limit = ACTIONS[action]
    day = datetime.now(timezone.utc).date().isoformat()
    # Raising inside the transaction rolls back the per-IP charge if the global one fails.
    with db.get_connection() as conn, conn.transaction():
        if not db.usage_try_increment(conn, f"{day}:ip:{ip}:{action}", 1, ip_limit):
            raise LimitReached("You've used today's free demo runs for this action.")
        if not db.usage_try_increment(conn, f"{day}:global", cost, GLOBAL_DAILY_UNITS):
            raise LimitReached("The daily demo limit has been reached for everyone.")


def is_out_of_credit(exc: Exception) -> bool:
    """True for API errors that mean the live demo can't run right now (no credit,
    provider-side rate limit, bad/missing key) - as opposed to a real bug."""
    if isinstance(exc, (anthropic.RateLimitError, anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return True
    return isinstance(exc, anthropic.BadRequestError) and "credit balance" in str(exc).lower()
