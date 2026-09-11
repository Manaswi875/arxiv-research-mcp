import io
import re
from collections import Counter

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; required when imported into a long-running MCP server
import matplotlib.pyplot as plt
import pandas as pd

import db
from chart_style import ACCENT, apply_style

apply_style()


def analyze() -> dict:
    rows = db.fetch_all_papers()
    if not rows:
        return {"error": "The bibliography is empty. Save some papers first with save_to_bibliography."}

    df = pd.DataFrame(rows)

    def get_common_words(text_series, top_n=8):
        text = " ".join(text_series.dropna().astype(str).tolist())
        words = re.findall(r'\w+', text.lower())
        stopwords = set(['the', 'a', 'an', 'in', 'of', 'to', 'and', 'for', 'with', 'on', 'is', 'that', 'by', 'this', 'we', 'are', 'from', 'as', 'method', 'problem', 'result', 'not', 'explicitly', 'found', 'paper', 'models', 'model', 'based', 'using'])
        filtered = [w for w in words if w not in stopwords and len(w) > 3]
        return Counter(filtered).most_common(top_n)

    method_keywords = get_common_words(df['method']) if 'method' in df.columns else []
    problem_keywords = get_common_words(df['problem']) if 'problem' in df.columns else []

    chart_png = None
    if method_keywords:
        words, counts = zip(*method_keywords)

        plt.figure(figsize=(10, 6))
        bars = plt.bar(words, counts, color=ACCENT, width=0.6)
        for bar, count in zip(bars, counts):
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                      str(count), ha="center", va="bottom", fontsize=9, color="#52514e")
        plt.title('Top Method Keywords in Bibliography', fontsize=13, fontweight="bold")
        plt.xlabel('Keyword')
        plt.ylabel('Frequency')
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        chart_png = buf.getvalue()

    return {
        "papers_analyzed": len(df),
        "method_keywords": method_keywords,
        "problem_keywords": problem_keywords,
        "chart_png": chart_png,
    }


if __name__ == "__main__":
    print("Loading bibliography...")
    result = analyze()
    if "error" in result:
        print(result["error"])
    else:
        print(f"Loaded {result['papers_analyzed']} papers.")
        if result["chart_png"]:
            with open("method_keywords.png", "wb") as f:
                f.write(result["chart_png"])
            print("\n✅ Created chart: method_keywords.png")
        if result["problem_keywords"]:
            print("\nTop Problem Keywords:", result["problem_keywords"])
