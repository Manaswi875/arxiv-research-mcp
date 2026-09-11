import os

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from paths import REFERENCES_CSV, REFERENCES_WITH_TOPICS_CSV


def run_topic_modeling(num_topics: int = 5) -> dict:
    if not os.path.isfile(REFERENCES_CSV):
        return {"error": f"{REFERENCES_CSV} not found. Save some papers first with save_to_bibliography."}

    df = pd.read_csv(REFERENCES_CSV)
    if df.empty:
        return {"error": "references.csv is empty. Save some papers first."}

    if len(df) < num_topics:
        return {"error": f"Need at least {num_topics} papers to discover {num_topics} topics; only have {len(df)}. Save more papers or lower num_topics."}

    # 1. Feature Engineering
    # Combine relevant text fields to give the model more signal
    df['combined_text'] = (
        df['title'].fillna('') + " " +
        df['problem'].fillna('') + " " +
        df['method'].fillna('') + " " +
        df['result'].fillna('')
    )

    # 2. Vectorization (TF-IDF)
    # Ignore terms that appear in >95% of docs (max_df) or <2 docs (min_df)
    tfidf_vectorizer = TfidfVectorizer(
        max_df=0.95,
        min_df=2,
        stop_words='english'
    )
    tfidf = tfidf_vectorizer.fit_transform(df['combined_text'])

    # 3. NMF Model (Non-Negative Matrix Factorization)
    nmf_model = NMF(
        n_components=num_topics,
        random_state=42,
        init='nndsvd'  # Good for sparseness
    )
    nmf_features = nmf_model.fit_transform(tfidf)

    # 4. Build Topic Summaries
    feature_names = tfidf_vectorizer.get_feature_names_out()

    topic_summaries = {}
    for topic_idx, topic in enumerate(nmf_model.components_):
        # Get top 10 words for this topic
        top_indices = topic.argsort()[:-11:-1]
        top_words = [feature_names[i] for i in top_indices]
        topic_summaries[topic_idx] = ", ".join(top_words)

    # 5. Assign Dominant Topic to Papers
    dominant_topic_indices = np.argmax(nmf_features, axis=1)

    df['Topic_ID'] = dominant_topic_indices
    df['Topic_Keywords'] = df['Topic_ID'].map(topic_summaries)

    # Save results
    df.to_csv(REFERENCES_WITH_TOPICS_CSV, index=False)

    return {
        "papers_analyzed": len(df),
        "topic_summaries": {str(k): v for k, v in topic_summaries.items()},
        "topic_distribution": df['Topic_Keywords'].value_counts().to_dict(),
        "output_file": REFERENCES_WITH_TOPICS_CSV,
    }


if __name__ == "__main__":
    print("Loading references.csv...")
    result = run_topic_modeling()
    if "error" in result:
        print(result["error"])
    else:
        print(f"Processing {result['papers_analyzed']} papers...")
        print("\n=== Discovered Research Topics ===")
        for topic_idx, summary in result["topic_summaries"].items():
            print(f"Topic {int(topic_idx) + 1}: {summary}")
        print(f"\n✅ Analysis Complete!")
        print(f"   Saved detailed results to: {os.path.abspath(result['output_file'])}")
        print("\n--- Topic Distribution ---")
        for keywords, count in result["topic_distribution"].items():
            print(f"{keywords}    {count}")
