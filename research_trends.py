import io

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; required when imported into a long-running MCP server
import matplotlib.pyplot as plt
import pandas as pd

import db
from chart_style import OTHER_COLOR, PALETTE, apply_style

apply_style()


def analyze_trends() -> dict:
    rows = db.fetch_all_papers()
    if not rows:
        return {"error": "The bibliography is empty. Save some papers first with save_to_bibliography."}

    df = pd.DataFrame(rows)
    df = df[df["published"].notna()].copy()
    if df.empty:
        return {"error": "No saved papers have a 'published' date, so a timeline can't be built."}

    df["year"] = pd.to_datetime(df["published"]).dt.year.astype(str)
    df["topic_label"] = df["topic_label"].fillna(df["topic_keywords"]).fillna("Uncategorized")

    pivot = df.pivot_table(index="year", columns="topic_label", values="id", aggfunc="count", fill_value=0)
    pivot = pivot.sort_index()

    # Fold any topic beyond the palette's size into a single gray "Other" bucket,
    # so a growing/renamed set of topics over time can never outrun the palette.
    if len(pivot.columns) > len(PALETTE):
        totals = pivot.sum().sort_values(ascending=False)
        keep = totals.index[: len(PALETTE)]
        drop = totals.index[len(PALETTE):]
        pivot["Other"] = pivot[drop].sum(axis=1)
        pivot = pivot[list(keep) + ["Other"]]

    chart_png = None
    if not pivot.empty:
        plt.figure(figsize=(10, 6))
        bottom = None
        for i, topic in enumerate(pivot.columns):
            color = OTHER_COLOR if topic == "Other" else PALETTE[i % len(PALETTE)]
            plt.bar(pivot.index, pivot[topic], bottom=bottom, label=topic,
                     color=color, edgecolor="#ffffff", linewidth=1.5)
            bottom = pivot[topic] if bottom is None else bottom + pivot[topic]
        plt.title("Research Topics Over Time", fontsize=13, fontweight="bold")
        plt.xlabel("Year")
        plt.ylabel("Papers")
        plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=9, frameon=False, labelcolor="#0b0b0b")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close()
        chart_png = buf.getvalue()

    return {
        "papers_analyzed": len(df),
        "years": pivot.index.tolist(),
        "topics": [
            {"topic_label": topic, "counts_by_year": pivot[topic].tolist()}
            for topic in pivot.columns
        ],
        "chart_png": chart_png,
    }


if __name__ == "__main__":
    print("Loading bibliography...")
    result = analyze_trends()
    if "error" in result:
        print(result["error"])
    else:
        print(f"Analyzed {result['papers_analyzed']} papers across years: {result['years']}")
        for topic in result["topics"]:
            print(f"  {topic['topic_label']}: {topic['counts_by_year']}")
        if result["chart_png"]:
            with open("research_trends.png", "wb") as f:
                f.write(result["chart_png"])
            print("\n✅ Created chart: research_trends.png")
