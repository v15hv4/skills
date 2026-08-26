---
name: cyber-audit
description: Run an offensive security audit of a repo or monorepo inside an isolated disposable git worktree with all documentation stripped, applying the owasp-security skill (auto-installed from github.com/agamm/claude-code-owasp if missing) to find exploitable vulnerabilities, then produce a markdown report where each finding has a title, short description, severity (critical/high/medium/low), and concise reproduce steps against a running instance; optionally files one Linear ticket per finding when a Linear project is given. Use when asked to security-audit a codebase, run a cyber audit, pentest-review an app, or audit every service in a monorepo in parallel.
---

# Cyber Audit

Audit a repository's committed code for exploitable vulnerabilities using the `owasp-security`
skill, inside a throwaway git worktree with all documentation deleted, and emit a markdown
report (plus optional Linear tickets). In a monorepo, fan out one subagent per service and run
the audits in parallel.

Pipeline: prerequisites → repo/monorepo detection → temp worktree → strip docs → ingress
mapping → audit → report → optional Linear tickets → cleanup.

## Hard rules

- `rm -rf` runs ONLY inside the temporary worktree. Never delete anything under the real
  checkout. Double-check `$PWD` before every destructive command.
- The only writes outside the worktree are the report file(s) at the repo root and Linear
  issues. Never edit application code.
- Static analysis only. Do not exploit, fuzz, or send traffic to any system. Repro steps are
  instructions for a human with a legitimately running instance.
- Every reported finding must pass the triage gates in Step 4. A pattern match is not a
  vulnerability.
- Always clean up the worktree, even when the audit fails partway.

## Step 0 — Prerequisites

1. Confirm the target is a git repo: `git rev-parse --is-inside-work-tree`. If not, stop and
   tell the user.
2. Capture context:
   ```bash
   REPO_ROOT=$(git rev-parse --show-toplevel)
   HEAD_SHA=$(git rev-parse HEAD)
   ```
3. If `git status --porcelain` is not empty, warn the user: the worktree checks out committed
   `HEAD` only, so uncommitted changes will NOT be audited. Continue unless they object.
4. Ensure the `owasp-security` skill is available:
   - If it is registered in this session (loadable via the skill tool), use it.
   - Otherwise locate it on disk — check `~/.claude/skills/owasp-security/SKILL.md`,
     `~/.agents/skills/owasp-security/SKILL.md`, and `.opencode/skill*/owasp-security/SKILL.md`
     in both the project and home config dirs.
   - If still missing, install it:
     ```bash
     npx degit agamm/claude-code-owasp/.claude/skills/owasp-security ~/.claude/skills/owasp-security
     ```
     Fallback without `degit`:
     ```bash
     git clone --depth 1 https://github.com/agamm/claude-code-owasp.git "$TMPDIR/claude-code-owasp"
     mkdir -p ~/.claude/skills && cp -r "$TMPDIR/claude-code-owasp/.claude/skills/owasp-security" ~/.claude/skills/
     ```
   - Either way, READ the `SKILL.md` straight from disk and follow it — a freshly installed
     skill is not registered in the running session. Set `OWASP_SKILL` to its folder. Load
     `reference/languages.md` for each language found in Step 4; pull
     `reference/owasp-report.md` on demand for deep dives.

## Step 1 — Repo or monorepo?

Treat the target as a monorepo when several independently deployable applications exist:
multiple manifests (`package.json`, `go.mod`, `pyproject.toml`, `Cargo.toml`, `pom.xml`,
`build.gradle*`, `composer.json`, `Gemfile`) in sibling directories; `apps/`, `services/`,
`packages/`, `api/`, `workers/` layouts; workspace markers (`pnpm-workspace.yaml`, turbo/nx/
lerna/bazel configs); or a docker-compose file with multiple build contexts. A single-root
manifest with workspaces counts as a monorepo — each runnable workspace app is a service.

Shared libraries and packages that nothing deploys on their own are NOT services; fold them
into whichever service imports them. If the split is ambiguous, show the user your candidate
service list and confirm before proceeding.

## Step 2 — Temporary worktree

```bash
AUDIT_TMP=$(mktemp -d /tmp/cyber-audit-XXXXXX)
git -C "$REPO_ROOT" worktree add --detach "$AUDIT_TMP/wt" HEAD
WT="$AUDIT_TMP/wt"
```

One worktree covers the whole repo (all services in a monorepo). It contains committed code
only — gitignored and untracked files are absent by design.

## Step 3 — Strip documentation (inside `$WT` ONLY)

Docs are removed so the audit judges code, not prose — documentation routinely asserts
security controls that do not exist in the implementation, and it buries real signals.

