---
name: python-deslop
description: Remove AI smells and untangle spaghetti Python written by agents. Use when asked to clean up Python code, deslop an agent-written codebase, remove dead code, add structured JSON logging, reduce over-engineering, fix type/lint issues, remove circular imports, or make Python more idiomatic and maintainable.
---

# Python deslop

Clean Python code by making it simpler, typed, lint-clean, less agent-shaped, and free of verified dead code. Prefer small, mechanical changes first, then refactors backed by tests and type/lint output.

## Required workflow

Complete every numbered step below. Do not stop after the tool-only steps: the deslop passes are part of the required workflow. If a step is not applicable, say why in the final report. Step 8 (structured logging with `structlog`) is the one exception: it is opt-in, not required — only do it if the user explicitly asked for structured/JSON logging in this request. Otherwise skip it silently, without noting it as skipped in the final report.

1. Inspect the project layout and Python tooling:
   - `pyproject.toml`, `ruff.toml`, `.ruff.toml`, `ty.toml`
   - dependency manager files: `uv.lock`, `poetry.lock`, `requirements*.txt`, `setup.py`
   - test commands in README, CI, `Makefile`, `justfile`, `tox.ini`, `noxfile.py`
   - existing logging setup, `logging.getLogger`, `logging.basicConfig`, custom logger wrappers, and `print()` usage
   - the minimum Python version the service actually runs on: `requires-python` in `pyproject.toml`, `python_requires` in `setup.py`/`setup.cfg`, `ruff`'s `target-version`, CI matrix/runtime files (`.python-version`, Dockerfile base image, CI workflow), deployment/runtime config. Use the highest floor you can confirm; if evidence conflicts or nothing pins a version, do not assume 3.12+.
2. Ensure `ruff`, `ty`, and `vulture` are available as dev tools.
   - If they are missing from dev dependencies, add them as dev dependencies.
   - Prefer uv when the project uses uv: `uv add --dev ruff ty vulture`.
   - If uv is not available but the project clearly uses another manager, use that manager's dev dependency mechanism.
   - Do not silently add runtime dependencies except for `structlog`, and only when the user explicitly asked for structured logging and you add or use the structured logging module from step 8.
3. Merge this baseline config into the existing config file.
   - Prefer `pyproject.toml`; if the project already uses `ruff.toml`/`.ruff.toml` or `ty.toml`, merge there instead.
   - Preserve unrelated settings.
   - Keep stricter existing settings unless they conflict with the requested baseline.
   - Do not delete project-specific `exclude`, `src`, `target-version`, per-file ignores, or formatter settings unless they are obsolete and you can justify it.

   ```toml
   [tool.ruff.lint]
   select = [
     "E",                      # pycodestyle errors
     "F",                      # Pyflakes
     "W",                      # pycodestyle warnings
     "B",                      # bugbear
     "Q",                      # quotes
     "SIM",                    # simplify
     "I", "PLC0415", "E402",   # imports
     "C901", "PLR0912"         # complexity
   ]
   ignore = []
   fixable = ["ALL"]

   [tool.ruff.format]
   quote-style = "double"
   indent-style = "space"
   line-ending = "auto"
   docstring-code-format = true
   docstring-code-line-length = 120

   [tool.ty.rules]
   possibly-unresolved-reference = "warn"
   ambiguous-protocol-member = "warn"
   unresolved-attribute = "ignore"
   ```
4. Run `uv run ty check`.
   - Resolve type issues properly.
   - Avoid papering over errors with `Any`, casts, `type: ignore`, or looser signatures unless the boundary is dynamic.
5. Run `uv run ruff check --fix`.
   - Let Ruff perform safe automatic edits.
6. Run `uv run ruff check`.
   - Fix remaining non-auto-fixable issues using project context.
7. Run `uv run vulture . --min-confidence 80` and delete verified dead code.
   - Treat Vulture output as leads, not proof. Check callers with search, public exports, entry points, tests, framework conventions, migrations, plugin hooks, pytest fixtures, pydantic/dataclass fields, and serialization boundaries before deleting.
   - Prefer deleting unused private functions, classes, variables, imports, branches, files, stale compatibility shims, and one-off helpers that have no live callers.
   - Keep externally referenced or convention-based code only when you can name the boundary. If needed, add a narrow Vulture whitelist with a short reason instead of broad suppressions.
   - Re-run Vulture after deletions until remaining findings are accepted residuals.
