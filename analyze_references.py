import os
import re
from collections import Counter

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; required when imported into a long-running MCP server
import matplotlib.pyplot as plt
import pandas as pd

from paths import REFERENCES_CSV, METHOD_KEYWORDS_PNG


def analyze() -> dict:
    if not os.path.isfile(REFERENCES_CSV):
        return {"error": f"{REFERENCES_CSV} not found. Save some papers first with save_to_bibliography."}

    df = pd.read_csv(REFERENCES_CSV)
    if df.empty:
        return {"error": "references.csv is empty. Save some papers first."}

    def get_common_words(text_series, top_n=8):
        text = " ".join(text_series.dropna().astype(str).tolist())
        words = re.findall(r'\w+', text.lower())
        stopwords = set(['the', 'a', 'an', 'in', 'of', 'to', 'and', 'for', 'with', 'on', 'is', 'that', 'by', 'this', 'we', 'are', 'from', 'as', 'method', 'problem', 'result', 'not', 'explicitly', 'found', 'paper', 'models', 'model', 'based', 'using'])
        filtered = [w for w in words if w not in stopwords and len(w) > 3]
        return Counter(filtered).most_common(top_n)

    method_keywords = get_common_words(df['method']) if 'method' in df.columns else []
    problem_keywords = get_common_words(df['problem']) if 'problem' in df.columns else []

    chart_path = None
    if method_keywords:
        words, counts = zip(*method_keywords)

        plt.figure(figsize=(10, 6))
        plt.bar(words, counts, color='skyblue')
        plt.title('Top Method Keywords in Bibliography')
        plt.xlabel('Keyword')
        plt.ylabel('Frequency')
        plt.xticks(rotation=45)
        plt.tight_layout()

        plt.savefig(METHOD_KEYWORDS_PNG)
        plt.close()
        chart_path = METHOD_KEYWORDS_PNG

    return {
        "papers_analyzed": len(df),
        "method_keywords": method_keywords,
        "problem_keywords": problem_keywords,
        "chart_path": chart_path,
    }


if __name__ == "__main__":
    print("Loading references.csv...")
    result = analyze()
    if "error" in result:
        print(result["error"])
    else:
        print(f"Loaded {result['papers_analyzed']} papers.")
        if result["chart_path"]:
            print(f"\n✅ Created chart: {os.path.abspath(result['chart_path'])}")
        if result["problem_keywords"]:
            print("\nTop Problem Keywords:", result["problem_keywords"])
