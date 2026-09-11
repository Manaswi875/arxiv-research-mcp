# 🎓 ArXiv Research Assistant (MCP Server)

An automated Research Agent server built with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). This tool helps Data Scientists and Researchers search ArXiv, analyze papers, and discover insights using Machine Learning—all directly from their IDE.

## 🚀 Features

*   Automated Search: Query ArXiv for papers on any topic.
*   Intelligent Extraction: Uses NLP heuristics to extract the core "Problem", "Method", and "Result" from abstracts.
*   Data Science Pipeline — all available as MCP tools, so an agent can trigger them directly:
    *   Saves findings to a structured dataset (`references.csv`).
    *   Visualize Trends: Generate charts of dominating research methods (`visualize_keyword_trends` tool / `analyze_references.py`).
    *   Topic Modeling: Uses NMF (Non-Negative Matrix Factorization) to automatically discover hidden research themes (`discover_research_topics` tool / `topic_modeling.py`).
    *   Knowledge Graph: Generates an interactive HTML network graph of author collaborations (`generate_author_network` tool / `generate_network.py`).

## Installation

### Prerequisites
*   Python 3.10+ (Tested on Python 3.14)

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

## ⚙️ Configuration

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
        "PYTHONPATH": "/absolute/path/to/your/arxiv-research-mcp"
      }
    }
  }
}
```
*Note: Replace `/absolute/path/to/your/arxiv-research-mcp/` with the actual full path on your machine.*

## 💡 Usage

Everything below is available as an MCP tool an agent can call directly — no separate terminal step needed. Just ask your AI Assistant things like:

> "Find 5 papers on 'Reinforcement Learning from Human Feedback', extract their key findings, and save them to my bibliography."

> "Now visualize the keyword trends in my bibliography and tell me the dominant research topics."

### MCP Tools

*   **`search_arxiv(query, max_results)`** — Search ArXiv for papers.
*   **`extract_key_findings(abstract)`** — Heuristically extract Problem/Method/Result from an abstract.
*   **`save_to_bibliography(paper_metadata)`** — Append a paper (with its findings) to `references.csv`.
*   **`visualize_keyword_trends()`** — Generate a bar chart of common method keywords; saves `method_keywords.png`.
*   **`generate_author_network()`** — Build an interactive co-authorship graph; saves `author_network.html`.
*   **`discover_research_topics(num_topics)`** — Run NMF topic modeling over the bibliography; saves `references_with_topics.csv`.

### Running the analysis scripts standalone

Each analysis tool is also a runnable CLI script, if you'd rather generate insights from the terminal directly:

```bash
python analyze_references.py     # -> method_keywords.png
python generate_network.py       # -> author_network.html
python topic_modeling.py         # -> references_with_topics.csv
```

## 📂 Project Structure

- `research_server.py`: The core MCP server — exposes all tools listed above.
- `paths.py`: Shared file paths, anchored to the project directory (not the caller's working directory).
- `analyze_references.py`: Keyword-frequency visualization (also the `visualize_keyword_trends` tool).
- `generate_network.py`: NetworkX/Pyvis co-authorship graph (also the `generate_author_network` tool).
- `topic_modeling.py`: Scikit-learn NMF topic modeling (also the `discover_research_topics` tool).
- `references.csv`: The dataset built by the agent.
- `requirements.txt`: Python dependencies.

---
*Built with [mcp](https://pypi.org/project/mcp/), [arxiv](https://pypi.org/project/arxiv/), [pandas](https://pandas.pydata.org/), [scikit-learn](https://scikit-learn.org/), and [networkx](https://networkx.org/).*
