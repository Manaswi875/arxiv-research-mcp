# 🎓 ArXiv Research Assistant (MCP Server)

A Research Agent server built with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). Search ArXiv, extract structured findings from papers, build a bibliography, and discover insights (keyword trends, topic clusters, a research timeline, an AI-written literature review) — all as tools an AI assistant can call directly, plus a full multi-page web dashboard with editing built in. Runs either as a local server launched by your IDE, or hosted remotely.

## 🚀 Features

*   Automated Search: Query ArXiv for papers on any topic.
*   Intelligent Extraction: heuristic keyword-based extraction (free), or LLM-based extraction via Claude Haiku 4.5 (higher accuracy, small API cost) — of the core "Problem", "Method", and "Result" from abstracts.
*   Bibliography: saved to a Postgres database (dedupes automatically by paper URL), fully editable — update or delete any saved paper.
*   Data Science Pipeline — all available as MCP tools, so an agent can trigger them directly:
    *   Visualize Trends: bar chart of dominant research methods.
    *   Research Timeline: stacked bar chart of how your saved papers' topics have shifted year over year.
    *   Topic Modeling: NMF (Non-Negative Matrix Factorization) discovers hidden research themes, then a single Claude Haiku call turns the raw keyword clusters into short readable labels — labels can also be renamed manually at any time.
    *   Literature Review: one Claude Haiku call synthesizes the whole bibliography into a cohesive, numbered-citation narrative review — editable directly, or regenerated from scratch.
*   Web Dashboard: a real multi-page site (Overview / Papers / Topics / Review) at the deployed root URL, gated behind a login page — not open to the whole internet.

## Installation

