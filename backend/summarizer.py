from openai import AsyncOpenAI
from config import settings

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def synthesize_summary(
    question: str,
    short_answers: list[str],
    weights: list[float] | None = None,
) -> str:
    if not short_answers:
        return ""
    if weights is not None and len(weights) == len(short_answers):
        paired = sorted(zip(weights, short_answers), key=lambda x: x[0], reverse=True)[:10]
        answers_text = "\n".join(f"- [score: {round(w)}] {a}" for w, a in paired)
        system_content = (
            "You are a research librarian. Write a 2–3 sentence synthesis of "
            "the key findings below, in plain English. Be concise and factual. "
            "Each finding is annotated with a quality score (0–100); "
            "higher scores indicate more reliable research — weight them accordingly."
        )
    else:
        answers_text = "\n".join(f"- {a}" for a in short_answers[:10])
        system_content = (
            "You are a research librarian. Write a 2–3 sentence synthesis of "
            "the key findings below, in plain English. Be concise and factual."
        )
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Question: {question}\n\nFindings:\n{answers_text}"},
        ],
        max_tokens=200,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
