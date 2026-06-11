"""Shared configuration for the OpenRouter-based lab."""
import os
from getpass import getpass

from openai import OpenAI


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"


def setup_api_key() -> str:
    """Load the OpenRouter key without storing it in source files."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        api_key = getpass("Enter OPENROUTER_API_KEY: ")
        os.environ["OPENROUTER_API_KEY"] = api_key
    # NeMo and other OpenAI-compatible clients read these conventional names.
    os.environ.setdefault("OPENAI_API_KEY", api_key)
    os.environ.setdefault("OPENAI_BASE_URL", OPENROUTER_BASE_URL)
    print("OpenRouter API key loaded.")
    return api_key


def create_openrouter_client() -> OpenAI:
    """Create an OpenAI-compatible client configured for OpenRouter."""
    return OpenAI(
        api_key=setup_api_key(),
        base_url=OPENROUTER_BASE_URL,
    )


ALLOWED_TOPICS = [
    "banking", "bank", "account", "transaction", "transfer",
    "loan", "interest", "savings", "credit", "card",
    "deposit", "withdrawal", "balance", "payment", "money",
    "tai khoan", "giao dich", "tiet kiem", "lai suat",
    "chuyen tien", "the tin dung", "so du", "vay",
    "ngan hang", "atm",
]

BLOCKED_TOPICS = [
    "hack", "exploit", "weapon", "drug", "illegal",
    "violence", "gambling", "bomb", "kill", "steal",
]