### Prerequisites
*   Python 3.10+
*   A Postgres database — [Neon](https://neon.tech) has a free tier and is what this was built/tested against.
*   An [Anthropic API key](https://console.anthropic.com/) for the LLM-based tools (`extract_key_findings_llm`, the topic-labeling step inside `discover_research_topics`, and `generate_literature_review`). Not needed for the rest of the server.

### Setup
1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd arxiv-research-mcp
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables** — copy `.env.example` to `.env` and fill in `DATABASE_URL` (your Neon connection string) and `ANTHROPIC_API_KEY`. Leave `MCP_SERVER_URL`/`MCP_AUTH_TOKEN` unset for local use.

5.  **Initialize the database schema** (one-time):
    ```bash
    python db.py
    ```

## ⚙️ Configuration — Local (stdio)

Add the server to your IDE's MCP settings (e.g., `mcp-servers.json` in VS Code or Claude Desktop):

```json
{
  "mcpServers": {
    "research-assistant": {
      "command": "/absolute/path/to/your/arxiv-research-mcp/.venv/bin/python",
      "args": [
        "/absolute/path/to/your/arxiv-research-mcp/research_server.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/your/arxiv-research-mcp",
        "DATABASE_URL": "postgresql://...",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```
*Note: Replace the absolute paths with the actual full paths on your machine.*

## ☁️ Configuration — Remote (hosted on Vercel)

This same server can run as a remote MCP endpoint instead of a process your IDE launches. It authenticates over OAuth rather than a static bearer token — clients like Claude.ai's "Add custom connector" only speak full OAuth for connectors that declare auth, so this server implements a minimal single-user authorization server (dynamic client registration + a login form) rather than expecting the client to accept a pasted token directly.

1. Deploy this repo to Vercel (it auto-detects the Python entrypoint `index.py`).
2. Set these Vercel environment variables:
   - `DATABASE_URL`, `ANTHROPIC_API_KEY` (same as local)
   - `MCP_SERVER_URL` — the public URL this deployment is reachable at, e.g. `https://<your-project>.vercel.app`
   - `MCP_AUTH_TOKEN` — the password you'll type into the login form during setup (not something you paste into the client). Generate one with:
     ```bash
     python -c "import secrets; print(secrets.token_urlsafe(32))"
     ```
3. In your MCP client (e.g. Claude.ai → Settings → Connectors → Add custom connector), enter the server URL as `https://<your-project>.vercel.app/mcp`. The client will register itself and redirect you to a login page hosted by this server — enter the `MCP_AUTH_TOKEN` there to authorize it.

**OAuth (and with it, the login gate) only activates when `MCP_SERVER_URL` is set.** Leaving it unset — the local-dev default — means the deployed endpoint would be wide open, letting anyone who finds the URL call your tools and spend your Anthropic budget. Set both `MCP_SERVER_URL` and `MCP_AUTH_TOKEN` together for a real hosted deployment.

## 💡 Usage

Everything below is available as an MCP tool an agent can call directly — no separate terminal step needed. Just ask your AI Assistant things like:

> "Find 5 papers on 'Reinforcement Learning from Human Feedback', extract their key findings, and save them to my bibliography."

> "Now visualize the keyword trends in my bibliography, tell me the dominant research topics, and write me a literature review."

### MCP Tools

*   **`search_arxiv(query, max_results)`** — Search ArXiv for papers.
*   **`extract_key_findings(abstract)`** — Free, heuristic Problem/Method/Result extraction.
*   **`extract_key_findings_llm(abstract)`** — Same extraction via Claude Haiku 4.5 — more accurate, small API cost.
*   **`save_to_bibliography(paper_metadata)`** — Upsert a paper (with its findings) into the database, keyed by its PDF URL.
*   **`update_paper(paper_id, ...)`** — Edit any field of a saved paper (title, authors, published, problem, method, result). Fields left unset are unchanged.
*   **`delete_paper(paper_id)`** — Permanently remove a paper from the bibliography.
*   **`visualize_keyword_trends()`** — Bar chart of common method keywords, returned as an inline image.
*   **`visualize_research_trends()`** — Stacked bar chart of papers per topic per year, returned as an inline image.
*   **`discover_research_topics(num_topics)`** — NMF topic modeling over the bibliography, plus Claude-generated readable labels for each topic.
*   **`rename_topic(topic_id, label)`** — Manually rename a topic's label; applies to every paper sharing that topic, no recompute needed.
*   **`generate_literature_review()`** — Synthesizes the whole bibliography into one narrative review with numbered `[n]` citations, via a single Claude Haiku call.
*   **`update_literature_review(content)`** — Manually overwrite the saved review's text without regenerating it.

### Web Dashboard

Once deployed (or run locally), visit the server's root URL in a browser — it's gated behind a login form using the same `MCP_AUTH_TOKEN` as the OAuth setup.

- **Overview** (`/`) — stat tiles, both charts, a recently-saved papers preview.
- **Papers** (`/dashboard/papers`) — the full bibliography with search/sort, a Problem preview per row, and Edit/Delete actions. Each paper's edit page (`/dashboard/papers/{id}/edit`) exposes every field, including the full Problem/Method/Result text.
- **Topics** (`/dashboard/topics`) — every discovered topic with its raw NMF keywords and paper count, an inline rename form per topic, and a Recompute Topics button.
- **Review** (`/dashboard/review`) — the literature review in an editable textarea, with Save and Regenerate (regenerating warns first if you have unsaved manual edits).

### Running the analysis scripts standalone

Each analysis tool is also a runnable CLI script, if you'd rather generate insights from the terminal directly (writes its output to a local file, for convenience — the MCP tools above never touch disk):

```bash
python analyze_references.py     # -> method_keywords.png
python research_trends.py        # -> research_trends.png
python topic_modeling.py         # updates topic assignments in the database
```

## 📂 Project Structure

- `research_server.py`: The core MCP server — defines every tool listed above.
- `index.py`: Vercel entrypoint — exposes the same server over Streamable HTTP.
- `db.py`: Postgres access (schema, paper CRUD, topic updates, literature review cache).
- `oauth_provider.py`: Minimal single-user OAuth authorization server for the hosted deployment (dynamic client registration + a login form gated by `MCP_AUTH_TOKEN`).
- `dashboard.py` / `dashboard_templates.py`: The web dashboard's routes/CRUD logic and its Jinja2 templates, with their own login-cookie gate (also keyed by `MCP_AUTH_TOKEN`, separate from the OAuth flow above).
- `llm.py`: Claude Haiku 4.5 calls (structured-output extraction, topic labeling, literature review generation).
- `chart_style.py`: Shared matplotlib styling so every chart looks consistent.
- `analyze_references.py`: Keyword-frequency visualization (also the `visualize_keyword_trends` tool).
- `research_trends.py`: Topic-over-time analysis (also the `visualize_research_trends` tool).
- `topic_modeling.py`: Scikit-learn NMF topic modeling (also the `discover_research_topics` tool).
- `requirements.txt`: Python dependencies.

---
*Built with [mcp](https://pypi.org/project/mcp/), [arxiv](https://pypi.org/project/arxiv/), [anthropic](https://pypi.org/project/anthropic/), [pandas](https://pandas.pydata.org/), [scikit-learn](https://scikit-learn.org/), [Jinja2](https://jinja.palletsprojects.com/), and [Neon Postgres](https://neon.tech).*
