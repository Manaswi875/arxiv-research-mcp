from itertools import combinations

import networkx as nx
from pyvis.network import Network

import db


def generate_graph() -> dict:
    rows = db.fetch_all_papers()
    if not rows:
        return {"error": "The bibliography is empty. Save some papers first with save_to_bibliography."}

    # Initialize Graph
    G = nx.Graph()

    # Process Authors - stored as real JSONB, so psycopg already hands back a Python list.
    for row in rows:
        authors = row.get("authors") or []

        for author in authors:
            if not G.has_node(author):
                G.add_node(author, title=author, group=1)

        if len(authors) > 1:
            for a1, a2 in combinations(authors, 2):
                if G.has_edge(a1, a2):
                    G[a1][a2]['weight'] += 1
                    G[a1][a2]['value'] += 1  # Pyvis uses 'value' for edge thickness
                else:
                    G.add_edge(a1, a2, weight=1, value=1)

    # Visualize - cdn_resources="in_line" keeps everything in one self-contained
    # string with zero disk I/O (no persistent filesystem once hosted).
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", cdn_resources="in_line")
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

    html = net.generate_html()

    return {
        "num_authors": G.number_of_nodes(),
        "num_collaborations": G.number_of_edges(),
        "html": html,
    }


if __name__ == "__main__":
    print("Loading bibliography...")
    result = generate_graph()
    if "error" in result:
        print(result["error"])
    else:
        print(f"Graph stats: {result['num_authors']} authors, {result['num_collaborations']} collaborations.")
        with open("author_network.html", "w", encoding="utf-8") as f:
            f.write(result["html"])
        print("✅ Created interactive graph: author_network.html")
