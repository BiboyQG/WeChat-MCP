from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Literal

from openai import OpenAI

from .logging_config import logger


AIProvider = Literal["openai", "ollama"]


@dataclass
class AIConfig:
    provider: AIProvider
    model: str
    base_url: str
    api_key: str | None


def load_ai_config() -> AIConfig:
    """
    Load AI configuration from environment variables.

    Supported providers:
    - openai: uses WECHAT_MCP_AI_API_KEY, WECHAT_MCP_AI_BASE_URL, WECHAT_MCP_AI_MODEL
    - ollama: uses WECHAT_MCP_AI_MODEL and an OpenAI-compatible API at
      http://localhost:11434/v1 by default (or WECHAT_MCP_AI_BASE_URL if set)
    """
    provider = os.getenv("WECHAT_MCP_AI_PROVIDER", "openai").lower()
    if provider not in ("openai", "ollama"):
        raise ValueError(
            f"WECHAT_MCP_AI_PROVIDER must be 'openai' or 'ollama', got {provider!r}"
        )

    model = os.getenv("WECHAT_MCP_AI_MODEL")
    if not model:
        raise ValueError("WECHAT_MCP_AI_MODEL must be set")

    base_url_env = os.getenv("WECHAT_MCP_AI_BASE_URL")
    api_key_env = os.getenv("WECHAT_MCP_AI_API_KEY")

    if provider == "openai":
        if not api_key_env:
            raise ValueError(
                "WECHAT_MCP_AI_API_KEY must be set when WECHAT_MCP_AI_PROVIDER='openai'"
            )
        base_url = base_url_env or "https://api.openai.com/v1"
        api_key = api_key_env
    else:
        # Ollama: OpenAI-compatible API, no real API key required
        base_url = base_url_env or "http://localhost:11434/v1"
        api_key = api_key_env or "ollama"

    config = AIConfig(
        provider=provider, model=model, base_url=base_url, api_key=api_key
    )
    logger.info(
        "Loaded AI config: provider=%s, model=%s, base_url=%s",
        config.provider,
        config.model,
        config.base_url,
    )
    return config


def create_client(config: AIConfig) -> OpenAI:
    """
    Create an OpenAI-compatible client for the given configuration.
    """
    client = OpenAI(base_url=config.base_url, api_key=config.api_key)
    return client


def build_conversation_prompt(
    contact_name: str,
    messages: Iterable[dict[str, str]],
    instructions: str | None = None,
) -> str:
    """
    Build a single text prompt representing the recent conversation.

    Each message dict is expected to have 'sender' and 'text' fields.
    """
    lines: list[str] = []
    for msg in messages:
        sender = msg.get("sender", "UNKNOWN")
        text = msg.get("text", "")
        lines.append(f"{sender}: {text}")

    base_instruction = (
        "You are helping compose a reply in an instant messaging app conversation.\n"
        f"The contact's display name is: {contact_name!r}.\n"
        "Conversation history (from oldest to newest) is below.\n"
        "Each line starts with 'ME', 'OTHER', or 'UNKNOWN'.\n"
        "Reply as ME to the most recent message from OTHER.\n"
        "Return only the message content to send, without quotes or prefixes."
    )

    if instructions:
        base_instruction += "\n\nAdditional instructions:\n" + instructions.strip()

    conversation = "\n".join(lines)
    prompt = base_instruction + "\n\nConversation:\n" + conversation
    return prompt


def generate_reply_for_contact(
    contact_name: str,
    messages: list[dict[str, str]],
    instructions: str | None = None,
) -> str:
    """
    Generate a reply message for a contact using the configured LLM.
    """
    if not messages:
        raise ValueError("No messages available to generate a reply from")

    config = load_ai_config()
    client = create_client(config)

    prompt = build_conversation_prompt(contact_name, messages, instructions)

    logger.info(
        "Requesting LLM reply for contact=%s using model=%s (provider=%s)",
        contact_name,
        config.model,
        config.provider,
    )

    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful assistant that writes natural, concise "
                    "WeChat messages following the user's style."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
    )

    choice = response.choices[0]
    reply = (choice.message.content or "").strip()

    logger.info("Generated reply of length %d characters", len(reply))
    return reply
