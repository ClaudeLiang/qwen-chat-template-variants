# SPDX-License-Identifier: Apache-2.0
"""Render checks for qwen3.8/system_first.jinja.

The template is the Qwen3.8 chat template with one change: when tools are
present, the leading system message is emitted before the tools block.

Set QWEN38_UPSTREAM_TEMPLATE to the path of the upstream chat_template.jinja
to also check the variant against it (`make check-upstream` does this).
"""

import json
import os
import unittest
from pathlib import Path

import jinja2
import jinja2.ext
from jinja2.sandbox import ImmutableSandboxedEnvironment


TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1] / "qwen3.8" / "system_first.jinja"
)
UPSTREAM_PATH = os.environ.get("QWEN38_UPSTREAM_TEMPLATE")
SYSTEM = "SYSTEM_SENTINEL_ALPHA"
USER = "USER_SENTINEL_BETA"


def raise_exception(message):
    raise jinja2.TemplateError(message)


def tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
    # transformers overrides Jinja's tojson: no HTML escaping, no key sorting.
    return json.dumps(
        x,
        ensure_ascii=ensure_ascii,
        indent=indent,
        separators=separators,
        sort_keys=sort_keys,
    )


def make_env():
    # Mirrors the environment transformers' apply_chat_template uses, which is
    # what SGLang and vLLM render with.
    env = ImmutableSandboxedEnvironment(
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=[jinja2.ext.loopcontrols],
    )
    env.filters["tojson"] = tojson
    env.globals["raise_exception"] = raise_exception
    return env


def render(messages, template_path=TEMPLATE_PATH, **kwargs):
    # Missing kwargs stay undefined, matching the serving engines. The template
    # treats those as false via `is undefined` and bare `if` checks.
    template = make_env().from_string(Path(template_path).read_text())
    return template.render(messages=messages, **kwargs)


def tool(name="lookup_order", description="Look up an order."):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    }


def tool_conversation():
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER},
        {
            "role": "assistant",
            "content": "Looking it up.",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_order",
                        "arguments": {"order_id": "A1"},
                    },
                }
            ],
        },
        {"role": "tool", "content": "status=paid"},
        {"role": "user", "content": "Thanks"},
    ]


