import base64
import json
import os
import re
from datetime import date

import arxiv
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.transport_security import TransportSecuritySettings

import db
from analyze_references import analyze
from auth import StaticTokenVerifier
from generate_network import generate_graph
from llm import extract_findings_llm, label_topics
from topic_modeling import run_topic_modeling

# Initialize FastMCP server.
# stateless_http is always on - correct for both stdio (inert there) and a
# serverless HTTP deployment (no session affinity can be assumed across
# invocations). Auth is wired only when MCP_AUTH_TOKEN is set, so local dev
# needs no new env vars.
#
# MCP's built-in DNS-rebinding protection (transport_security) only allows
# Host/Origin headers matching a fixed allowlist, which defeats a real
# public deployment (Vercel's hostname, plus a different one per preview
# deploy). Disabled only when hosted - the bearer token above is the real
# access control here, not this browser-focused protection meant for
# locally-running dev servers.
_auth_token = os.environ.get("MCP_AUTH_TOKEN")
mcp = FastMCP(
    "ArXiv Research Assistant",
    stateless_http=True,
    token_verifier=StaticTokenVerifier() if _auth_token else None,
    auth=AuthSettings(issuer_url="https://arxiv-research-mcp.invalid", resource_server_url=None) if _auth_token else None,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False) if _auth_token else None,
)

@mcp.tool()
def search_arxiv(query: str, max_results: int = 5) -> str:
    """
    Search ArXiv for papers.

    Args:
        query: The search query.
        max_results: Maximum number of results to return (default 5).

    Returns:
        JSON string containing a list of papers with title, authors, published date, and abstract.
    """
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = []
        for result in client.results(search):
            paper_info = {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "published": result.published.strftime("%Y-%m-%d"),
                "pdf_url": result.pdf_url,
                "abstract": result.summary
            }
            results.append(paper_info)

        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": f"ArXiv search failed: {str(e)}"})

@mcp.tool()
def extract_key_findings(abstract: str) -> str:
    """
    Extract key findings (Problem, Method, Result) from an abstract using heuristic keyword matching.
    Free, no API cost. For higher-accuracy extraction, see extract_key_findings_llm.

    Args:
        abstract: The text of the paper abstract.

    Returns:
        JSON string with keys 'problem', 'method', 'result'.
    """
    # 1. Clean and Split into sentences
    text = abstract.replace("\n", " ")
    # Simple regex split by . or ? or ! followed by space or end of string
    sentences = re.split(r'(?<=[.?!])\s+', text)

    findings = {
        "problem": [],
        "method": [],
        "result": []
    }

    # 2. Keyword definitions
    keywords = {
        "problem": ["problem", "challenge", "issue", "limitat", "address", "motivation", "gap"],
        "method": ["method", "propose", "approach", "framework", "architecture", "algorithm", "technique", "use", "using"],
        "result": ["result", "show", "demonstrate", "find", "achieve", "perform", "improve", "accuracy", "state-of-the-art"]
    }

    # 3. Classify sentences
    for sent in sentences:
        sent_lower = sent.lower()

        # Simple scoring: count keyword matches for each category
        scores = {cat: 0 for cat in keywords}
        for cat, kw_list in keywords.items():
            for kw in kw_list:
                if kw in sent_lower:
                    scores[cat] += 1

        # Assign sentence to category with highest score (if score > 0)
        best_cat = None
        max_score = 0

        for cat, score in scores.items():
            if score > max_score:
                max_score = score
                best_cat = cat

        if best_cat:
            findings[best_cat].append(sent)

    # Join lists into single strings for better readability
    final_findings = {k: " ".join(v) if v else "Not explicitly found." for k, v in findings.items()}

    return json.dumps(final_findings, indent=2)

@mcp.tool()
def extract_key_findings_llm(abstract: str) -> str:
    """
    Extract key findings (Problem, Method, Result) from an abstract using Claude Haiku 4.5.
    More accurate than the free heuristic extract_key_findings, at a small per-call API cost.

    Args:
        abstract: The text of the paper abstract.

    Returns:
        JSON string with keys 'problem', 'method', 'result', or an 'error' message.
    """
    try:
        findings = extract_findings_llm(abstract)
        return findings.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"error": f"LLM extraction failed: {str(e)}"})

@mcp.tool()
def save_to_bibliography(paper_metadata: str) -> str:
    """
    Save a paper's metadata and key findings to the bibliography database.
    Saving the same paper (same pdf_url) again updates it instead of duplicating it.

    Args:
        paper_metadata: JSON string or dict. Should contain 'title', 'authors', 'published', 'pdf_url'.
                       Can optionally contain 'problem', 'method', 'result' from extract_key_findings.

    Returns:
        Success message.
    """
    if isinstance(paper_metadata, str):
        try:
            data = json.loads(paper_metadata)
        except json.JSONDecodeError:
            return "Error: paper_metadata must be a valid JSON string."
    else:
        data = paper_metadata

    published = data.get("published")
    if published:
        try:
            published = date.fromisoformat(published)
        except ValueError:
            published = None

    try:
        paper_id = db.upsert_paper({**data, "published": published})
        return f"Successfully saved '{data.get('title', '')}' (id={paper_id}) to the bibliography."
    except Exception as e:
        return f"Error saving to bibliography: {str(e)}"

@mcp.tool()
def visualize_keyword_trends() -> list:
    """
    Analyze the bibliography and generate a bar chart of the most common keywords in the
    saved 'method' descriptions, plus the most common 'problem' keywords.

    Returns:
        A JSON text block with 'papers_analyzed', 'method_keywords', 'problem_keywords' (or an
        'error' message if there's no bibliography yet), followed by the chart as an inline image.
    """
    result = analyze()
    png_bytes = result.pop("chart_png", None)
    blocks: list = [json.dumps(result, indent=2)]
    if png_bytes:
        blocks.append(Image(data=png_bytes, format="png"))
    return blocks

@mcp.tool()
def generate_author_network() -> str:
    """
    Build an interactive co-authorship network graph from the bibliography.

    Returns:
        JSON string with 'num_authors', 'num_collaborations', and 'html_base64' (the interactive
        graph as a base64-encoded, self-contained HTML file - decode and save it to view it), or
        an 'error' message if there's no bibliography yet.
    """
    result = generate_graph()
    html = result.pop("html", None)
    if html:
        result["html_base64"] = base64.b64encode(html.encode("utf-8")).decode("ascii")
    return json.dumps(result, indent=2)

@mcp.tool()
def discover_research_topics(num_topics: int = 5) -> str:
    """
    Run NMF topic modeling over the bibliography to automatically discover hidden research
    themes, and save the per-paper topic assignments back to the database.

    Args:
        num_topics: Number of topics to discover (default 5). Must be <= number of saved papers.

    Returns:
        JSON string with 'topic_summaries' (raw top TF-IDF keywords per topic), 'topic_labels'
        (short human-readable label per topic, from a single batched Claude Haiku call),
        'topic_distribution' (paper count per topic), or an 'error' message.
    """
    result = run_topic_modeling(num_topics=num_topics)
    if "error" not in result:
        try:
            result["topic_labels"] = label_topics(result["topic_summaries"])
        except Exception as e:
            result["topic_labels_error"] = str(e)
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
