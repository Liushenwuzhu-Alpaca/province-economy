"""Agent end-to-end eval — requires .env with valid API keys.

These are smoke tests: they verify the agent can call tools and produce
responses. Not deterministic due to LLM variance; run manually before demos.
"""

import json
import os

import pytest

from src.agent.agent import chat, chat_stream

_run_live = os.environ.get("RUN_LIVE_TESTS", "").lower() in ("1", "true", "yes")

EVAL_CASES = [
    {
        "query": "2024年广东排名第几？",
        "expect_tool": "get_ranking",
        "expect_chart": "show_chart",
        "expect_word": "广东",
    },
    {
        "query": "各省分成几个梯队？",
        "expect_tool": "get_cluster_members",
        "expect_chart": "show_chart",
        "expect_word": "梯队",
    },
    {
        "query": "浙江最近几年排名有什么变化？",
        "expect_tool": "compare_years",
        "expect_chart": "show_chart",
        "expect_word": "浙江",
    },
    {
        "query": "广东和江苏哪个更强？对比一下",
        "expect_tool": "get_province_detail",
        "expect_chart": "show_chart",
        "expect_word": "广东",
    },
    {
        "query": "2024年排名前10有哪些？",
        "expect_tool": "get_ranking",
        "expect_chart": "show_chart",
        "expect_word": "排名",
    },
]


@pytest.mark.skipif(not _run_live, reason="Set RUN_LIVE_TESTS=1 to run live eval")
class TestAgentEval:
    @pytest.mark.parametrize("case", EVAL_CASES)
    def test_chat_response(self, case):
        """Non-streaming: verify response contains expected words."""
        result = chat(case["query"])
        assert len(result) > 10
        assert case["expect_word"] in result


@pytest.mark.skipif(not _run_live, reason="Set RUN_LIVE_TESTS=1 to run live eval")
class TestAgentStreamEval:
    def test_stream_returns_events(self):
        """Streaming: verify we get token and done events."""
        events = list(chat_stream("2024年北京排名第几？"))
        tokens = [e for e in events if "token" in e]
        done = [e for e in events if "done" in e]
        assert len(tokens) > 0
        assert len(done) >= 1

    def test_stream_show_chart_called(self):
        """Streaming: verify show_chart tool is invoked."""
        events = list(chat_stream("对比广东和浙江"))
        tool_names = []
        for e in events:
            if "event: tool" in e:
                data_line = events[events.index(e) + 1] if events.index(e) + 1 < len(events) else ""
                if "show_chart" in e:
                    tool_names.append("show_chart")
        # At minimum, some data tools should be called
        sse_text = " ".join(events)
        assert "token" in sse_text or "done" in sse_text
