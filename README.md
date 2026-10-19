# qwen-chat-template-variants

[![test](https://github.com/ClaudeLiang/qwen-chat-template-variants/actions/workflows/test.yml/badge.svg)](https://github.com/ClaudeLiang/qwen-chat-template-variants/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Serving-time variants of official Qwen chat templates. Each file is a drop-in
`--chat-template` for SGLang, vLLM, and llama.cpp. Tool-call markup stays on
the upstream contract. A variant changes one named behavior.

The checkpoint template remains the default. These files exist for workloads
that want a different prompt order.

## Variants

| File | Model family | Behavior |
| --- | --- | --- |
| [`qwen3.8/system_first.jinja`](qwen3.8/system_first.jinja) | Qwen3.8 (same XML tool format as Qwen3.5 and Qwen3.6) | With tools, the leading system message is rendered before the tools block. |

Upstream Qwen3.8 renders one system turn in this order:

```text
reasoning instruction
# Tools
tool schemas and the tool-call instructions
the caller's system message
```

`system_first` renders:

```text
reasoning instruction
the caller's system message
# Tools
tool schemas and the tool-call instructions
```

Everything after that turn matches the upstream template: user and assistant
messages, XML tool calls, tool results, vision placeholders, and the
`<think>` generation prompt.

## When to use `system_first`

Prefix caches match from the start of the prompt.

Use `system_first` when the system prompt is long and stable, and the tool
list changes from request to request. The system text stays a cacheable
prefix, and a different tool list invalidates only the suffix.

Use the checkpoint template when the tool list is stable and the system
prompt changes. Upstream puts the tools first, so that prefix survives a
system-prompt change.

Qwen3.8 was trained with tools before the system message. This variant keeps
the XML tool-call format the parser expects, and it changes where the system
text sits. Instruction following and tool choice can differ from the
checkpoint template. Compare the two on your own traffic before switching.

`reasoning_effort` is still a sentence inserted at the start of the system
turn, as in the upstream template. `xhigh` (the default) and `low` add a
sentence; `medium` adds none. Changing the effort level changes bytes ahead of the system text,
so it also changes the prefix. `enable_thinking=false` omits the sentence.

## Usage

Point the server at the file. The path replaces the checkpoint template for
every request.

```bash
# SGLang
python -m sglang.launch_server \
  --model-path Qwen/Qwen3.8-27B \
  --chat-template /path/to/qwen3.8/system_first.jinja

# vLLM
vllm serve Qwen/Qwen3.8-27B \
  --chat-template /path/to/qwen3.8/system_first.jinja

# llama.cpp
llama-server -m model.gguf \
  --chat-template-file /path/to/qwen3.8/system_first.jinja --jinja
```

Template kwargs are unchanged from upstream: `enable_thinking`,
`reasoning_effort` (`xhigh`, `medium`, `low`; default `xhigh`),
`preserve_thinking`, `add_vision_id`, and `add_generation_prompt`.

Pass them per request the way your server exposes them, for example
`chat_template_kwargs` in the OpenAI-compatible request body for SGLang and
vLLM.

## Tests

The tests render the Jinja file with Jinja2 in the same sandboxed
environment that transformers uses, and pin the order. They do not load a
model.

```bash
pip install -r requirements-dev.txt
make test
```

`make check-upstream` downloads the upstream template and checks that the
variant renders byte-identical prompts except for the moved system text. CI
runs it weekly to catch upstream changes.

The tests cover the Jinja2 (Python) renderer only. llama.cpp renders with its
own Jinja implementation, which is not exercised in CI.

## Provenance

`qwen3.8/system_first.jinja` is derived from the Qwen3.8 chat template
shipped with [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/chat_template.jinja).
That template is Apache-2.0. The intentional diff is the position of the
leading system message relative to `# Tools`. See `NOTICE`.

This repository does not vendor the upstream file. When Qwen publishes a new
template, rebase the variant onto that file and keep this reorder as the
only intended change. `make check-upstream` verifies that.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Report security issues as described
in [`SECURITY.md`](SECURITY.md). Changes are listed in
[`CHANGELOG.md`](CHANGELOG.md).

## License

Apache License, Version 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

This is an independent project and is not affiliated with or endorsed by
Alibaba Cloud or the Qwen team.
