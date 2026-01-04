import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import re
import os

def analyze():
    print("Loading references.csv...")
    try:
        df = pd.read_csv("references.csv")
    except FileNotFoundError:
        print("references.csv not found.")
        return

    print(f"Loaded {len(df)} papers.")
    
    # Keyword Analysis
    def get_common_words(text_series, top_n=8):
        text = " ".join(text_series.dropna().astype(str).tolist())
        words = re.findall(r'\w+', text.lower())
        stopwords = set(['the', 'a', 'an', 'in', 'of', 'to', 'and', 'for', 'with', 'on', 'is', 'that', 'by', 'this', 'we', 'are', 'from', 'as', 'method', 'problem', 'result', 'not', 'explicitly', 'found', 'paper', 'models', 'model', 'based', 'using'])
        filtered = [w for w in words if w not in stopwords and len(w) > 3]
        return Counter(filtered).most_common(top_n)

    method_keywords = get_common_words(df['method']) if 'method' in df.columns else []
    problem_keywords = get_common_words(df['problem']) if 'problem' in df.columns else []

    # Visualization
    if method_keywords:
        words, counts = zip(*method_keywords)
        
        plt.figure(figsize=(10, 6))
        plt.bar(words, counts, color='skyblue')
        plt.title('Top Method Keyswords in Bibliography')
        plt.xlabel('Keyword')
        plt.ylabel('Frequency')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_file = "method_keywords.png"
        plt.savefig(output_file)
        print(f"\n✅ Created chart: {os.path.abspath(output_file)}")
    
    if problem_keywords:
        print("\nTop Problem Keywords:", problem_keywords)

if __name__ == "__main__":
    analyze()
