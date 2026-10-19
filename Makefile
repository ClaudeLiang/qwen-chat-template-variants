PYTHON ?= python3
UPSTREAM_URL ?= https://huggingface.co/Qwen/Qwen3.8-27B/raw/main/chat_template.jinja

.PHONY: test check-upstream

# Render tests. No network, no model.
test:
	$(PYTHON) -m unittest discover -s tests -v

# Download the upstream template and check that the variant differs from it
# only by the intended reorder.
check-upstream:
	@tmp=$$(mktemp -d) && trap 'rm -rf "$$tmp"' EXIT && \
	curl -fsSL -o "$$tmp/chat_template.jinja" "$(UPSTREAM_URL)" && \
	QWEN38_UPSTREAM_TEMPLATE="$$tmp/chat_template.jinja" \
	$(PYTHON) -m unittest discover -s tests -v
