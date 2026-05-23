"""Claude Agent for province economy Q&A with tool use + RAG.

Supports two API backends:
- **anthropic**: Native Anthropic Claude API (default)
- **openai**: OpenAI-compatible API (ZhipuGLM, DeepSeek, etc.)

Both support multi-turn conversation, SSE streaming, and tool calling.
Config via .env file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv

from agent.rag import get_context
from agent.tools import TOOL_DEFINITIONS, TOOL_MAP

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SYSTEM_PROMPT = """\
你是省域经济综合竞争力评价系统的AI助手。你可以回答关于中国31个省份经济评价的问题。

## 项目背景

本项目使用国家统计局公开数据，对31个省/自治区/直辖市的经济竞争力进行量化评价。
- 覆盖年份：2019-2024（共6年）
- 方法A：熵权法（客观赋权 → 综合得分排名）
- 方法B：PCA降维 + K-Means聚类（k=4梯队分类）
- 10个核心指标，3个维度（经济实力、居民生活、产业结构）

## 你的能力

1. 查询排名、指标数据、梯队分类、权重等精确数据（通过工具）
2. 解释方法论（熵权法原理、PCA聚类含义）
3. 分析排名变化背后的经济原因（结合知识库背景）
4. 回答对比类问题（省份间、年份间）

## 回答原则

