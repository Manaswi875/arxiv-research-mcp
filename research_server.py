import re
import csv
import json
import os
from typing import List, Dict, Any
import arxiv
from mcp.server.fastmcp import FastMCP

from paths import REFERENCES_CSV
from analyze_references import analyze
from generate_network import generate_graph
from topic_modeling import run_topic_modeling

# Initialize FastMCP server
mcp = FastMCP("ArXiv Research Assistant")

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
def save_to_bibliography(paper_metadata: str) -> str:
    """
    Save a paper's metadata and key findings to a local references.csv file.
    
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
        
    required_keys = ["title", "authors", "published", "pdf_url", "problem", "method", "result"]
    # Handle missing keys gracefully
    row = {k: str(data.get(k, "")) for k in required_keys}

    file_exists = os.path.isfile(REFERENCES_CSV)

    try:
        with open(REFERENCES_CSV, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=required_keys)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        return f"Successfully added '{row['title']}' to {REFERENCES_CSV}"
    except Exception as e:
        return f"Error saving to bibliography: {str(e)}"

@mcp.tool()
def visualize_keyword_trends() -> str:
    """
    Analyze the local bibliography (references.csv) and generate a bar chart of the most
    common keywords in the saved 'method' descriptions, plus the most common 'problem' keywords.

    Returns:
        JSON string with 'papers_analyzed', 'method_keywords', 'problem_keywords', and 'chart_path'
        (path to the saved PNG), or an 'error' message if there's no bibliography yet.
    """
    return json.dumps(analyze(), indent=2)

@mcp.tool()
def generate_author_network() -> str:
    """
    Build an interactive co-authorship network graph from the local bibliography
    (references.csv), saved as an HTML file.

    Returns:
        JSON string with 'num_authors', 'num_collaborations', and 'output_file' (path to the
        saved HTML graph), or an 'error' message if there's no bibliography yet.
    """
    return json.dumps(generate_graph(), indent=2)

@mcp.tool()
def discover_research_topics(num_topics: int = 5) -> str:
    """
    Run NMF topic modeling over the local bibliography (references.csv) to automatically
    discover hidden research themes, and save the per-paper topic assignments to
    references_with_topics.csv.

    Args:
        num_topics: Number of topics to discover (default 5). Must be <= number of saved papers.

    Returns:
        JSON string with 'topic_summaries' (top keywords per topic), 'topic_distribution'
        (paper count per topic), and 'output_file', or an 'error' message.
    """
    return json.dumps(run_topic_modeling(num_topics=num_topics), indent=2)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
