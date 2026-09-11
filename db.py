import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS papers (
    id SERIAL PRIMARY KEY,
    pdf_url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    authors JSONB NOT NULL DEFAULT '[]',
    published DATE,
    problem TEXT,
    method TEXT,
    result TEXT,
    topic_id INTEGER,
    topic_keywords TEXT,
    topic_label TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Generic key-value store for OAuth state (registered clients, in-flight
-- authorize state, issued codes/tokens). Needs to be a real table, not an
-- in-memory dict, since a serverless invocation can't assume any previous
-- state survived in process memory.
CREATE TABLE IF NOT EXISTS oauth_store (
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (kind, key)
);
"""

UPSERT_SQL = """
INSERT INTO papers (pdf_url, title, authors, published, problem, method, result)
VALUES (%(pdf_url)s, %(title)s, %(authors)s, %(published)s, %(problem)s, %(method)s, %(result)s)
ON CONFLICT (pdf_url) DO UPDATE SET
    title = EXCLUDED.title,
    authors = EXCLUDED.authors,
    published = EXCLUDED.published,
    problem = EXCLUDED.problem,
    method = EXCLUDED.method,
    result = EXCLUDED.result
RETURNING id;
"""


def get_connection() -> psycopg.Connection:
    """One connection per call - never a module-level pool.

    Vercel Functions don't guarantee a shared process/thread across
    invocations, so a persistent pool object is a correctness risk here
    for no real benefit at this traffic level (single-user tool).
    """
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, autocommit=True)


def init_schema() -> None:
    with get_connection() as conn:
        conn.execute(SCHEMA_DDL)


def upsert_paper(data: dict) -> int:
    row = {
        "pdf_url": data.get("pdf_url", ""),
        "title": data.get("title", ""),
        "authors": Jsonb(data.get("authors", [])),
        "published": data.get("published") or None,
        "problem": data.get("problem", ""),
        "method": data.get("method", ""),
        "result": data.get("result", ""),
    }
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(UPSERT_SQL, row)
        return cur.fetchone()["id"]


def fetch_all_papers() -> list[dict]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM papers ORDER BY id;")
        return cur.fetchall()


def get_paper(paper_id: int) -> dict | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM papers WHERE id = %s;", (paper_id,))
        return cur.fetchone()


def update_paper(paper_id: int, data: dict) -> None:
    """Full update of the 6 editable fields. `authors` must be a plain list -
    wrapped in Jsonb here, same trap as upsert_paper (a bare list misadapts to
    a Postgres array literal, not JSON)."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE papers SET title = %s, authors = %s, published = %s,
                problem = %s, method = %s, result = %s
            WHERE id = %s;
            """,
            (
                data["title"], Jsonb(data["authors"]), data["published"],
                data["problem"], data["method"], data["result"], paper_id,
            ),
        )


def delete_paper(paper_id: int) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM papers WHERE id = %s;", (paper_id,))


def update_topics(paper_id: int, topic_id: int, topic_keywords: str, topic_label: str | None) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE papers SET topic_id = %s, topic_keywords = %s, topic_label = %s WHERE id = %s;",
            (topic_id, topic_keywords, topic_label, paper_id),
        )


def update_topic_labels_bulk(labels: dict[int, str]) -> None:
    """Persist the human-readable label for each topic_id (labels is topic_id -> label)."""
    with get_connection() as conn, conn.cursor() as cur:
        for topic_id, label in labels.items():
            cur.execute(
                "UPDATE papers SET topic_label = %s WHERE topic_id = %s;",
                (label, topic_id),
            )


def rename_topic(topic_id: int, label: str) -> None:
    """Renaming a topic is just re-applying a label to every paper sharing that
    topic_id - no new SQL needed beyond the existing bulk-label updater."""
    update_topic_labels_bulk({topic_id: label})


def save_literature_review(content: str, paper_count: int) -> None:
    """Called on a fresh LLM-generated review - always clears the 'edited' flag,
    since a regenerate always overwrites any manual edits from before."""
    oauth_set(
        "literature_review",
        "latest",
        {
            "content": content,
            "paper_count": paper_count,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "edited": False,
            "edited_at": None,
        },
    )


def update_literature_review_content(content: str) -> None:
    """Called on a manual dashboard/tool edit - keeps generated_at/paper_count
    from the last real generation (or None/0 if none has ever run), marks edited=True."""
    existing = get_latest_literature_review() or {"paper_count": len(fetch_all_papers()), "generated_at": None}
    oauth_set(
        "literature_review",
        "latest",
        {
            "content": content,
            "paper_count": existing.get("paper_count", 0),
            "generated_at": existing.get("generated_at"),
            "edited": True,
            "edited_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def get_latest_literature_review() -> dict | None:
    return oauth_get("literature_review", "latest")


def oauth_set(kind: str, key: str, value: dict, ttl_seconds: int | None = None) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        if ttl_seconds is not None:
            cur.execute(
                """
                INSERT INTO oauth_store (kind, key, value, expires_at)
                VALUES (%s, %s, %s, now() + (%s * interval '1 second'))
                ON CONFLICT (kind, key) DO UPDATE SET value = EXCLUDED.value, expires_at = EXCLUDED.expires_at;
                """,
                (kind, key, Jsonb(value), ttl_seconds),
            )
        else:
            cur.execute(
                """
                INSERT INTO oauth_store (kind, key, value, expires_at)
                VALUES (%s, %s, %s, NULL)
                ON CONFLICT (kind, key) DO UPDATE SET value = EXCLUDED.value, expires_at = NULL;
                """,
                (kind, key, Jsonb(value)),
            )


def oauth_get(kind: str, key: str) -> dict | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT value FROM oauth_store WHERE kind = %s AND key = %s AND (expires_at IS NULL OR expires_at > now());",
            (kind, key),
        )
        row = cur.fetchone()
        return row["value"] if row else None


def oauth_delete(kind: str, key: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM oauth_store WHERE kind = %s AND key = %s;", (kind, key))


if __name__ == "__main__":
    init_schema()
    print("Schema ready.")