- 优先使用工具查询精确数据，再用知识库补充背景解释
- 数据驱动，用具体数字支撑观点
- 如果用户没有指定年份，默认使用2024年
- 回答要简洁有条理，避免过长
"""

# 默认模型名（仅当 .env 未配置时生效，实际以 .env 为准）
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_OPENAI_MODEL = "gpt-4o"
MAX_TURNS = 5


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _get_api_type() -> str:
    return os.environ.get("API_TYPE", "anthropic").lower()


# ---------------------------------------------------------------------------
# Tool execution (shared)
# ---------------------------------------------------------------------------

def _run_tool(name: str, input_args: dict) -> str:
    fn = TOOL_MAP.get(name)
    if fn is None:
        return f"未知工具: {name}"
    try:
        return fn(**input_args)
    except Exception as e:
        return f"工具执行错误: {e}"


def _build_messages(
    user_message: str,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    """Build system prompt (with RAG context) and message list."""
    rag_context = get_context(user_message, top_k=3)

    system = SYSTEM_PROMPT
    if rag_context:
        system += f"\n\n## 相关知识库内容（供参考）\n\n{rag_context}"

    messages = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    return system, messages


# ---------------------------------------------------------------------------
# Anthropic backend
# ---------------------------------------------------------------------------

def _anthropic_chat(user_message: str, history: list[dict] | None = None) -> str:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "当前大模型 API 未配置，请在 .env 文件中设置 ANTHROPIC_API_KEY 后重试。"

    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    base_url = os.environ.get("ANTHROPIC_BASE_URL") or None
    client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
    system, messages = _build_messages(user_message, history)

    for _ in range(MAX_TURNS):
        response = client.messages.create(
            model=model, max_tokens=2000, system=system,
            messages=messages, tools=TOOL_DEFINITIONS,
        )
        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if hasattr(b, "text"))
        if response.stop_reason == "tool_use":
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": _run_tool(block.name, block.input)})
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": results})
        else:
            return "".join(b.text for b in response.content if hasattr(b, "text")) or "当前大模型 API 未配置，请在 .env 文件中设置后重试。"
    return "当前大模型 API 未配置，请在 .env 文件中设置后重试。"


def _anthropic_stream(
    user_message: str, history: list[dict] | None = None,
) -> Generator[str, None, None]:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        yield _sse("error", {"text": "当前大模型 API 未配置，请在 .env 文件中设置 ANTHROPIC_API_KEY 后重试。"})
        yield _sse("done", {})
        return

    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    base_url = os.environ.get("ANTHROPIC_BASE_URL") or None
    client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
    system, messages = _build_messages(user_message, history)

    for _ in range(MAX_TURNS):
        with client.messages.stream(
            model=model, max_tokens=2000, system=system,
            messages=messages, tools=TOOL_DEFINITIONS,
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                    yield _sse("token", {"text": event.delta.text})
            final = stream.get_final_message()

        if final.stop_reason == "end_turn":
            yield _sse("done", {})
            return
        if final.stop_reason == "tool_use":
            results = []
            for block in final.content:
                if block.type == "tool_use":
                    yield _sse("tool", {"name": block.name, "input": block.input})
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": _run_tool(block.name, block.input)})
            messages.append({"role": "assistant", "content": final.content})
            messages.append({"role": "user", "content": results})
        else:
            yield _sse("done", {})
            return
    yield _sse("done", {})


# ---------------------------------------------------------------------------
# OpenAI-compatible backend
# ---------------------------------------------------------------------------

def _openai_tools_schema() -> list[dict]:
    """Convert Anthropic tool definitions to OpenAI function calling format."""
    tools = []
    for t in TOOL_DEFINITIONS:
        tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        })
    return tools


def _openai_chat(user_message: str, history: list[dict] | None = None) -> str:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "当前大模型 API 未配置，请在 .env 文件中设置 OPENAI_API_KEY 后重试。"

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    client = OpenAI(api_key=api_key, base_url=base_url)
    system, raw_messages = _build_messages(user_message, history)

    messages = [{"role": "system", "content": system}]
    for m in raw_messages:
        messages.append(m)

    for _ in range(MAX_TURNS):
        response = client.chat.completions.create(
            model=model, max_tokens=2000, messages=messages,
            tools=_openai_tools_schema(),
        )
        choice = response.choices[0]
        msg = choice.message

        if choice.finish_reason == "stop":
            return msg.content or "当前大模型 API 未配置，请在 .env 文件中设置后重试。"

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = _run_tool(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            return msg.content or "当前大模型 API 未配置，请在 .env 文件中设置后重试。"
    return "当前大模型 API 未配置，请在 .env 文件中设置后重试。"


def _openai_stream(
    user_message: str, history: list[dict] | None = None,
) -> Generator[str, None, None]:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        yield _sse("error", {"text": "当前大模型 API 未配置，请在 .env 文件中设置 OPENAI_API_KEY 后重试。"})
        yield _sse("done", {})
        return

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    client = OpenAI(api_key=api_key, base_url=base_url)
    system, raw_messages = _build_messages(user_message, history)

    messages = [{"role": "system", "content": system}]
    for m in raw_messages:
        messages.append(m)

    for _ in range(MAX_TURNS):
        response = client.chat.completions.create(
            model=model, max_tokens=2000, messages=messages,
            tools=_openai_tools_schema(), stream=True,
        )

        current_text = ""
        tool_calls_map: dict[int, dict] = {}

        for chunk in response:
            delta = chunk.choices[0].delta

            # Text content
            if delta.content:
                current_text += delta.content
                yield _sse("token", {"text": delta.content})

            # Tool calls (accumulated across chunks)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {"id": tc.id or "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_map[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_map[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_map[idx]["arguments"] += tc.function.arguments

            # Check finish
            if chunk.choices[0].finish_reason == "stop":
                yield _sse("done", {})
                return

            if chunk.choices[0].finish_reason == "tool_calls":
                # Process accumulated tool calls
                assistant_msg = {"role": "assistant", "content": current_text or None, "tool_calls": []}
                for idx in sorted(tool_calls_map):
                    tc = tool_calls_map[idx]
                    assistant_msg["tool_calls"].append({
                        "id": tc["id"], "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    })
                messages.append(assistant_msg)

                for idx in sorted(tool_calls_map):
                    tc = tool_calls_map[idx]
                    args = json.loads(tc["arguments"])
                    yield _sse("tool", {"name": tc["name"], "input": args})
                    result = _run_tool(tc["name"], args)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

                # Continue loop for next turn
                break
        else:
            # Stream ended without explicit finish reason
            yield _sse("done", {})
            return

    yield _sse("done", {})


# ---------------------------------------------------------------------------
# Public API — dispatch by API_TYPE
# ---------------------------------------------------------------------------

def chat(user_message: str, history: list[dict] | None = None) -> str:
    """Non-streaming chat, dispatches to the configured backend."""
    if _get_api_type() == "openai":
        return _openai_chat(user_message, history)
    return _anthropic_chat(user_message, history)


def chat_stream(
    user_message: str, history: list[dict] | None = None,
) -> Generator[str, None, None]:
    """Streaming chat (SSE), dispatches to the configured backend."""
    if _get_api_type() == "openai":
        yield from _openai_stream(user_message, history)
    else:
        yield from _anthropic_stream(user_message, history)


def _sse(event: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
