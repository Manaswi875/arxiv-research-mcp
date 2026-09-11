import base64
import json
import os
import re
from datetime import date

import arxiv
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.transport_security import TransportSecuritySettings
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

import dashboard
import db
from analyze_references import analyze
from generate_network import generate_graph
from llm import extract_findings_llm, label_topics
from llm import generate_literature_review as generate_literature_review_llm
from oauth_provider import MCP_SCOPE, SimpleOAuthProvider
from research_trends import analyze_trends
from topic_modeling import run_topic_modeling

# Initialize FastMCP server.
# stateless_http is always on - correct for both stdio (inert there) and a
# serverless HTTP deployment (no session affinity can be assumed across
# invocations). OAuth (dynamic client registration + a login form gated by
# MCP_AUTH_TOKEN) is wired only when MCP_SERVER_URL is set, so local stdio
# dev needs no new env vars. A plain static bearer token doesn't work here:
# Claude.ai's "Add custom connector" flow only speaks full OAuth for
# connectors that declare auth, so the provider below implements a minimal
# single-user authorization server instead (see oauth_provider.py).
#
# MCP's built-in DNS-rebinding protection (transport_security) only allows
# Host/Origin headers matching a fixed allowlist, which defeats a real
# public deployment (Vercel's hostname, plus a different one per preview
# deploy). Disabled only when hosted - the OAuth login above is the real
# access control here, not this browser-focused protection meant for
# locally-running dev servers.
_server_url = os.environ.get("MCP_SERVER_URL")
_oauth_provider = SimpleOAuthProvider(auth_callback_url=f"{_server_url}/login", server_url=_server_url) if _server_url else None
mcp = FastMCP(
    "ArXiv Research Assistant",
    stateless_http=True,
    auth_server_provider=_oauth_provider,
    auth=AuthSettings(
        issuer_url=_server_url,
        client_registration_options=ClientRegistrationOptions(
            enabled=True, valid_scopes=[MCP_SCOPE], default_scopes=[MCP_SCOPE]
        ),
        required_scopes=[MCP_SCOPE],
        resource_server_url=None,
    ) if _server_url else None,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False) if _server_url else None,
)

if _oauth_provider:
    @mcp.custom_route("/login", methods=["GET"])
    async def login_page_handler(request: Request) -> Response:
        state = request.query_params.get("state")
        if not state:
            raise HTTPException(400, "Missing state parameter")
        return await _oauth_provider.get_login_page(state)

    @mcp.custom_route("/login/callback", methods=["POST"])
    async def login_callback_handler(request: Request) -> Response:
        return await _oauth_provider.handle_login_callback(request)

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
def visualize_research_trends() -> list:
    """
    Analyze how the bibliography's research topics have shifted over time (papers per
    topic per year), using the topic labels from discover_research_topics.

    Returns:
        A JSON text block with 'papers_analyzed', 'years', and 'topics' (each with
        'topic_label' and 'counts_by_year') - or an 'error' message if there's no
        bibliography yet, or no saved paper has a publish date - followed by a stacked
        bar chart as an inline image.
    """
    result = analyze_trends()
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

def _recompute_topics(num_topics: int = 5) -> dict:
    """Shared by the discover_research_topics tool and the dashboard's "Recompute
    Topics" button - one code path, so the two surfaces can never drift apart."""
    result = run_topic_modeling(num_topics=num_topics)
    if "error" not in result:
        try:
            labels = label_topics(result["topic_summaries"])
            db.update_topic_labels_bulk({int(k): v for k, v in labels.items()})
            result["topic_labels"] = labels
        except Exception as e:
            result["topic_labels_error"] = str(e)
    return result

@mcp.tool()
def discover_research_topics(num_topics: int = 5) -> str:
    """
    Run NMF topic modeling over the bibliography to automatically discover hidden research
    themes, and save the per-paper topic assignments (including readable labels) back to
    the database.

    Args:
        num_topics: Number of topics to discover (default 5). Must be <= number of saved papers.

    Returns:
        JSON string with 'topic_summaries' (raw top TF-IDF keywords per topic), 'topic_labels'
        (short human-readable label per topic, from a single batched Claude Haiku call),
        'topic_distribution' (paper count per topic), or an 'error' message.
    """
    return json.dumps(_recompute_topics(num_topics), indent=2)


def _generate_and_save_review() -> str:
    """Shared by the generate_literature_review tool and the dashboard's button."""
    papers = db.fetch_all_papers()
    review = generate_literature_review_llm(papers)
    db.save_literature_review(review, len(papers))
    return review

@mcp.tool()
def generate_literature_review() -> str:
    """
    Synthesize the whole bibliography into one narrative literature review with numbered
    [n] citations (matching the paper's position in the bibliography) and a References
    section, via a single batched Claude Haiku call - not one call per paper.

    Returns:
        The generated review text, or a JSON string with an 'error' message.
    """
    try:
        return _generate_and_save_review()
    except Exception as e:
        return json.dumps({"error": f"Literature review generation failed: {str(e)}"})

dashboard.register_dashboard_routes(mcp, generate_review_fn=_generate_and_save_review, recompute_topics_fn=_recompute_topics)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
