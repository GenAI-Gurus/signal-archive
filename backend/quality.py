import logging
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)
_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def _check_faithfulness(short_answer: str, full_body: str) -> float:
    try:
        resp = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research quality reviewer. "
                        "Does the short answer faithfully reflect the main conclusions of the research body? "
                        "Reply with exactly one word: YES, PARTIAL, or NO."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Short answer:\n{short_answer}\n\n"
                        f"Research body (first 4000 chars):\n{full_body[:4000]}"
                    ),
                },
            ],
            max_tokens=5,
            temperature=0,
        )
        verdict = resp.choices[0].message.content.strip().upper().rstrip(".")
        return {"YES": 1.0, "PARTIAL": 0.5, "NO": 0.0}.get(verdict, 0.0)
    except Exception:
        logger.warning("Faithfulness check failed; defaulting to 0.5", exc_info=True)
        return 0.5


async def compute_quality_score(
    source_domains: list[str],
    full_body: str,
    short_answer: str,
) -> float:
    source_score = min(40.0, len(set(source_domains)) / 20 * 40)
    word_count = len(full_body.split())
    word_score = min(30.0, word_count / 2000 * 30)
    faithfulness = await _check_faithfulness(short_answer, full_body)
    faithfulness_score = faithfulness * 30
    return round(source_score + word_score + faithfulness_score, 2)
