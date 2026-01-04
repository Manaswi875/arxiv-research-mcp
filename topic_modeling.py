import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
import numpy as np
import os

def run_topic_modeling(num_topics=5):
    print("Loading references.csv...")
    try:
        df = pd.read_csv("references.csv")
    except FileNotFoundError:
        print("references.csv not found.")
        return

    print(f"Processing {len(df)} papers...")
    
    # 1. Feature Engineering
    # Combine relevant text fields to give the model more signal
    # Fill NAs with empty string
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
        init='nndsvd' # Good for sparseness
    )
    nmf_features = nmf_model.fit_transform(tfidf)
    
    # 4. Display Topics
    feature_names = tfidf_vectorizer.get_feature_names_out()
    
    topic_summaries = {}
    print("\n=== Discovered Research Topics ===")
    
    for topic_idx, topic in enumerate(nmf_model.components_):
        # Get top 10 words for this topic
        top_indices = topic.argsort()[:-11:-1]
        top_words = [feature_names[i] for i in top_indices]
        summary = ", ".join(top_words)
        topic_summaries[topic_idx] = summary
        print(f"Topic {topic_idx + 1}: {summary}")
        
    # 5. Assign Dominant Topic to Papers
    # nmf_features is [n_samples, n_topics]
    dominant_topic_indices = np.argmax(nmf_features, axis=1)
    
    df['Topic_ID'] = dominant_topic_indices
    df['Topic_Keywords'] = df['Topic_ID'].map(topic_summaries)
    
    # Save results
    output_file = "references_with_topics.csv"
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ Analysis Complete!")
    print(f"   Saved detailed results to: {os.path.abspath(output_file)}")
    
    # Show sample distribution
    print("\n--- Topic Distribution ---")
    print(df['Topic_Keywords'].value_counts())

if __name__ == "__main__":
    run_topic_modeling()
