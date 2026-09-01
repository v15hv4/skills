---
name: golang-otel-autoinstrument
description: Auto-instrument a Go application with OpenTelemetry. Use when asked to add OpenTelemetry/OTel tracing to a Go app, wire observability or distributed tracing into Go services, or find and install matching Go instrumentation libraries. Use the zero-code path only when the user explicitly wants eBPF, compile-time, or Kubernetes Operator instrumentation.
---

# Go OTel auto-instrument

Add OpenTelemetry tracing to a Go application by matching its imports and modules against known instrumentation libraries, installing the right modules, and wiring them into the application's real entrypoints. Do not stop after adding dependencies.

Go has two distinct approaches. Default to **code-based library instrumentation**, which is the closest equivalent to the Python skill's workflow and works across ordinary deployments. Use **zero-code instrumentation** only when the user explicitly requests eBPF, compile-time instrumentation, or OpenTelemetry Operator injection; it has different deployment requirements and must not be mixed casually with a manually initialized SDK.

## Required workflow: code-based instrumentation

Complete every step. Preserve the application's existing architecture, dependency-management conventions, and signal scope; if the user asked only for tracing, do not add a metrics or logs pipeline.

### 1. Identify the module and entrypoints

- Find the target `go.mod` and any enclosing `go.work`. If the repository contains multiple plausible applications or modules, confirm scope before editing.
- Inspect `go.mod`, `go.sum`, and the packages under the selected module. Run `go list -json ./...` and `go list -m -json all` from the module directory when possible.
- Make dependencies available using the repository's existing bootstrap flow. Use `go mod download` when needed, but preserve intentional vendoring and workspace configuration.
- Identify HTTP frameworks and routers, gRPC servers/clients, database drivers, caches, queues, cloud SDKs, and outbound HTTP clients actually used by application packages.
- Locate every real process entrypoint (`package main`, `cmd/*`, server constructors, workers, and scheduled jobs). Determine where shared clients, routers, gRPC servers, and database handles are constructed.
- Note existing OpenTelemetry setup and avoid creating a second global provider, exporter, or duplicate middleware.

### 2. Discover matching instrumentation libraries

Run the bundled discovery helper from the target module directory:

```bash
python3 /home/vishva/skills/golang-otel-autoinstrument/scripts/discover_instrumentation.py /path/to/module
```

The JSON report contains:

- `application_imports`: imports made directly by packages in the selected module, including tests.
- `direct_modules`: direct non-standard-library module requirements reported by the Go toolchain.
- `official_contrib_matches`: high-confidence matches derived from `go.mod` paths in the official `open-telemetry/opentelemetry-go-contrib` repository. Prefer these.
- `registry_matches`: lower-confidence ecosystem-registry candidates. Inspect each candidate's repository and package documentation before using it.
- `unmatched_direct_modules`: direct modules with no discovered instrumentation. Report relevant unmatched runtime dependencies rather than silently dropping them.
- `warnings`: discovery failures or degraded fallbacks. Do not describe network-derived results as current if the helper says it used its bundled fallback catalog.

Review the output manually:

- Keep only instrumentation for code paths the application actually uses. A module in `go.mod` is insufficient if no application package imports it.
- Prefer official OpenTelemetry Go contrib modules over third-party alternatives unless the user requests a vendor-specific or specialized span model.
- Check the candidate package's current API and supported versions before editing. Go instrumentation is middleware/wrapping, not Python-style runtime monkey-patching, and call sites differ by library.
- Do not add speculative instrumentation for every transitive module.

### 3. Add the required modules

Use `go get` from the target module for the core trace SDK, OTLP exporter, and each confirmed instrumentation module. Prefer the transport already expected by the deployment:

```bash
go get go.opentelemetry.io/otel \
  go.opentelemetry.io/otel/sdk \
  go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc \
  <each-confirmed-instrumentation-module>
go mod tidy
```

Use `otlptracehttp` instead of `otlptracegrpc` when the existing collector or deployment configuration requires OTLP/HTTP. Do not add both exporters without a concrete need. Let Go resolve mutually compatible versions; do not invent pins from unrelated examples.

### 4. Create one telemetry lifecycle

Add a small application-owned setup package, such as `internal/telemetry`, that:

