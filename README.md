# 🎓 ArXiv Research Assistant (MCP Server)

A Research Agent server built with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). Search ArXiv, extract structured findings from papers, build a bibliography, and discover insights (keyword trends, author networks, topic clusters) — all as tools an AI assistant can call directly. Runs either as a local server launched by your IDE, or hosted remotely.

## 🚀 Features

*   Automated Search: Query ArXiv for papers on any topic.
*   Intelligent Extraction: heuristic keyword-based extraction (free), or LLM-based extraction via Claude Haiku 4.5 (higher accuracy, small API cost) — of the core "Problem", "Method", and "Result" from abstracts.
*   Bibliography: saved to a Postgres database (dedupes automatically by paper URL).
*   Data Science Pipeline — all available as MCP tools, so an agent can trigger them directly:
    *   Visualize Trends: bar chart of dominant research methods.
    *   Topic Modeling: NMF (Non-Negative Matrix Factorization) discovers hidden research themes, then a single Claude Haiku call turns the raw keyword clusters into short readable labels.
    *   Knowledge Graph: interactive HTML network graph of author collaborations.

## Installation

### Prerequisites
*   Python 3.10+
*   A Postgres database — [Neon](https://neon.tech) has a free tier and is what this was built/tested against.
*   An [Anthropic API key](https://console.anthropic.com/) for the LLM-based tools (`extract_key_findings_llm`, and the topic-labeling step inside `discover_research_topics`). Not needed for the rest of the server.

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

4.  **Configure environment variables** — copy `.env.example` to `.env` and fill in `DATABASE_URL` (your Neon connection string) and `ANTHROPIC_API_KEY`. Leave `MCP_AUTH_TOKEN` unset for local use.

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

This same server can run as a remote MCP endpoint instead of a process your IDE launches:

1. Deploy this repo to Vercel (it auto-detects the Python entrypoint `index.py`).
2. Set `DATABASE_URL`, `ANTHROPIC_API_KEY`, and `MCP_AUTH_TOKEN` as Vercel environment variables. Generate the auth token once with:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. Point a remote-MCP-capable client at `https://<your-project>.vercel.app/mcp`, sending `Authorization: Bearer <MCP_AUTH_TOKEN>` on every request. **Without `MCP_AUTH_TOKEN` set, the deployed endpoint is wide open — anyone with the URL could call your tools and spend your Anthropic budget.** Setting it is what enables the auth check; there is no separate on/off switch.

## 💡 Usage

Everything below is available as an MCP tool an agent can call directly — no separate terminal step needed. Just ask your AI Assistant things like:

> "Find 5 papers on 'Reinforcement Learning from Human Feedback', extract their key findings, and save them to my bibliography."

> "Now visualize the keyword trends in my bibliography and tell me the dominant research topics."

### MCP Tools

*   **`search_arxiv(query, max_results)`** — Search ArXiv for papers.
*   **`extract_key_findings(abstract)`** — Free, heuristic Problem/Method/Result extraction.
*   **`extract_key_findings_llm(abstract)`** — Same extraction via Claude Haiku 4.5 — more accurate, small API cost.
*   **`save_to_bibliography(paper_metadata)`** — Upsert a paper (with its findings) into the database, keyed by its PDF URL.
*   **`visualize_keyword_trends()`** — Bar chart of common method keywords, returned as an inline image.
*   **`generate_author_network()`** — Interactive co-authorship graph, returned as a base64-encoded self-contained HTML file (decode and open it to view).
*   **`discover_research_topics(num_topics)`** — NMF topic modeling over the bibliography, plus Claude-generated readable labels for each topic.

### Running the analysis scripts standalone

Each analysis tool is also a runnable CLI script, if you'd rather generate insights from the terminal directly (writes its output to a local file, for convenience — the MCP tools above never touch disk):

```bash
python analyze_references.py     # -> method_keywords.png
python generate_network.py       # -> author_network.html
python topic_modeling.py         # updates topic assignments in the database
```

## 📂 Project Structure

- `research_server.py`: The core MCP server — defines every tool listed above.
- `index.py`: Vercel entrypoint — exposes the same server over Streamable HTTP.
- `db.py`: Postgres access (schema, upsert, fetch, topic updates).
- `auth.py`: Bearer-token gate for the hosted deployment.
- `llm.py`: Claude Haiku 4.5 calls (structured-output extraction + topic labeling).
- `analyze_references.py`: Keyword-frequency visualization (also the `visualize_keyword_trends` tool).
- `generate_network.py`: NetworkX/Pyvis co-authorship graph (also the `generate_author_network` tool).
- `topic_modeling.py`: Scikit-learn NMF topic modeling (also the `discover_research_topics` tool).
- `requirements.txt`: Python dependencies.

---
*Built with [mcp](https://pypi.org/project/mcp/), [arxiv](https://pypi.org/project/arxiv/), [anthropic](https://pypi.org/project/anthropic/), [pandas](https://pandas.pydata.org/), [scikit-learn](https://scikit-learn.org/), [networkx](https://networkx.org/), and [Neon Postgres](https://neon.tech).*
