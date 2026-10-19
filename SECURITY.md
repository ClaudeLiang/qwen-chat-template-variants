# Security Policy

## Scope

This repository ships Jinja chat templates. A template runs inside the
inference server's template sandbox and controls how messages and tool
schemas are formatted into the prompt. Relevant reports include a template
that renders caller-controlled content in a way that lets it forge role or
tool-call markup the upstream template would not allow.

Vulnerabilities in SGLang, vLLM, llama.cpp, transformers, or the Qwen models
belong with those projects.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's private vulnerability reporting
("Report a vulnerability" under the repository's Security tab). Include the
template file, the messages and tools that trigger the issue, and the
rendered prompt.

You can expect an acknowledgement within 7 days.
