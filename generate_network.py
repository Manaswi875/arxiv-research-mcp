import ast
import os
from itertools import combinations

import networkx as nx
import pandas as pd
from pyvis.network import Network

from paths import REFERENCES_CSV, AUTHOR_NETWORK_HTML


def generate_graph() -> dict:
    if not os.path.isfile(REFERENCES_CSV):
        return {"error": f"{REFERENCES_CSV} not found. Save some papers first with save_to_bibliography."}

    df = pd.read_csv(REFERENCES_CSV)
    if df.empty:
        return {"error": "references.csv is empty. Save some papers first."}

    # Initialize Graph
    G = nx.Graph()

    # Process Authors
    for _, row in df.iterrows():
        try:
            # Authors are stored as string representation of list "['Author A', 'Author B']"
            # ast.literal_eval is safer than eval
            authors = ast.literal_eval(row['authors'])

            # Add nodes
            for author in authors:
                if not G.has_node(author):
                    G.add_node(author, title=author, group=1)

            # Add edges (co-authorship)
            if len(authors) > 1:
                for a1, a2 in combinations(authors, 2):
                    if G.has_edge(a1, a2):
                        G[a1][a2]['weight'] += 1
                        G[a1][a2]['value'] += 1  # Pyvis uses 'value' for edge thickness
                    else:
                        G.add_edge(a1, a2, weight=1, value=1)

        except (ValueError, SyntaxError):
            # Handle cases where author string might be malformed
            continue

    # Visualize
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)

    # Set physics layout suitable for large graphs
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=150,
        spring_strength=0.001,
        damping=0.09,
        overlap=0
    )

    net.save_graph(AUTHOR_NETWORK_HTML)

    return {
        "num_authors": G.number_of_nodes(),
        "num_collaborations": G.number_of_edges(),
        "output_file": AUTHOR_NETWORK_HTML,
    }


if __name__ == "__main__":
    print("Loading references.csv...")
    result = generate_graph()
    if "error" in result:
        print(result["error"])
    else:
        print(f"Graph stats: {result['num_authors']} authors, {result['num_collaborations']} collaborations.")
        print(f"✅ Created interactive graph: {os.path.abspath(result['output_file'])}")
