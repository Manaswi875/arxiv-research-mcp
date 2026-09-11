import anthropic
from pydantic import BaseModel

MODEL = "claude-haiku-4-5"

_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


class Findings(BaseModel):
    problem: str
    method: str
    result: str


class TopicLabel(BaseModel):
    topic_id: str
    label: str


class TopicLabels(BaseModel):
    labels: list[TopicLabel]


def extract_findings_llm(abstract: str) -> Findings:
    response = _client.messages.parse(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                "Extract the core Problem, Method, and Result from this paper abstract. "
                "Be concise (1-2 sentences each).\n\nAbstract:\n" + abstract
            ),
        }],
        output_format=Findings,
    )
    return response.parsed_output


def label_topics(topic_summaries: dict) -> dict:
    """One batched call covers every topic, regardless of how many there are."""
    lines = "\n".join(f"Topic {topic_id}: {keywords}" for topic_id, keywords in topic_summaries.items())
    prompt = (
        "Each line below is a research topic described by its top TF-IDF keywords. "
        "Give each one a short (3-6 word) human-readable label. Return one entry in `labels` "
        f"for every topic_id listed below - there are {len(topic_summaries)} topics total, "
        "so `labels` must have exactly that many entries.\n\n" + lines
    )
    response = _client.messages.parse(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format=TopicLabels,
    )
    return {entry.topic_id: entry.label for entry in response.parsed_output.labels}
