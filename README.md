# cascade-review

> AI-powered code reviewer that catches what others miss.  
> Build-breaker prevention. SonarQube-grade checks. Blast radius analysis.  
> Works with 8 LLM providers. **Zero cost to start.**

[![PyPI](https://img.shields.io/pypi/v/cascade-review)](https://pypi.org/project/cascade-review/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

```bash
pip install cascade-review
git diff | cascade
```

---

## What it does

Most AI code reviewers give you comments. Cascade gives you **impact** — and catches builds that would break in CI before you push.

```
──────────────────────────────────────────────────────────
  cascade-review  github.com/vyshakhgnair/cascade-review

  CHANGE SUMMARY
  Added token refresh logic to authenticate_user(). Extends
  session handling with a new remember_me parameter.
  Type: LOGIC  ⚠ Auth path changed — affects all logged-in users

  ⛔ SECRETS DETECTED
  CRITICAL  [API Key] in config/settings.py
  api_key = "sk-proj-xxxxxxxxxxxxxxxxxxx..."

  REGRESSION RISK
  8/10  ████████░░  CRITICAL
  › Security-sensitive file: auth/login.py
  › 3 files depend on authenticate_user()

  BLAST RADIUS
  Changed: authenticate_user, refresh_token
  Risk: HIGH
  → routes/dashboard.py   uses authenticate_user
  → middleware/guard.py   uses authenticate_user
  → api/v2/token.py       uses refresh_token

  SONARQUBE SIMULATION
  CRITICAL   S2077  SQL built from user input — use parameterised queries  [30min]
  MAJOR      S3776  Cognitive complexity 18 exceeds threshold of 15        [1h]
  MINOR      S1481  Variable "tmp" assigned but never used                 [2min]

  🚧 BUILD BREAKERS
  HIGH       [MISSING_DEP]      'redis' imported but not in requirements.txt
  CRITICAL   [CASE_SENSITIVITY] Import 'Utils' — actual file is 'utils.py' (breaks on Linux CI)
  WARNING    [LOCKFILE_DRIFT]   package.json changed but lock file not updated
──────────────────────────────────────────────────────────
```

---

## Why Cascade is different

| Feature | Cascade | CodeRabbit | PR-Agent | SonarQube |
|---|---|---|---|---|
| **Build-breaker prevention** | **✅ 8 checks** | ❌ | ❌ | ❌ |
| **Code redaction** (privacy) | **✅** | ❌ | ❌ | n/a |
| Blast radius analysis | ✅ | ❌ | ❌ | ❌ |
| SonarQube rule simulation | ✅ | ❌ | ❌ | ✅ paid |
| Regression risk score | ✅ | ❌ | ❌ | ❌ |
| AI-generated code detection | ✅ | ❌ | ❌ | ❌ |
| Architecture drift check | ✅ | ❌ | ❌ | ❌ |
| Version conflict detection | ✅ | ❌ | ❌ | ❌ |
| Review policy as code | ✅ | ✅ | ❌ | ✅ |
| Works fully offline | ✅ | ❌ | ❌ | ❌ |
| Pre-commit hook | ✅ | ❌ | ❌ | ❌ |
| Audit trail (SOC 2) | ✅ | ❌ | ❌ | ✅ |
| Cost | **$0** | $24/mo | Self-host | Enterprise |
| Supports 8 LLM providers | ✅ | ❌ | Partial | ❌ |

**Cascade catches builds that would break in CI — no other code reviewer does this.**

---

## Quick start

```bash
pip install cascade-review

# Review current changes (static only, no API key needed)
git diff | cascade --no-llm

# Review staged changes
cascade --staged

# Full review with LLM (free with Groq)
export GROQ_API_KEY=your-key-here
git diff | cascade

# Use a specific provider
cascade --provider anthropic --model claude-sonnet-4-6

# Output as markdown (for PR comments)
git diff | cascade --output markdown

# HTML dashboard report
git diff | cascade --output html > report.html

# Privacy mode — redact code before sending to LLM
git diff | cascade --redact

# CI mode — fail if critical findings exist
git diff | cascade --no-llm --severity-gate high
```

---

## Build-breaker prevention

Cascade's unique feature — catches things that pass code review but **explode in CI**:

| Check | What it catches |
|---|---|
| `MISSING_DEP` | Imported package not in requirements.txt / package.json |
| `DEV_IN_PROD` | devDependency used in production code |
| `CASE_SENSITIVITY` | File imports that work on Mac/Windows but break on Linux CI |
| `DELETED_SYMBOL` | Function/class removed but still imported elsewhere |
| `PLATFORM_PATH` | Hardcoded `C:\` or `/Users/` paths |
| `LOCKFILE_DRIFT` | package.json changed but lock file not updated |
| `LARGE_FILE` | Binary or data file accidentally committed |
| `MISSING_ENV_VAR` | Env var used in code but not in .env.example |

---

## Code redaction (privacy)

Don't trust your LLM provider with proprietary code? Use `--redact`:

```bash
# Before redaction:
api_key = "sk-prod-abc123"
price = 99.99

# What the LLM sees:
api_key = "STR_1"
price = NUM_2
```

Structure is preserved for accurate review. Values never leave your machine.

---

## Supported providers

```bash
cascade --list-providers   # See all providers and their status
```

| Provider | Free tier | Privacy | Notes |
|---|---|---|---|
| **Ollama** | ✅ Free (local) | ✅ Local | Offline, private, no quota |
| **Groq** | ✅ 30K TPM | ⚠ Check ToS | Fastest cloud inference |
| **OpenRouter** | ✅ 29 free models | ⚠ Check ToS | Frontier models at no cost |
| **DeepSeek** | ✅ Free tier | ⚠ Check ToS | Strong reasoning |
| **Gemini** | ✅ Free tier | ⚠ Check ToS | Gemini Flash / Pro |
| **Mistral** | ✅ Free tier | ✅ No-train | Fast, European |
| **Anthropic** | Paid | ✅ No-train | Claude Sonnet / Opus |
| **OpenAI** | Paid | ✅ No-train | GPT-4o, o1 |

Privacy labels: **local** = nothing leaves your machine, **no-train** = provider won't train on your inputs, **check ToS** = free tier may use inputs for training.

Cascade warns you when using providers with unclear privacy policies.

---

## Configuration

```bash
cascade --init   # Creates .cascade.yml in your repo
```

`.cascade.yml`:

```yaml
models:
  local:
    provider: ollama
    model: qwen2.5-coder:3b

  mid:
    provider: groq
    model: llama-3.3-70b-versatile
    api_key_env: GROQ_API_KEY

  frontier:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY

routing:
  local_max_lines: 50    # < 50 lines → local model
  mid_max_lines: 200     # 50-200 lines → mid tier
  force_tier: auto       # or: local / mid / frontier

review:
  severity_threshold: warning
  exclude: [migrations/, vendor/, node_modules/]
```

### Team config inheritance (monorepos)

Place a root `.cascade.yml` at the repo root, then override per-package:

```
my-monorepo/
  .cascade.yml           ← root config (shared settings)
  packages/
    api/
      .cascade.yml       ← overrides for API package
    frontend/
      .cascade.yml       ← overrides for frontend
```

Package configs deep-merge with root — you only override what's different.

---

## Review policy as code

Create `.cascade-rules.yml` to enforce team standards:

```yaml
rules:
  - name: no-console-log
    message: "Remove console.log before merging"
    files: "\\.(js|ts|tsx)$"
    pattern: "console\\.log\\("
    severity: WARNING

  - name: no-debugger
    message: "Debugger statement left in code"
    pattern: "\\bdebugger\\b"
    severity: HIGH

  - name: no-axios-in-services
    message: "Use the shared HTTP client, not raw axios"
    files: "services/"
    forbidden_imports: ["axios"]
    severity: WARNING

  - name: max-file-size
    message: "File too large — consider splitting"
    max_lines: 500
    severity: WARNING

  - name: tests-required
    message: "Test file should include at least one assertion"
    files: "(test_|spec\\.|__test)"
    require: "(assert|expect|should)"
    severity: HIGH
```

See [`examples/cascade-rules.yml`](examples/cascade-rules.yml) for more.

---

## Pre-commit hook

```bash
cascade --hook install     # Install pre-commit hook
cascade --hook uninstall   # Remove it
```

Runs static analysis on staged changes before every commit. Blocks commits with high-severity findings.

---

## Audit trail (SOC 2)

```bash
git diff | cascade --audit                          # Log to .cascade/audit.jsonl
git diff | cascade --audit --audit-path logs/reviews.jsonl  # Custom path
```

Every review is logged as a JSON line:

```json
{
  "timestamp": "2026-06-25T18:19:08Z",
  "version": "0.2.0",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "redacted": false,
  "files_reviewed": ["auth/login.py"],
  "findings": {"secrets": 0, "sonar": 3, "build_breakers": 1, "bugs": 0},
  "severities": {"CRITICAL": 1, "MAJOR": 2},
  "regression_risk": {"score": 6, "level": "HIGH"}
}
```

---

## CI / GitHub Action

```yaml
# .github/workflows/cascade.yml
name: Cascade Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
      security-events: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: vyshakhgnair/cascade-review@v1
        with:
          groq_api_key: ${{ secrets.GROQ_API_KEY }}
          output_format: markdown
          severity_gate: high
          fail_on_secrets: true
```

Add `GROQ_API_KEY` to repo secrets (free at [console.groq.com](https://console.groq.com)).

### Other CI platforms

- [GitLab CI](examples/gitlab-ci.yml)
- [Bitbucket Pipelines](examples/bitbucket-pipelines.yml)
- [Azure DevOps](examples/azure-pipelines.yml)

---

## Output formats

| Format | Flag | Use case |
|---|---|---|
| Terminal | `--output terminal` | Local development (default) |
| Markdown | `--output markdown` | PR comments |
| HTML | `--output html` | Shareable dashboard report |
| SARIF | `--output sarif` | GitHub Security tab |
| JSON | `--output json` | Programmatic consumption |

---

## Smart routing

```
< 50 lines   → local Ollama 3B    (instant, private, zero quota)
50–200 lines → Groq 70B           (fast, free tier)
200+ lines   → OpenRouter/Claude  (full context, deepest reasoning)
```

Auto-fallback when quotas run out. Override anytime: `cascade --tier frontier`

---

## What Cascade checks

**Static analysis — instant, works offline, no API key:**
- SonarQube rule simulation (Python + JS/TS — S1192, S2077, S3776, S1481, S106 and more)
- Secret / credential detection (15+ patterns — API keys, AWS, Stripe, GitHub, SSH keys)
- Blast radius — which files break if this change fails
- Regression risk score (1–10)
- Architecture drift (naming, layer violations, broad exceptions, god classes, circular imports)
- Build-breaker prevention (8 checks)
- Version conflict detection (cross-workspace / monorepo)
- Review policy enforcement (.cascade-rules.yml)

**LLM analysis — requires a model:**
- Plain English change summary (LOGIC / REFACTOR / FEATURE / BUGFIX / CONFIG / TEST / DOCS)
- Bug and logic error detection
- AI-generated code detection
- Fix suggestions with effort estimates

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Clean — no blocking findings |
| `1` | Error — could not parse diff |
| `2` | Secrets detected |
| `3` | Severity gate failed |

---

## All CLI flags

```
cascade --version                    # Show version
cascade --staged                     # Review staged changes only
cascade --no-llm                     # Static analysis only
cascade --redact                     # Strip literals before sending to LLM
cascade --provider groq              # Override LLM provider
cascade --model llama-3.3-70b        # Override model
cascade --tier frontier              # Force model tier
cascade --output html                # terminal / markdown / sarif / json / html
cascade --severity-gate high         # Fail if findings >= severity
cascade --audit                      # Write audit trail
cascade --audit-path path/log.jsonl  # Custom audit log path
cascade --hook install               # Install pre-commit hook
cascade --hook uninstall             # Remove pre-commit hook
cascade --list-providers             # Show providers and key status
cascade --init                       # Create .cascade.yml
```

---

## Contributing

```bash
git clone https://github.com/vyshakhgnair/cascade-review
cd cascade-review
pip install -e ".[dev]"
pytest
```

---

## License

MIT — use it, fork it, build on it.

---

*Built by [Vyshakh G Nair](https://github.com/vyshakhgnair) — [cascade-review](https://github.com/vyshakhgnair/cascade-review)*
