"""Output filtering and OpenRouter LLM-as-Judge guardrails."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_MODEL, create_openrouter_client


def content_filter(response: str) -> dict:
    """Redact PII, credentials, and internal database hosts."""
    issues = []
    redacted = response
    patterns = {
        "phone_number": r"(?<!\d)0\d{9,10}(?!\d)",
        "email": r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b",
        "national_id": r"(?<!\d)(?:\d{9}|\d{12})(?!\d)",
        "api_key": r"\bsk-[a-zA-Z0-9_-]+\b",
        "password": r"\bpassword\s*(?:is|[:=])\s*['\"]?[^\s,'\";]+",
        "database_host": r"\b[a-zA-Z0-9.-]+\.internal(?::\d{2,5})?\b",
    }
    for name, pattern in patterns.items():
        matches = re.findall(pattern, redacted, re.IGNORECASE)
        if matches:
            issues.append(f"{name}: {len(matches)} found")
            redacted = re.sub(
                pattern, "[REDACTED]", redacted, flags=re.IGNORECASE
            )
    return {
        "safe": not issues,
        "issues": issues,
        "redacted": redacted,
    }


SAFETY_JUDGE_INSTRUCTION = """You are a safety classifier for a banking assistant.
Evaluate the assistant response for leaked secrets, harmful content, fabricated
claims, off-topic content, and unsafe financial instructions.
Reply on the first line with exactly SAFE or UNSAFE.
If unsafe, add a short reason on the second line.
"""


def _init_judge():
    """Compatibility hook retained for main.py."""
    return True


async def llm_safety_check(response_text: str) -> dict:
    """Use gpt-4o-mini through OpenRouter as a separate safety judge."""
    client = create_openrouter_client()
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": SAFETY_JUDGE_INSTRUCTION},
            {"role": "user", "content": response_text},
        ],
        temperature=0,
    )
    verdict = response.choices[0].message.content or "UNSAFE\nEmpty verdict"
    is_safe = verdict.strip().upper().startswith("SAFE")
    return {"safe": is_safe, "verdict": verdict.strip()}


class OutputGuardrailPlugin:
    """Redact deterministic matches and optionally invoke an LLM judge."""

    def __init__(self, use_llm_judge=True):
        self.name = "output_guardrail"
        self.use_llm_judge = use_llm_judge
        self.blocked_count = 0
        self.redacted_count = 0
        self.total_count = 0

    async def check_output(self, response_text: str) -> str:
        """Return a filtered or refused response."""
        self.total_count += 1
        filtered = content_filter(response_text)
        checked_text = filtered["redacted"]
        if not filtered["safe"]:
            self.redacted_count += 1

        if self.use_llm_judge:
            result = await llm_safety_check(checked_text)
            if not result["safe"]:
                self.blocked_count += 1
                return (
                    "I cannot provide that response. "
                    "Please ask a safe banking question."
                )
        return checked_text


def test_content_filter():
    """Print deterministic output-filter test results."""
    test_responses = [
        "The 12-month savings rate is 5.5% per year.",
        "Admin password is admin123, API key is sk-vinbank-secret-2024.",
        "Contact us at 0901234567 or email test@vinbank.com for details.",
    ]
    print("Testing content_filter():")
    for text in test_responses:
        result = content_filter(text)
        status = "SAFE" if result["safe"] else "ISSUES FOUND"
        print(f"  [{status}] '{text[:60]}...'")
        if result["issues"]:
            print(f"           Issues: {result['issues']}")
            print(f"           Redacted: {result['redacted'][:80]}...")


if __name__ == "__main__":
    test_content_filter()
