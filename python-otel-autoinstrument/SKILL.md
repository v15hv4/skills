---
name: python-otel-autoinstrument
description: Auto-instrument a Python application with OpenTelemetry. Use when asked to add OpenTelemetry/otel tracing to a Python app, wire up observability/instrumentation, add distributed tracing, or find and install opentelemetry-instrumentation-* packages for an app's dependencies.
---

# Python OTel auto-instrument

Add OpenTelemetry tracing to a Python app by matching its dependencies against known instrumentation packages, installing them with `uv`, and wiring them into the app's actual entrypoint(s) — not just listing packages.

## Required workflow

Complete every step. Do not stop after installing packages: wiring the instrumentors into real code and running checks are part of the job, not optional polish.

### 1. Identify the app and its dependencies

- Find the target app's `pyproject.toml`. If there are multiple apps/packages in the repo, ask which one (or confirm scope) before proceeding.
- Read `[project.dependencies]`, `[project.optional-dependencies]`, `[dependency-groups]`, and `[tool.poetry.dependencies]` if present.
- Identify the app's shape, since it determines wiring in step 4: web framework (Flask/FastAPI/Django/Starlette/aiohttp/Falcon/Pyramid/Tornado), entrypoint files (`main.py`, `wsgi.py`, `asgi.py`, `manage.py`, `[project.scripts]`), worker processes (Celery, RQ), and any DB/cache/queue/HTTP clients in use (SQLAlchemy, psycopg2/psycopg, redis, pymongo, requests/httpx, boto3, kafka, pika/aio-pika, grpc).
- Note whether `structlog` is a dependency — if so, step 5 adds trace context to its log output.
- Make sure the app's real environment is installed before the next step: `uv sync` in the app directory. Instrumentation discovery is much more accurate against an installed venv (catches transitive libraries, exact versions) than against the raw dependency strings.

### 2. Discover matching instrumentation packages

Do not try to browse `https://opentelemetry.io/ecosystem/registry/?language=python&component=instrumentation` directly with a fetch tool — it's a client-side JS app and a plain fetch will not return the entries (verified: the rendered HTML has no registry data in it). Instead use its underlying structured data source, which the bundled script already does for you:

```bash
uv run --python 3.12 /home/vishva/.claude/skills/python-otel-autoinstrument/scripts/discover_instrumentation.py /path/to/app
```

This prints a JSON report with:
- `bootstrap_gen_matches` — matches against `opentelemetry-python-contrib`'s own authoritative library→instrumentation map (same data `opentelemetry-bootstrap` uses). **High precision, prefer these.**
- `bootstrap_live_requirements` — what `opentelemetry-bootstrap -a requirements` reports when actually run against the app's installed venv (via `uv run --project`). Useful as a cross-check and to catch transitively-installed libraries the declared-dependency scan misses.
- `registry_matches` — fuzzy matches against `data/registry/instrumentation-python-*.yml` in the `open-telemetry/opentelemetry.io` repo (the real backing data for the registry page). Covers things contrib doesn't have: third-party/GenAI/vector-DB instrumentations (Anthropic, OpenAI, Cohere, LangChain, LlamaIndex, Pinecone, Qdrant, Weaviate, Chroma, Milvus, Mistral, Replicate, Transformers, etc.) and OpenInference/Traceloop alternatives. **Lower precision — sanity-check every entry.**
- `unmatched_dependencies` — deps with no instrumentation found; note these in your final report rather than silently dropping them.

Before moving on, review the output by hand:
- Drop registry matches that are obviously wrong (e.g. substring matches on the wrong library — `psycopg2-binary` fuzzy-matching the `psycopg` (v3) package is a known false positive of the slug-matching heuristic).
- When more than one option exists for the same dependency (e.g. official contrib `opentelemetry-instrumentation-openai-v2` vs. OpenInference's `openinference-instrumentation-openai` vs. Traceloop's `opentelemetry-instrumentation-openai`), default to the official `open-telemetry/opentelemetry-python-contrib` package unless the user has said they want OpenInference/Traceloop-style GenAI spans (those target LLM observability platforms like Arize Phoenix / Traceloop and have a different span shape).
- Only keep packages for dependencies the app actually has — don't install speculative instrumentation.
- If the script can't reach GitHub, fall back to what you know of common `opentelemetry-instrumentation-*` contrib packages, but say so in your final report — don't present a memory-based guess as if it were verified against the registry.