8. Only if the user explicitly asked for structured/JSON logging in this request: add structured JSON logging with `structlog`, unless the project already has equivalent behavior. If the user did not ask for logging changes, skip this entire step and leave existing logging (stdlib, `print()`, or otherwise) untouched.
   - Add `structlog` as a runtime dependency only when the project lacks it and you add/use this logging module.
   - Put the module inside the main importable package as `<package>/logging.py` so callers can import `from <package>.logging import get_logger`. Avoid a repository-root `logging.py` that can shadow the stdlib module.
   - Use this implementation unless an existing project logger already provides the same JSON/pretty behavior and lazy setup:

   ```python
   import os
   import logging
   import sys

   from typing import Any

   import structlog

   # Read logging config from env
   LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
   LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

   _configured = False

   def _rename_event_to_message(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
       event = event_dict.pop("event", None)
       if event is not None:
           event_dict["message"] = event
       return event_dict


   def setup_logging() -> None:
       """Configure structlog once for the whole process."""

       global _configured

       if _configured:
           return

       log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
       pretty = LOG_FORMAT.lower() == "pretty"

       # Shared processors - run on BOTH native structlog events and foreign stdlib events.
       shared_processors: list[Any] = [
           structlog.contextvars.merge_contextvars,
           structlog.stdlib.add_log_level,
           structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
           structlog.processors.StackInfoRenderer(),
           structlog.processors.UnicodeDecoder(),
       ]

       if pretty:
           # ConsoleRenderer renders exc_info itself (colored, with rich if available),
           # so we deliberately do NOT pre-process exceptions in this mode. We also
           # leave the `event` key alone so ConsoleRenderer can render it as the
           # primary message.
           renderer = structlog.dev.ConsoleRenderer()
       else:
           # JSON mode: turn exc_info into a structured `exception` field
           # (type / value / frames) before rendering - friendlier for most
           # log processing backends.
           shared_processors.append(structlog.processors.dict_tracebacks)
           shared_processors.append(_rename_event_to_message)
           renderer = structlog.processors.JSONRenderer()

       formatter = structlog.stdlib.ProcessorFormatter(
           foreign_pre_chain=shared_processors,
           processors=[
               structlog.stdlib.ProcessorFormatter.remove_processors_meta,
               renderer,
           ],
       )

       handler = logging.StreamHandler(sys.stderr)
       handler.setFormatter(formatter)

       root_logger = logging.getLogger()
       root_logger.handlers.clear()
       root_logger.addHandler(handler)
       root_logger.setLevel(log_level)

       # Level filtering handled by the stdlib root logger
       structlog.configure(
           processors=[
               *shared_processors,
               structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
           ],
           wrapper_class=structlog.stdlib.BoundLogger,
           context_class=dict,
           logger_factory=structlog.stdlib.LoggerFactory(),
           cache_logger_on_first_use=True,
       )

       _configured = True


   def get_logger(name: str | None = None) -> Any:
       """Return a structlog logger, configuring it on first use."""

       setup_logging()
       return structlog.get_logger(name)
   ```

   - Replace direct stdlib logger setup and module loggers with `from <package>.logging import get_logger` and `logger = get_logger(__name__)` or `logger = get_logger()` for single-entry scripts.
   - Convert logging calls to structlog style with event names plus key/value fields: `logger.info("processed_file", path=str(path), count=count)`. Prefer fields over interpolated strings when values are useful for querying.
   - Convert as many `print()` calls as possible to proper log levels: `debug` for diagnostics, `info` for lifecycle/progress, `warning` for recoverable anomalies, `error` for failures, and `exception`/`exc_info=True` when stack traces are needed.
   - Keep `print()` only for intentional user-facing CLI output, prompts, machine-readable stdout, or test fixtures; document any remaining prints in the final report.
   - Remove redundant `logging.basicConfig`, ad-hoc handlers, and duplicate logger wrappers once callers use the shared module.
9. Remove dynamic access when static code is better.
   - Get rid of as many `getattr()`, `hasattr()`, and broad `isinstance()` calls as possible.
   - Replace dynamic attribute access with explicit attributes, protocols, dataclasses, typed configs, or simple branching.
   - Keep dynamic access only at real dynamic boundaries: plugin systems, untrusted JSON, CLI/env parsing, optional third-party integrations, or compatibility shims. Isolate those boundaries and type the result.
10. Remove `TYPE_CHECKING` import hacks.
    - Get rid of all `if TYPE_CHECKING:` blocks.
    - Restructure modules so circular imports do not occur: move shared types to a neutral module, split side-effectful initialization from definitions, depend inward on stable interfaces, or use local imports only as a last resort and only where they are the clean architectural boundary.
    - Do not replace `TYPE_CHECKING` with stringly, hidden, or more fragile cycles.
