import re
import csv
import json
import os
from typing import List, Dict, Any
import arxiv
import pandas as pd
from mcp.server.fastmcp import FastMCP

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
    
    # CSV file path
    file_path = "references.csv"
    file_exists = os.path.isfile(file_path)
    
    try:
        with open(file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=required_keys)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
            
        return f"Successfully added '{row['title']}' to {file_path}"
    except Exception as e:
        return f"Error saving to bibliography: {str(e)}"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
