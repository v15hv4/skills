#!/usr/bin/env python3
"""Discover OpenTelemetry instrumentation candidates for a Go module.

Combine application imports from `go list` with the official
opentelemetry-go-contrib repository tree and the OpenTelemetry ecosystem
registry. Network discovery is best-effort; a small built-in contrib catalog
keeps common matches useful offline. Results are candidates, not permission to
install every match.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CONTRIB_TREE_URL = (
    "https://api.github.com/repos/open-telemetry/"
    "opentelemetry-go-contrib/git/trees/main?recursive=1"
)
REGISTRY_TREE_URL = (
    "https://api.github.com/repos/open-telemetry/"
    "opentelemetry.io/git/trees/main?recursive=1"
)
REGISTRY_RAW_BASE = (
    "https://raw.githubusercontent.com/open-telemetry/opentelemetry.io/main/"
)

# Remote contrib discovery supersedes this fallback when GitHub is reachable.
FALLBACK_CATALOG = {
    "github.com/aws/aws-sdk-go-v2": "go.opentelemetry.io/contrib/instrumentation/github.com/aws/aws-sdk-go-v2/otelaws",
    "github.com/gin-gonic/gin": "go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin",
    "github.com/gorilla/mux": "go.opentelemetry.io/contrib/instrumentation/github.com/gorilla/mux/otelmux",
    "github.com/labstack/echo": "go.opentelemetry.io/contrib/instrumentation/github.com/labstack/echo/otelecho",
    "github.com/segmentio/kafka-go": "go.opentelemetry.io/contrib/instrumentation/github.com/segmentio/kafka-go/otelkafka",
    "go.mongodb.org/mongo-driver": "go.opentelemetry.io/contrib/instrumentation/go.mongodb.org/mongo-driver/mongo/otelmongo",
    "google.golang.org/grpc": "go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc",
    "net/http": "go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp",
}


def fetch(url: str, timeout: int = 20) -> str | None:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "codex-otel-discovery",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except (OSError, TimeoutError, urllib.error.URLError):
        return None


def decode_json_stream(raw: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    offset = 0
    values: list[dict[str, Any]] = []
    while offset < len(raw):
        while offset < len(raw) and raw[offset].isspace():
            offset += 1
        if offset >= len(raw):
            break
        value, offset = decoder.raw_decode(raw, offset)
        if isinstance(value, dict):
            values.append(value)
    return values


def run_go_json(
    app_dir: Path, *args: str
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        with tempfile.TemporaryDirectory(prefix="otel-go-build-cache-") as cache_dir:
            environment = os.environ.copy()
            environment["GOCACHE"] = cache_dir
            result = subprocess.run(
                ["go", *args],
                cwd=app_dir,
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        return [], f"go {' '.join(args)} failed: {error}"
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        message = detail[-1] if detail else "unknown error"
        return [], f"go {' '.join(args)} failed: {message}"
    try:
        return decode_json_stream(result.stdout), None
    except json.JSONDecodeError as error:
        return [], f"could not parse go {' '.join(args)} output: {error}"


def application_imports(app_dir: Path) -> tuple[list[str], str | None]:
    packages, warning = run_go_json(
        app_dir, "list", "-buildvcs=false", "-json", "./..."
    )
    imports: set[str] = set()
    for package in packages:
        for field in ("Imports", "TestImports", "XTestImports"):
            imports.update(
                item for item in package.get(field, []) if isinstance(item, str)
            )
    return sorted(imports), warning


def direct_modules(app_dir: Path) -> tuple[list[str], str | None]:
    modules, warning = run_go_json(app_dir, "list", "-m", "-json", "all")
    direct = {
        module["Path"]
        for module in modules
        if module.get("Path")
        and not module.get("Main", False)
        and not module.get("Indirect", False)
    }
    return sorted(direct), warning


def target_from_contrib_dir(directory: str) -> str | None:
    prefix = "instrumentation/"
    if not directory.startswith(prefix):
        return None
    relative = directory.removeprefix(prefix)
    parts = relative.split("/")
    if len(parts) > 1 and parts[-1].startswith("otel"):
        return "/".join(parts[:-1])
    if relative in {"host", "runtime"}:
        return relative
    return None


def remote_contrib_catalog() -> dict[str, str] | None:
    raw = fetch(CONTRIB_TREE_URL)
    if not raw:
        return None
    try:
        tree = json.loads(raw).get("tree", [])
    except json.JSONDecodeError:
        return None
    catalog: dict[str, str] = {}
    for item in tree:
        path = item.get("path", "")
        if item.get("type") != "blob" or not path.endswith("/go.mod"):
            continue
        directory = path.removesuffix("/go.mod")
        target = target_from_contrib_dir(directory)
        if target:
            catalog[target] = f"go.opentelemetry.io/contrib/{directory}"
    return catalog or None


def imported(imports: list[str], target: str) -> bool:
    return any(path == target or path.startswith(target + "/") for path in imports)


def contrib_matches(
    imports: list[str], catalog: dict[str, str], source: str
) -> list[dict[str, str]]:
    return [
        {
            "target_import": target,
            "instrumentation_module": module,
            "source": source,
        }
        for target, module in sorted(catalog.items())
        if imported(imports, target)
    ]


def registry_entries() -> list[dict[str, str]] | None:
    raw = fetch(REGISTRY_TREE_URL)
    if not raw:
        return None
    try:
        tree = json.loads(raw).get("tree", [])
    except json.JSONDecodeError:
        return None

    entries: list[dict[str, str]] = []
    for item in tree:
        path = item.get("path", "")
        if not re.fullmatch(r"data/registry/instrumentation-go-.+\.ya?ml", path):
            continue
        content = fetch(REGISTRY_RAW_BASE + path)
        if not content:
            continue
        title_match = re.search(
            r"^title:\s*[\"']?(.+?)[\"']?\s*$", content, re.MULTILINE
        )
        repo_match = re.search(
            r"^\s*repo:\s*[\"']?(\S+?)[\"']?\s*$", content, re.MULTILINE
        )
        slug = Path(path).stem.removeprefix("instrumentation-go-")
        entries.append(
            {
                "slug": slug,
                "title": title_match.group(1) if title_match else slug,
                "repository": repo_match.group(1) if repo_match else "",
                "registry_source": REGISTRY_RAW_BASE + path,
            }
        )
    return entries


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def match_registry(
    imports: list[str], modules: list[str], entries: list[dict[str, str]]
) -> list[dict[str, str]]:
    candidates = sorted(set(imports) | set(modules))
    matches: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for dependency in candidates:
        components = {
            normalize(part) for part in dependency.split("/") if len(part) >= 3
        }
        for entry in entries:
            slug = normalize(entry["slug"])
            if len(slug) < 4 or slug not in components:
                continue
            key = (dependency, entry["registry_source"])
            if key not in seen:
                seen.add(key)
                matches.append(
                    {"dependency": dependency, **entry, "source": "registry"}
                )
    return matches


def main() -> None:
    app_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not (app_dir / "go.mod").is_file():
        print(f"error: no go.mod at {app_dir / 'go.mod'}", file=sys.stderr)
        raise SystemExit(1)

    imports, imports_warning = application_imports(app_dir)
    modules, modules_warning = direct_modules(app_dir)
    warnings = [
        warning for warning in (imports_warning, modules_warning) if warning
    ]

    catalog = remote_contrib_catalog()
    if catalog is None:
        catalog = FALLBACK_CATALOG
        catalog_source = "bundled_fallback"
        warnings.append(
            "GitHub contrib discovery unavailable; used bundled fallback catalog"
        )
    else:
        catalog_source = "opentelemetry-go-contrib"

    official_matches = contrib_matches(imports, catalog, catalog_source)
    registry = registry_entries()
    if registry is None:
        registry_matches: list[dict[str, str]] = []
        warnings.append("OpenTelemetry ecosystem registry discovery unavailable")
    else:
        registry_matches = match_registry(imports, modules, registry)

    covered_targets = {match["target_import"] for match in official_matches}
    matched_modules = {
        module
        for module in modules
        if any(
            module == target
            or module.startswith(target + "/")
            or target.startswith(module + "/")
            for target in covered_targets
        )
    }
    matched_modules.update(
        match["dependency"]
        for match in registry_matches
        if match["dependency"] in modules
    )

    report = {
        "module_dir": str(app_dir),
        "application_imports": imports,
        "direct_modules": modules,
        "official_contrib_matches": official_matches,
        "registry_matches": registry_matches,
        "unmatched_direct_modules": sorted(set(modules) - matched_modules),
        "warnings": warnings,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
