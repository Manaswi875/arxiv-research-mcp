import json
import os
import time
from research_server import search_arxiv, extract_key_findings, save_to_bibliography

def run_tests():
    print("=== Populating Bibliography ===")
    
    # Topics to search
    topics = [
        "large language models", 
        "prompt engineering", 
        "chain of thought",
        "reinforcement learning from human feedback",
        "diffusion models",
        "vision transformers",
        "federated learning",
        "retrieval augmented generation"
    ]
    
    if os.path.exists("references.csv"):
        print("Existing references found.")
    
    for topic in topics:
        print(f"\nSearching for: {topic}...")
        results_json = search_arxiv(topic, max_results=20)
        results = json.loads(results_json)
        
        for paper in results:
            print(f"  Processing: {paper['title'][:50]}...")
            
            # Extract
            findings_json = extract_key_findings(paper['abstract'])
            findings = json.loads(findings_json)
            paper.update(findings)
            
            # Save
            save_to_bibliography(json.dumps(paper))
            time.sleep(0.5) # Be nice to APIs

if __name__ == "__main__":
    run_tests()