```bash
cd "$WT" || exit 1   # verify $PWD prints the worktree path before continuing

find . -type d \( -name docs -o -name doc -o -name openwiki -o -name wiki \) -prune -exec rm -rf {} +
find . -type f \( \
  -name 'AGENTS.md'  -o -name 'CLAUDE.md'      -o -name 'README.md'       -o \
  -name 'CONTRIBUTING.md' -o -name 'CHANGELOG.md' -o -name 'SECURITY.md' -o \
  -name 'CODE_OF_CONDUCT.md' -o -name 'AUTHORS.md' -o -name 'GOVERNANCE.md' -o \
  -name 'SUPPORT.md' -o -name 'ARCHITECTURE.md' \) -delete
```

Then sweep remaining `*.md`: delete every file that is clearly prose documentation (per-package
READMEs, design notes, tutorials). KEEP markdown that code consumes — test fixtures, prompt
templates loaded at runtime, API examples referenced by tests. When unsure, keep it.

## Step 4 — Audit each service

Work from `$OWASP_SKILL/SKILL.md` methodology. For each service (its subtree under `$WT`):

1. Map the ingress and exposed surface before judging reachability. Inspect committed deployment
   and network configuration alongside the application: Kubernetes `Ingress`/`Gateway`/
   `HTTPRoute`/`Service`/NetworkPolicy resources; Docker Compose port mappings; Dockerfiles;
   Terraform and cloud load-balancer, API-gateway, DNS, firewall/security-group, and private
   endpoint resources; reverse-proxy configuration; and Tailscale/Headscale configuration,
   tags, ACLs, and Funnel settings. Record the evidence used and classify each service as:
   - **public** — internet-reachable ingress exists, or the repository provides insufficient
     evidence to establish private-only access;
   - **private/internal** — every evidenced ingress is restricted to a private network,
     cluster/VPC, VPN, or org identity boundary; or
   - **no network ingress evidenced** — no inbound listener is evidenced (for example, a worker
     or CLI). Do not treat missing infrastructure files alone as proof of this classification.
   Treat a Tailscale-only listener as private/internal only when no Tailscale Funnel, public
   reverse proxy, load balancer, or other internet-facing route is present. If evidence conflicts
   or is incomplete, classify it as **public** for triage and state that the exposure is unknown
   in the report.
2. Map the application attack surface: HTTP routes/controllers, GraphQL resolvers, WebSocket
   handlers, RPC endpoints, queue consumers, cron jobs, CLI entrypoints, admin panels, webhook
   receivers. Note auth middleware placement and what it skips, and connect each network-facing
   handler to its ingress classification where possible.
3. Trace untrusted input to sinks: SQL/NoSQL queries, shell execution, `eval`/dynamic code,
   deserialization, file read/write/path joins, URL redirects, outbound HTTP (SSRF), template
   rendering, HTML/JS output, and — where present — LLM prompts and tool calls.
4. Check cross-cutting controls: authentication and session management, object-level
   authorization (IDOR), privilege boundaries, cryptography choices, secret handling, CORS and
   security headers, error responses, dependency manifests for known-risky pins, and infra
   configs (Dockerfile, k8s manifests, terraform) when present.
5. Apply the owasp-security triage gates before reporting ANYTHING:
   - Is the input genuinely attacker-controlled (request param, header, cookie, upload,
     webhook, queue message, third-party response)?
   - Does it reach the sink with no validation/allowlist/ORM/auth middleware in between?
   - What is the blast radius — who can trigger it and what crosses a trust boundary?
   - For a service classified **private/internal**, assume trusted actors within the organization
     can reach its private ingress. Therefore, do not report or score a finding whose only
     realistic adversary is an unauthenticated internet user directly reaching that private
     endpoint. Relax public-edge-only concerns accordingly (for example, missing public rate
     limiting or an unauthenticated route that is harmless under the stated internal-trust
     assumption).
   - This exception is narrow: still report vulnerabilities reachable by a compromised internal
     account or workload, an authorized but low-privilege user, a tenant, a forged/third-party
     webhook or queue message, SSRF, a supply-chain/pivot path, or any route that crosses a
     meaningful trust or privilege boundary. Still report internet-reachable paths even when the
     backend itself is private.
6. Severity follows exploitability, not pattern popularity. Mark findings you could not fully
   confirm as `theoretical` in the description; theoretical findings are excluded from Linear
   filing.

## Step 5 — Markdown report

Write reports OUTSIDE the worktree (it gets deleted): single repo → `$REPO_ROOT/cyber-audit-report.md`;
monorepo → one `$REPO_ROOT/cyber-audit/<service>.md` per service, merged by the parent into
`$REPO_ROOT/cyber-audit-report.md`.

Report skeleton:

```markdown
# Cyber Audit — <repo or service name>

- Commit audited: <HEAD_SHA>
- Date: <YYYY-MM-DD>
- Method: owasp-security skill (Top 10:2025, ASVS 5.0, LLM Top 10, Agentic AI)
- Scope: <services / paths covered>
- Ingress classification: <public | private/internal | no network ingress evidenced>, with
  <concise evidence and any uncertainty>

| Severity | Count |
|----------|-------|
| Critical | N     |

## Findings
(sorted critical → low; one section per finding, template below)
```

