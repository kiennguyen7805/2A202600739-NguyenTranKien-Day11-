"""Helpers for sending messages through the OpenRouter pipeline."""
from dataclasses import dataclass, field
from uuid import uuid4

from core.config import create_openrouter_client


@dataclass
class ChatSession:
    """Minimal conversation state compatible with the original lab helper."""

    id: str = field(default_factory=lambda: str(uuid4()))
    messages: list = field(default_factory=list)


async def chat_with_agent(agent, runner, user_message: str, session_id=None):
    """Run input guards, call OpenRouter, then run output guards."""
    session = runner.get_session(session_id)

    for plugin in runner.plugins:
        check_input = getattr(plugin, "check_input", None)
        if check_input:
            block_message = await check_input(user_message)
            if block_message:
                return block_message, session

    messages = [
        {"role": "system", "content": agent.instruction},
        *session.messages,
        {"role": "user", "content": user_message},
    ]
    client = create_openrouter_client()
    response = client.chat.completions.create(
        model=agent.model,
        messages=messages,
        temperature=agent.temperature,
    )
    if not response.choices:
        raise RuntimeError("OpenRouter returned no choices.")

    response_text = response.choices[0].message.content or ""
    for plugin in runner.plugins:
        check_output = getattr(plugin, "check_output", None)
        if check_output:
            response_text = await check_output(response_text)

    session.messages.extend([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response_text},
    ])
    return response_text, session
