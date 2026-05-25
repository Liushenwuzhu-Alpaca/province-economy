"""Token counting and context window management."""

from __future__ import annotations

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")

# Approximate token sizes for structured content
TOOL_DEF_TOKENS = 1200  # all tool definitions combined (~1200 tokens)
TOOL_RESULT_OVERHEAD = 150  # per tool result block
MAX_CONTEXT = 8000


def count_tokens(text: str) -> int:
    """Count tokens in a text string."""
    return len(_ENCODING.encode(text))


def count_messages(messages: list[dict]) -> int:
    """Estimate tokens for a list of chat messages."""
    total = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content) + 4  # role + formatting overhead
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    total += count_tokens(block["text"])
        total += 4
    return total


def estimate_total(
    system_prompt: str,
    messages: list[dict],
    pending_tool_calls: int = 0,
) -> int:
    """Estimate total tokens: system + messages + tool defs + pending tool results."""
    return (
        count_tokens(system_prompt)
        + count_messages(messages)
        + TOOL_DEF_TOKENS
        + pending_tool_calls * TOOL_RESULT_OVERHEAD
    )


def trim_history(
    history: list[dict],
    max_tokens: int = MAX_CONTEXT,
    keep_last: int = 3,
) -> list[dict]:
    """Trim oldest message pairs while keeping the most recent `keep_last` rounds.

    Each round = user + assistant pair. Returns trimmed history.
    """
    if not history:
        return history

    # Group into rounds
    rounds: list[list[dict]] = []
    current: list[dict] = []
    for m in history:
        current.append(m)
        if m["role"] == "assistant":
            rounds.append(current)
            current = []
    if current:
        rounds.append(current)

    if len(rounds) <= keep_last:
        return history

    # Estimate tokens for each round and drop from oldest
    while len(rounds) > keep_last:
        dropped = rounds.pop(0)
        # If under budget, stop trimming
        remaining: list[dict] = []
        for r in rounds:
            remaining.extend(r)
        if count_messages(remaining) < max_tokens * 0.7:
            break

    result: list[dict] = []
    for r in rounds:
        result.extend(r)
    return result
