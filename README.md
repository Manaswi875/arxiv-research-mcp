# 🎓 ArXiv Research Assistant (MCP Server)

An automated Research Agent server built with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). This tool helps Data Scientists and Researchers search ArXiv, analyze papers, and discover insights using Machine Learning—all directly from their IDE.

## 🚀 Features

*   automated Search: Query ArXiv for papers on any topic.
*   Intelligent Extraction: Uses NLP heuristics to extract the core "Problem", "Method", and "Result" from abstracts.
*   Data Science Pipeline:
    *   Saves findings to a structured dataset (`references.csv`).
    *   Visualize Trends: Generate charts of dominating research methods (`analyze_references.py`).
    *   Topic Modeling: Uses NMF (Non-Negative Matrix Factorization) to automatically discover hidden research themes (`topic_modeling.py`).
*   Knowledge Graph: Generates an interactive HTML network graph of author collaborations (`generate_network.py`).

## Installation

### Prerequisites
*   Python 3.10+ (Tested on Python 3.14)

### Setup
1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd mcp-project
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
      "command": "/absolute/path/to/your/mcp-project/.venv/bin/python",
      "args": [
        "/absolute/path/to/your/mcp-project/research_server.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/your/mcp-project"
      }
    }
  }
}
```
*Note: Replace `/absolute/path/to/your/mcp-project/` with the actual full path on your machine.*

## 💡 Usage

### 1. The MCP Agent
Once configured, you can ask your AI Assistant commands like:
> "Find 5 papers on 'Reinforcement Learning from Human Feedback', extract their key findings, and save them to my bibliography."

### 2. Analysis Tools
Run these scripts to generate insights from your collected `references.csv`:

*   **Visualize Keyword Trends**:
    ```bash
    python analyze_references.py
    ```
    *Generates `method_keywords.png`.*

*   **View Author Network**:
    ```bash
    python generate_network.py
    ```
    *Generates `author_network.html` (interactive).*

*   **Discover Hidden Topics**:
    ```bash
    python topic_modeling.py
    ```
    *Generates `references_with_topics.csv` with ML-assigned topic clusters.*

## 📂 Project Structure

- `research_server.py`: The core MCP server logic.
- `analyze_references.py`: Visualization script for keyword frequencies.
- `generate_network.py`: NetworkX/Pyvis script for knowledge graphs.
- `topic_modeling.py`: Scikit-learn script for NMF topic modeling.
- `references.csv`: The dataset built by the agent.
- `requirements.txt`: Python dependencies.

---
*Built with [mcp](https://pypi.org/project/mcp/), [arxiv](https://pypi.org/project/arxiv/), [pandas](https://pandas.pydata.org/), [scikit-learn](https://scikit-learn.org/), and [networkx](https://networkx.org/).*
# arxiv-research-mcp
# arxiv-research-mcp