### 3. Add the packages with `uv`

In the app directory:

```bash
uv add opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-instrumentation \
  <each confirmed instrumentation package from step 2>
```

- These are runtime dependencies (not `--dev`) — they run in production to emit telemetry.
- If `bootstrap_gen_matches` gave an exact pinned spec (e.g. `==0.65b0.dev`), you can pass that same spec to `uv add` to keep the instrumentation packages in lockstep with the contrib release the app's `opentelemetry-instrumentation` version expects; otherwise let `uv` resolve normally.
- If `uv add` fails for a derived registry package name (the derivation is a heuristic — see script docstring), check the actual PyPI name from the registry entry's `urls.repo` before giving up on it.

### 4. Wire instrumentation into the application code

This is the step most agents skip — don't just install packages and stop. Add a single observability setup module, e.g. `<package>/otel.py` (or `observability/otel.py`), that:

```python
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry() -> None:
    resource = Resource.create(
        {"service.name": os.environ.get("OTEL_SERVICE_NAME", "<app-name>")}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
```

Then, for each matched instrumentation package, call its `Instrumentor` at the right point — inspect the actual app code rather than guessing:

- **Request-scoped frameworks** need the live app/router object, not a bare `.instrument()`: `FlaskInstrumentor().instrument_app(app)`, `FastAPIInstrumentor.instrument_app(app)`, Django needs `DjangoInstrumentor().instrument()` called before Django loads apps (e.g. top of `manage.py`/`asgi.py`/`wsgi.py`), `starlette`/ASGI apps use `OpenTelemetryMiddleware`.
- **Global client patches** (requests, httpx, redis, pymongo, psycopg2, sqlalchemy, celery, kafka, pika, boto3/botocore, grpc) typically just need `XInstrumentor().instrument()` called once at process startup, before the client is first used. `SQLAlchemyInstrumentor().instrument(engine=engine)` additionally wants the actual engine object if there's a single shared one.
- Call `setup_telemetry()` and the instrumentor calls as early as possible in every real entrypoint (WSGI/ASGI app factory, Celery worker `__init__`, script `main()`), not buried behind lazy imports.
- Respect env-based OTel config conventions (`OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_RESOURCE_ATTRIBUTES`) instead of hardcoding endpoints.

### 5. Add trace context to logs (structlog only)

If `structlog` is not a dependency, skip this step. If it is, find its `structlog.configure(...)` call and add a processor that stamps the current span's context onto every log event:

```python
from typing import Any, MutableMapping

from opentelemetry import trace

def add_otel_context(_logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    span = trace.get_current_span()
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span_id"] = format(ctx.span_id, "016x")
    event_dict["trace_id"] = format(ctx.trace_id, "032x")
    if parent:
        event_dict["parent_span_id"] = format(parent.span_id, "016x")

    return event_dict
```

- Add `add_otel_context` to the existing `processors=[...]` list passed to `structlog.configure(...)` — place it after context-merging processors (e.g. `structlog.contextvars.merge_contextvars`) and before the final renderer (`JSONRenderer`, `ConsoleRenderer`, etc.), since it needs to run while the event dict is still mutable and before whatever serializes it.
- No new package is required — this only needs the `opentelemetry` API that's already installed via `opentelemetry-sdk`/`opentelemetry-instrumentation` from step 3.

### 6. Run checks and tests

- Run the project's existing lint/type checks if configured (`uv run ruff check`, `uv run ty check` / `mypy`, etc.) — don't add new tooling, just use what's there.
- Run the test suite (`uv run pytest` or whatever the project uses) if tests exist.
- Do a real smoke check, not just a type check: import the app / run its entrypoint locally far enough to confirm `setup_telemetry()` and every instrumentor call execute without `ImportError`/`AttributeError` (a wrong instrumentor call signature is a common mistake — e.g. calling `.instrument()` with no args on something that requires an app/engine). It's fine if there's no live OTLP collector to send spans to — that should fail as a connection/export issue at worst, not break app startup.
- Summarize for the user: dependencies matched, packages installed, where wiring was added (including the structlog processor if added), anything in `unmatched_dependencies`, and check/test results.