11. Remove `from __future__ import annotations` on services confirmed to run on Python 3.12+.
    - Only do this when step 1 confirmed a minimum runtime of Python 3.12 or newer. If the floor is lower, unconfirmed, or the target is a library that supports older interpreters, leave the import in place.
    - Delete the `from __future__ import annotations` line from each affected module.
    - This import only postpones annotation evaluation (PEP 563); it does not affect runtime behavior of ordinary code, so removal is behavior-preserving on 3.12+. The one exception is code that introspects annotations at runtime (e.g. `typing.get_type_hints`, some `dataclasses`/`pydantic`/serialization paths that read `__annotations__` directly): re-check those call sites still resolve correctly without the postponed-evaluation behavior, since strings vs. real objects in `__annotations__` can differ.
    - Do not add this back as a suppression or compatibility shim; if a module genuinely needs postponed evaluation on a confirmed 3.12+ target, that is itself a smell to fix (e.g. resolve a real circular import per step 10) rather than a reason to keep the import.
12. Delete pointless indirection.
    - Remove reassignments that add no meaning, for example `svc = cfg.svc`, `fp = function_param`, or `self._schema = schema` when only mirrored and never needed as object state.
    - Keep a local only when it shortens repeated complex expressions, gives a real domain name, narrows a type, or avoids repeated expensive work.
13. Inline one-off helpers.
    - Delete helper functions used only once when they do not improve clarity, testing, reuse, or separation of concerns.
    - Keep a one-use helper if it names a complex domain concept, isolates IO, removes duplication across future extension points, or is independently tested.
14. Strip AI-smell prose.
    - Remove useless, obvious, stale, or incorrect comments and docstrings.
    - Shorten remaining comments/docstrings. Explain why, not what.
    - Remove filler and AI-sounding words such as "genuinely", "robust", "seamless", "comprehensive", "leverages", "delve", and em-dash-heavy phrasing.
    - Do not delete public API docs that users rely on; make them concise and accurate.
15. Remove suppressions.
    - Get rid of as many `type: ignore`, `# noqa`, Ruff per-file ignores, and Vulture whitelists as possible.
    - Resolve root causes with better types, imports, module structure, dead-code deletion, or simpler code.
    - Keep a suppression only for a documented external bug or unavoidable dynamic boundary, and make it narrow with the exact rule/code.
16. Remove `# fmt: skip`, `# fmt: off`, and `# fmt: on` comments.
    - Find every occurrence and fix the underlying reason the formatter was bypassed instead of just deleting the comment: undo manual alignment/spacing, split or restructure long lines, replace ad-hoc multi-line literals with a layout Ruff formats cleanly, or reformat the block so `ruff format` output is correct on its own.
    - After fixing the code, drop the skip/off/on directive so the line or block is formatted normally going forward.
    - Keep a directive only when formatting would break a real invariant no restructuring reasonably fixes (e.g. a hand-aligned data table where the alignment is the point, or a generated block). Keep it narrow (single line, not a wide `fmt: off`/`fmt: on` region) and note why in the final report.
    - Verify with `uv run ruff format --check` (or a normal `ruff format` run) after step 18 that resolved lines now format stably.
17. Reduce complexity for `C901` and `PLR0912` findings.
    - Prefer guard clauses, early returns, table-driven dispatch, and extracting coherent domain operations.
    - Do not create tiny procedural fragments just to satisfy the metric.
    - Avoid new classes unless they model stable state or behavior.
18. Apply refactor style constraints while making all changes.
    - Make behavior-preserving edits unless the user explicitly asks for behavior changes.
    - Commit to direct, idiomatic Python over generic enterprise patterns.
    - Prefer clear functions, typed dataclasses, enums, protocols, and small modules.
    - Keep public interfaces stable unless changing them is required to remove the smell; then update all callers and tests.
    - Read nearby code before changing a pattern. Match the project's real style after applying the requested Ruff/format rules.
    - Use tests and tool output as the authority. Do not assume a refactor is safe because it looks cleaner.
19. Run `uv run ruff format .`.
    - Format after lint, Vulture, logging, and deslop fixes.
20. Re-run `uv run ty check`, `uv run ruff check`, and `uv run vulture . --min-confidence 80` after manual edits.
    - Repeat fix-and-check until clean or until only explicitly accepted residual issues remain.
21. Run the project tests or the smallest relevant test command.
    - If no tests exist, run import/smoke checks for touched modules, including one check that imports the new logging module when it was added.
22. Report the completed work.
    - Summarize config/dependency changes, including `vulture`, and `structlog` if step 8 ran.
    - List type/lint/format/Vulture commands run and their results.
    - List tests or smoke checks run.
    - Summarize dead-code deletions, logging conversion (if any), and major deslop refactors.
    - State the confirmed minimum Python version and whether `from __future__ import annotations` imports were removed (step 11); if step 11 was skipped, say why (version not 3.12+, unconfirmed, or a library target).
    - List any remaining suppressions, `fmt: skip`/`fmt: off` directives, Vulture findings, dynamic constructs, or `print()` calls and why they remain.

If the project does not use uv, still prefer `uv run` when uv can run the project without disrupting it. Otherwise use the project's runner and document the deviation.
