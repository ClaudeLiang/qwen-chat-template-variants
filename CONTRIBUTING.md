# Contributing

Contributions are licensed under the Apache License, Version 2.0, the same
license as this repository. See `LICENSE`.

## What belongs here

A serving-time variant of an official Qwen chat template. Each variant is one
Jinja file under a version directory:

```text
qwen3.8/system_first.jinja
```

The file is passed to an inference server with `--chat-template` (SGLang,
vLLM) or `--chat-template-file` (llama.cpp). It replaces the checkpoint
template for that request.

## Rules for a new variant

1. Start from the upstream template for that model version. Link the source
   file in the variant's header comment and in `NOTICE` if the upstream
   attribution is not already covered.
2. Keep the upstream tool-call markup. A variant may change prompt order or
   another named behavior. It does not invent a new tool-call syntax.
3. Describe the behavior in `README.md`, including when the upstream order is
   the better choice.
4. Add a render test under `tests/` that pins the behavior with a sentinel
   string. Run `make test`. If the variant has an upstream-comparison test,
   run `make check-upstream` too.
5. Leave the rendered prompt free of the file's header comment. Jinja comments
   are fine; text outside `{# #}` is part of the prompt.

## Rebasing onto a newer upstream template

Copy the new upstream file, re-apply only this variant's intended diff, and
update the test if the surrounding markup changed. `make check-upstream` must
pass against the new upstream file. Say so in the pull request and add an
entry to `CHANGELOG.md`.

## Pull requests

- Keep one variant or one rebase per pull request.
- `make test` must pass. CI runs it on every pull request.
- Note user-visible changes under "Unreleased" in `CHANGELOG.md`.

By participating you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
