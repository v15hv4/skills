#!/usr/bin/env python3
"""Discover OpenTelemetry instrumentation packages for a Python app.

Cross-references the app's declared dependencies against two sources:

1. opentelemetry-bootstrap's own library->instrumentation map (authoritative
   for packages in opentelemetry-python-contrib), run against the app's
   *actual installed* environment.
2. The OpenTelemetry ecosystem registry (github.com/open-telemetry/opentelemetry.io,
   data/registry/instrumentation-python-*.yml), which additionally covers
   third-party / GenAI / vector-db instrumentations not in contrib.

Run with a recent stdlib Python (3.11+, for tomllib):
    uv run --python 3.12 discover_instrumentation.py /path/to/app

Prints a JSON report to stdout. Network calls are best-effort: if GitHub is
unreachable, registry_matches will be empty but bootstrap_matches still work.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    print("error: needs Python 3.11+ for tomllib (run via: uv run --python 3.12 ...)", file=sys.stderr)
    raise

GITHUB_API_TREE = (
    "https://api.github.com/repos/open-telemetry/opentelemetry.io/git/trees/main?recursive=1"
)
RAW_BASE = "https://raw.githubusercontent.com/open-telemetry/opentelemetry.io/main/"
BOOTSTRAP_GEN_URL = (
    "https://raw.githubusercontent.com/open-telemetry/opentelemetry-python-contrib/"
    "main/opentelemetry-instrumentation/src/opentelemetry/instrumentation/bootstrap_gen.py"
)


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_declared_dependencies(pyproject_path: Path) -> list[str]:
    data = tomllib.loads(pyproject_path.read_text())
    deps: list[str] = []

    project = data.get("project", {})
    deps.extend(project.get("dependencies", []))
    for group_deps in project.get("optional-dependencies", {}).values():
        deps.extend(group_deps)

    for group_deps in data.get("dependency-groups", {}).values():
        deps.extend(d for d in group_deps if isinstance(d, str))

    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    deps.extend(k for k in poetry_deps if k.lower() != "python")

    names = []
    for spec in deps:
        match = re.match(r"^([A-Za-z0-9._-]+)", spec)
        if match:
            names.append(match.group(1))
    return sorted(set(names))


def fetch(url: str, timeout: int = 15) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError):
        return None


def bootstrap_gen_matches(dep_names: list[str]) -> list[dict]:
    """Match declared deps against contrib's own library->instrumentation map."""
    src = fetch(BOOTSTRAP_GEN_URL)
    if not src:
        return []

    entries = re.findall(
        r'"library":\s*"([^"]+)",\s*"instrumentation":\s*"([^"]+)"', src
    )
    normalized_deps = {normalize(d): d for d in dep_names}

    matches = []
    for library_spec, instrumentation_spec in entries:
        lib_name = re.match(r"^([A-Za-z0-9._-]+)", library_spec.strip())
        if not lib_name:
            continue
        lib_norm = normalize(lib_name.group(1))
        if lib_norm in normalized_deps:
            pkg_name = re.match(r"^([A-Za-z0-9._-]+)", instrumentation_spec.strip())
            matches.append(
                {
                    "dependency": normalized_deps[lib_norm],
                    "instrumentation_package": pkg_name.group(1) if pkg_name else instrumentation_spec,
                    "instrumentation_spec": instrumentation_spec,
                    "source": "bootstrap_gen",
                }
            )
    return matches


def bootstrap_live_requirements(app_dir: Path) -> list[str]:
    """Ask opentelemetry-bootstrap what it sees in the app's *installed* venv.

    Requires the app's deps to already be synced (uv sync). Best-effort: if uv
    or the venv isn't set up, returns [].
    """
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(app_dir),
                "--with",
                "opentelemetry-instrumentation",
                "opentelemetry-bootstrap",
                "-a",
                "requirements",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def registry_candidates() -> list[dict]:
    tree_json = fetch(GITHUB_API_TREE)
    if not tree_json:
        return []
    tree = json.loads(tree_json)
    paths = [
        t["path"]
        for t in tree.get("tree", [])
        if t["path"].startswith("data/registry/instrumentation-python-")
    ]

    candidates = []
    for path in paths:
        slug = path.removeprefix("data/registry/instrumentation-python-").removesuffix(".yml")
        content = fetch(RAW_BASE + path)
        if not content:
            continue

        title_m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
        repo_m = re.search(r"repo:\s*(\S+)", content)
        first_party_m = re.search(r"isFirstParty:\s*(true|false)", content)
        desc_m = re.search(r"description:\s*(.+?)\nauthors:", content, re.DOTALL)

        package_name = None
        if repo_m:
            package_name = repo_m.group(1).rstrip("/").split("/")[-1]

        candidates.append(
            {
                "slug": slug,
                "title": title_m.group(1).strip() if title_m else slug,
                "description": " ".join(desc_m.group(1).split()) if desc_m else "",
                "package_name": package_name,
                "is_first_party": first_party_m.group(1) == "true" if first_party_m else None,
            }
        )
    return candidates


def match_registry(dep_names: list[str], candidates: list[dict]) -> list[dict]:
    matches = []
    for dep in dep_names:
        dep_norm = normalize(dep)
        if not dep_norm:
            continue
        for cand in candidates:
            slug_norm = normalize(cand["slug"])
            if not slug_norm:
                continue
            if dep_norm == slug_norm or slug_norm in dep_norm or dep_norm in slug_norm:
                matches.append(
                    {
                        "dependency": dep,
                        "instrumentation_package": cand["package_name"],
                        "title": cand["title"],
                        "description": cand["description"],
                        "is_first_party": cand["is_first_party"],
                        "source": "registry",
                    }
                )
    return matches


def main() -> None:
    app_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    pyproject_path = app_dir / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"error: no pyproject.toml at {pyproject_path}", file=sys.stderr)
        sys.exit(1)

    dep_names = load_declared_dependencies(pyproject_path)

    bootstrap_matches = bootstrap_gen_matches(dep_names)
    bootstrap_live = bootstrap_live_requirements(app_dir)

    candidates = registry_candidates()
    registry_matches = match_registry(dep_names, candidates)

    covered_deps = {m["dependency"] for m in bootstrap_matches} | {m["dependency"] for m in registry_matches}
    # dedupe registry matches already covered by bootstrap_gen with the same package
    bootstrap_pkgs = {normalize(m["instrumentation_package"]) for m in bootstrap_matches}
    registry_matches = [
        m for m in registry_matches
        if not m["instrumentation_package"] or normalize(m["instrumentation_package"]) not in bootstrap_pkgs
    ]

    report = {
        "app_dir": str(app_dir),
        "declared_dependencies": dep_names,
        "bootstrap_gen_matches": bootstrap_matches,
        "bootstrap_live_requirements": bootstrap_live,
        "registry_matches": registry_matches,
        "unmatched_dependencies": sorted(set(dep_names) - covered_deps),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