Per-finding template — exactly these four elements:

```markdown
### <Title>

<Short description: the flaw, the attacker-controlled input, the sink, and the impact.>

**Severity:** critical | high | medium | low
**Location:** `path/to/file.ext:LINE`

**Reproduce (against a running instance):**
1. <concrete step — e.g. curl command with full request>
2. <next step>
3. <observed result that proves the vulnerability>
```

## Step 6 — Optional Linear tickets

Only when BOTH hold: the user supplied a Linear project, and Linear MCP tools are available.
Otherwise skip silently and note it in the final summary.

1. Resolve the project with `linear_get_project`; take its first team unless the user named
   one. Ask when several teams are plausible.
2. Per finding, dedup first: search `linear_list_issues` (and any needed pagination) across
   **all states** in the supplied project, using the finding title and affected service/path to
   identify a materially similar security issue. Skip creation if one already exists, regardless
   of whether it is triage, backlog, in progress, completed, canceled, or otherwise closed; note
   the existing issue identifier/URL in the report. Do not rely on an open-only filter.
3. Create with `linear_save_issue`:
   - Title: `<service> <finding title>` in monorepo mode (e.g. `[billing] RCE in pdf export`),
     plain title in single-repo mode.
   - Body: description, severity, `Location:` file:line, reproduce steps, audited commit SHA.
   - Status: resolve and set the owning team's existing `triage` workflow state (never leave a
     newly created audit finding in `backlog`). If that team has no `triage` state, stop and ask
     the user which state to use; do not create a replacement state.
   - Priority: critical→1 (Urgent), high→2 (High), medium→3 (Medium), low→4 (Low).
   - Labels: reuse an existing `security` label if one exists; never invent labels.
4. Append each created issue identifier/URL to the report section for that finding.

## Step 7 — Monorepo: parallel subagents

The PARENT does Steps 0–3 once (one worktree, one doc-strip for the whole tree), creates
`$REPO_ROOT/cyber-audit/`, then spawns one `general` subagent per service — all `task` calls
in a single message so they run concurrently (batch into groups of ≤6 if there are more).
Each subagent owns its service's audit AND its report/ticket creation.

Subagent prompt template (fill the placeholders):

```text
You are a security auditor. STATIC ANALYSIS ONLY — do not modify any file, do not run the
app, do not send network traffic.

Service: <name> — audit ONLY the subtree <WT>/<service-path>.
First read <OWASP_SKILL>/SKILL.md and follow its methodology (triage gates included);
consult <OWASP_SKILL>/reference/languages.md for the languages present.

Do: first map ingress from committed app and deployment/network configuration (including k8s
Ingress/Gateway/Service, compose ports, reverse proxies, cloud LB/API-gateway/DNS/firewall/
private-endpoint Terraform, and Tailscale ACL/Funnel settings). Classify ingress as public,
private/internal, or no network ingress evidenced; when uncertain, use public and note the
uncertainty. Then map
the application attack surface and trace attacker-controlled input to sinks; check auth/session/
authorization/crypto/secrets/headers/dependencies/infra-config. For private/internal ingress,
assume trusted org actors can directly reach it and relax only findings whose sole adversary is
an unauthenticated internet user. Still report privilege-boundary, compromised-workload,
low-privilege-user, webhook/queue, SSRF, supply-chain, pivot, and any publicly reachable path.
Severity by exploitability; mark unconfirmed findings "theoretical".

Deliverable 1 — write <REPO_ROOT>/cyber-audit/<name>.md using the report skeleton (including
the ingress classification and evidence) and the per-finding template (title, short description,
severity, Location file:line, numbered reproduce steps against a running instance), findings
sorted critical→low.

Deliverable 2 — Linear (only if instructed below): for each non-theoretical finding call
linear_save_issue on project "<project>" / team "<team>", title "[<name>] <finding title>",
status `triage` (resolve the team's existing workflow state; if absent, ask rather than using
`backlog`), priority critical→1/high→2/medium→3/low→4, body with description, location,
repro steps, and commit <HEAD_SHA>. Before creating, search the entire supplied project across
all states and pagination for a materially similar finding (title plus affected service/path);
skip it if one exists in any state and record that existing issue identifier/URL. Collect
identifiers.

Return: counts by severity, the list of finding titles, and all created Linear issue IDs.
```

When subagents finish, the parent merges the per-service files into
`cyber-audit-report.md` (global summary table first, then each service's findings), and
prints: report path, total findings by severity, and every Linear issue created.

## Cleanup

Always finish with:

```bash
git -C "$REPO_ROOT" worktree remove --force "$WT"
rm -rf "$AUDIT_TMP"
git -C "$REPO_ROOT" worktree prune
```

Run cleanup even when earlier steps failed. The report lives at the repo root and survives.
