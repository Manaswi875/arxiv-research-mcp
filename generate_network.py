import pandas as pd
import networkx as nx
from pyvis.network import Network
import ast
from itertools import combinations
import os

def generate_graph():
    print("Loading references.csv...")
    try:
        df = pd.read_csv("references.csv")
    except FileNotFoundError:
        print("references.csv not found.")
        return

    print(f"Processing {len(df)} papers...")
    
    # Initialize Graph
    G = nx.Graph()
    
    # Process Authors
    for index, row in df.iterrows():
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
                        G[a1][a2]['value'] += 1 # Pyvis uses 'value' for edge thickness
                    else:
                        G.add_edge(a1, a2, weight=1, value=1)
                        
        except (ValueError, SyntaxError) as e:
            # Handle cases where author string might be malformed
            continue

    print(f"Graph stats: {G.number_of_nodes()} authors, {G.number_of_edges()} collaborations.")
    
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
    
    output_file = "author_network.html"
    net.save_graph(output_file)
    print(f"✅ Created interactive graph: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    generate_graph()