- Creates the OTLP trace exporter with a context.
- Builds a resource using `resource.Default()` merged with `service.name` only when the application's existing configuration does not already supply it. Prefer standard environment configuration such as `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`, and exporter-specific OTLP variables.
- Creates one `sdktrace.TracerProvider`, normally with `sdktrace.NewBatchSpanProcessor` or `sdktrace.WithBatcher`.
- Registers the provider with `otel.SetTracerProvider` and installs W3C Trace Context plus Baggage propagation with `otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))`.
- Returns an idempotent or single-owner shutdown function and flushes telemetry during graceful process shutdown. Never rely on `defer` in a helper that returns immediately.

Call setup once, early in each real executable process, before constructing instrumented servers or clients. Propagate setup errors according to the application's existing startup policy. Do not hardcode collector endpoints, credentials, or deployment-specific resource attributes.

### 5. Wire each matched library into real code

Inspect the installed package documentation and current signatures. Typical shapes include:

- `net/http` server: wrap the actual root handler with `otelhttp.NewHandler(handler, operation)` before passing it to `http.Server` or `http.Serve`.
- `net/http` client: use `otelhttp.NewTransport(base)` on the application's shared `http.Client`; preserve a non-nil custom transport instead of replacing it blindly. Do not mutate `http.DefaultTransport` globally unless that is already the application's explicit design.
- Gin, Echo, and Gorilla Mux: install `otelgin.Middleware`, `otelecho.Middleware`, or wrap the router with `otelmux.Middleware` at router construction, following the current package API.
- gRPC: use `grpc.StatsHandler(otelgrpc.NewServerHandler())` and `grpc.WithStatsHandler(otelgrpc.NewClientHandler())` at the real server and client constructors. Do not copy deprecated interceptor examples when the current package recommends stats handlers.
- AWS SDK v2: append `otelaws.AppendMiddlewares` through the SDK's API options when constructing the shared config/client.
- Database, Redis, MongoDB, Kafka, and other clients: use the specific wrapper, monitor, hook, or constructor option required by the confirmed library. There is no universal `Instrument()` call in Go.

Avoid duplicate spans: do not layer generic `otelhttp` server wrapping on top of framework middleware for the same request unless the user explicitly wants both span boundaries. Ensure incoming context reaches handlers and outgoing calls use the request/job context rather than `context.Background()`.

### 6. Add trace context to logs only when appropriate

OpenTelemetry Go does not require replacing the application's logger. If structured logging is already present and the user wants trace-log correlation, enrich log records at request/job boundaries with the current valid span context:

```go
sc := trace.SpanContextFromContext(ctx)
if sc.IsValid() {
    // Add trace_id and span_id through the logger's existing structured API.
}
```

Use lowercase `trace_id` and `span_id` unless the application's logging schema specifies other keys. Preserve the existing logger and handler chain; use an official OTel bridge only when the application already uses the corresponding logging API and the bridge's behavior matches the requested signal pipeline.

### 7. Run checks and a smoke test

- Run `gofmt` on changed Go files, then `go mod tidy`.
- Run the repository's existing lint/static checks if configured, plus `go vet ./...` and `go test ./...` when appropriate.
- Run or import each executable far enough to verify provider setup, middleware/client construction, and graceful shutdown compile and execute. An absent collector may produce export connection errors but must not prevent normal startup unless the application intentionally treats it as fatal.
- Inspect the diff for unrelated `go.mod` or `go.sum` churn and duplicate instrumentation.
- Summarize matched dependencies, modules added, wiring locations, unmatched relevant dependencies, signal/export protocol choices, and all check results.

## Explicit zero-code path

Use this path only when the user explicitly asks for zero-code/eBPF/compile-time/Operator instrumentation or source edits are out of scope.

- Verify current support and deployment requirements from official OpenTelemetry documentation before changing deployment files; Go zero-code support and its library/version matrix evolve quickly.
- Treat OpenTelemetry eBPF Instrumentation/OBI or Operator injection as a deployment change, not a `go get` substitute. Confirm the target binary, container/Kubernetes environment, privileges, kernel/runtime compatibility, and OTLP destination.
- If manual spans must correlate with eBPF-generated spans, use the Go Auto SDK behavior documented for the selected agent. **Do not initialize or register a normal global `sdktrace.TracerProvider` in that process**: it conflicts with the Auto SDK provider and breaks correlation.
- Do not also add code-based middleware for libraries already covered by the selected zero-code agent unless the user knowingly accepts duplicate spans.
- Validate using a built binary in the real execution model and verify exported spans, parent-child relationships, and shutdown behavior—not only compilation.
