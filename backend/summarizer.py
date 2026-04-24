from openai import AsyncOpenAI
from config import settings

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def synthesize_summary(question: str, short_answers: list[str]) -> str:
    if not short_answers:
        return ""
    answers_text = "\n".join(f"- {a}" for a in short_answers[:10])
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research librarian. Write a 2–3 sentence synthesis of "
                    "the key findings below, in plain English. Be concise and factual."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nFindings:\n{answers_text}",
            },
        ],
        max_tokens=200,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
