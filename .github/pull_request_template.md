## What this changes and why

<!-- The "why" matters more than the "what" here — the diff already shows what changed. -->

## Checklist

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` passes
- [ ] New tools or spec fields have tests in the matching `tests/test_*.py` file
- [ ] If this adds a spec field that gets spliced into generated code (like
      `config.function` or `condition`), it has a validator identifier check
      (see `mcp_server/validator/validate.py`)
- [ ] `render_python` is still deterministic — no LLM calls or
      non-reproducible output in the render path
- [ ] For anything beyond a small fix: linked to the issue where this was discussed first

<!-- See CONTRIBUTING.md for the full checklist and project layout. -->
