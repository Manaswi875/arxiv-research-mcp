import os

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


def update_topics(paper_id: int, topic_id: int, topic_keywords: str, topic_label: str | None) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE papers SET topic_id = %s, topic_keywords = %s, topic_label = %s WHERE id = %s;",
            (topic_id, topic_keywords, topic_label, paper_id),
        )


if __name__ == "__main__":
    init_schema()
    print("Schema ready.")