class SystemFirstOrderTest(unittest.TestCase):
    def test_system_text_precedes_tools(self):
        prompt = render(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER},
            ],
            tools=[tool()],
            reasoning_effort="medium",
            add_generation_prompt=True,
        )
        system_at = prompt.index(SYSTEM)
        tools_at = prompt.index("# Tools")
        user_at = prompt.index(USER)
        self.assertLess(system_at, tools_at)
        self.assertLess(tools_at, user_at)
        self.assertIn("<function=example_function_name>", prompt)
        self.assertIn(json.dumps(tool()), prompt)
        self.assertTrue(
            prompt.startswith("<|im_start|>system\n" + SYSTEM + "\n\n# Tools\n")
        )
        self.assertIn("</IMPORTANT><|im_end|>\n<|im_start|>user\n", prompt)
        self.assertNotIn("SPDX-License-Identifier", prompt)
        self.assertTrue(prompt.endswith("<|im_start|>assistant\n<think>\n"))

    def test_multipart_system_text_precedes_tools(self):
        prompt = render(
            [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": SYSTEM}],
                },
                {"role": "user", "content": USER},
            ],
            tools=[tool()],
            reasoning_effort="medium",
        )
        self.assertLess(prompt.index(SYSTEM), prompt.index("# Tools"))

    def test_empty_system_message_with_tools_adds_no_blank_lines(self):
        prompt = render(
            [
                {"role": "system", "content": "  "},
                {"role": "user", "content": USER},
            ],
            tools=[tool()],
            reasoning_effort="medium",
        )
        self.assertTrue(prompt.startswith("<|im_start|>system\n# Tools\n"))

    def test_tool_schema_is_rendered_verbatim(self):
        description = "Return <b> & 'quoted' text, 中文."
        prompt = render(
            [{"role": "user", "content": USER}],
            tools=[tool(description=description)],
            reasoning_effort="medium",
        )
        self.assertIn(
            json.dumps(tool(description=description), ensure_ascii=False),
            prompt,
        )

    def test_reasoning_sentence_stays_ahead_of_the_system_text(self):
        prompt = render(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER},
            ],
            tools=[tool()],
            reasoning_effort="xhigh",
        )
        effort_at = prompt.index("Reasoning effort is set to xhigh.")
        self.assertLess(effort_at, prompt.index(SYSTEM))
        self.assertLess(prompt.index(SYSTEM), prompt.index("# Tools"))

    def test_default_reasoning_effort_is_xhigh(self):
        prompt = render(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER},
            ],
            tools=[tool()],
        )
        self.assertTrue(
            prompt.startswith(
                "<|im_start|>system\nReasoning effort is set to xhigh."
            )
        )

    def test_low_effort_sentence_stays_ahead_of_the_system_text(self):
        prompt = render(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER},
            ],
            tools=[tool()],
            reasoning_effort="low",
        )
        self.assertLess(
            prompt.index("Reasoning effort is set to low."),
            prompt.index(SYSTEM),
        )

    def test_disabled_thinking_omits_the_effort_sentence(self):
        prompt = render(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER},
            ],
            tools=[tool()],
            reasoning_effort="xhigh",
            enable_thinking=False,
            add_generation_prompt=True,
        )
        self.assertNotIn("Reasoning effort is set to", prompt)
        self.assertLess(prompt.index(SYSTEM), prompt.index("# Tools"))
        self.assertTrue(prompt.endswith("<think>\n\n</think>\n\n"))

    def test_no_tools_renders_the_system_turn_only(self):
        prompt = render(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER},
            ],
            reasoning_effort="medium",
        )
        self.assertNotIn("# Tools", prompt)
        self.assertIn("<|im_start|>system\n" + SYSTEM + "<|im_end|>\n", prompt)
        self.assertIn("<|im_start|>user\n" + USER + "<|im_end|>\n", prompt)

    def test_tools_without_a_system_message_still_open_with_tools(self):
        prompt = render(
            [{"role": "user", "content": USER}],
            tools=[tool()],
            reasoning_effort="medium",
        )
        self.assertTrue(prompt.startswith("<|im_start|>system\n# Tools\n"))
        self.assertLess(prompt.index("# Tools"), prompt.index(USER))

    def test_assistant_tool_call_markup_is_unchanged(self):
        prompt = render(
            tool_conversation(),
            tools=[tool()],
            reasoning_effort="medium",
            preserve_thinking=False,
        )
        self.assertIn(
            "<tool_call>\n<function=lookup_order>\n<parameter=order_id>\nA1\n</parameter>\n</function>\n</tool_call>",
            prompt,
        )
        self.assertIn("<tool_response>\nstatus=paid\n</tool_response>", prompt)

    def test_unknown_reasoning_effort_is_rejected(self):
        with self.assertRaises(jinja2.TemplateError):
            render(
                [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": USER},
                ],
                reasoning_effort="max",
            )

    def test_image_in_system_message_is_rejected(self):
        with self.assertRaises(jinja2.TemplateError):
            render(
                [
                    {"role": "system", "content": [{"type": "image"}]},
                    {"role": "user", "content": USER},
                ],
                tools=[tool()],
                reasoning_effort="medium",
            )

    def test_a_later_system_message_is_rejected(self):
        with self.assertRaises(jinja2.TemplateError):
            render(
                [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": USER},
                    {"role": "system", "content": "mid-conversation"},
                ],
                reasoning_effort="medium",
            )


@unittest.skipUnless(UPSTREAM_PATH, "QWEN38_UPSTREAM_TEMPLATE is not set")
class MatchesUpstreamTest(unittest.TestCase):
    """The reorder is the only difference from the upstream template."""

    CASES = [
        dict(reasoning_effort="medium"),
        dict(reasoning_effort="xhigh", add_generation_prompt=True),
        dict(reasoning_effort="low", preserve_thinking=False),
        dict(enable_thinking=False, add_generation_prompt=True),
        dict(),
    ]

    def assert_same(self, messages, **kwargs):
        self.assertEqual(
            render(messages, **kwargs),
            render(messages, template_path=UPSTREAM_PATH, **kwargs),
        )

    def test_identical_without_tools(self):
        for kwargs in self.CASES:
            with self.subTest(**kwargs):
                self.assert_same(tool_conversation(), **kwargs)
                self.assert_same(tool_conversation()[1:], **kwargs)

    def test_identical_with_tools_and_no_system_message(self):
        for kwargs in self.CASES:
            with self.subTest(**kwargs):
                self.assert_same(
                    tool_conversation()[1:], tools=[tool()], **kwargs
                )

    def test_only_the_system_text_moves_with_tools(self):
        for kwargs in self.CASES:
            with self.subTest(**kwargs):
                ours = render(tool_conversation(), tools=[tool()], **kwargs)
                theirs = render(
                    tool_conversation(),
                    template_path=UPSTREAM_PATH,
                    tools=[tool()],
                    **kwargs,
                )
                moved = theirs.replace(
                    "</IMPORTANT>\n\n" + SYSTEM, "</IMPORTANT>", 1
                ).replace("# Tools\n", SYSTEM + "\n\n# Tools\n", 1)
                self.assertNotEqual(ours, theirs)
                self.assertEqual(ours, moved)


if __name__ == "__main__":
    unittest.main()
