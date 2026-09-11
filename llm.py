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


def generate_literature_review(papers: list[dict]) -> str:
    """One call synthesizes the whole bibliography into a narrative review.

    Deliberately does NOT use output_format=Pydantic like the two functions above -
    that's right for discrete fields, but forcing multi-paragraph prose through strict
    JSON-string escaping adds risk for zero benefit here. Plain text generation instead.
    """
    if not papers:
        raise ValueError("The bibliography is empty. Save some papers first with save_to_bibliography.")

    numbered = []
    for i, p in enumerate(papers, start=1):
        published = p.get("published")
        year = published.year if hasattr(published, "year") else "n.d."
        numbered.append(
            f'[{i}] "{p.get("title", "")}" ({year})\n'
            f'    Problem: {p.get("problem") or "N/A"}\n'
            f'    Method: {p.get("method") or "N/A"}\n'
            f'    Result: {p.get("result") or "N/A"}'
        )

    prompt = (
        "You are writing a literature review section for a research paper, synthesizing the "
        f"following {len(papers)} papers. Write a cohesive narrative (not a list) that groups "
        "related papers thematically, compares their methods and findings, and highlights trends "
        "or gaps. Cite every paper using its bracketed number exactly as given, e.g. [3], inline "
        "in the text - never invent a number, never omit a citation when referencing a specific "
        "paper's claim. End with a 'References' section listing every number with its title and "
        "year.\n\nPapers:\n\n" + "\n\n".join(numbered)
    )
    response = _client.messages.create(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
