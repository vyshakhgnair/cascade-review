# cascade-review

> AI-powered code reviewer that actually understands your codebase.  
> SonarQube-grade checks. Blast radius analysis. Works with any LLM provider.  
> **Zero cost to start.**

```bash
pip install cascade-review
git diff | cascade
```

---

## What it does

Most AI code reviewers give you comments. Cascade gives you **impact**.

```
──────────────────────────────────────────────────────────
  cascade-review

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
  › Functions modified: authenticate_user, refresh_token

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
──────────────────────────────────────────────────────────
```

---

## Why Cascade is different

| Feature | Cascade | CodeRabbit | PR-Agent | SonarQube |
|---|---|---|---|---|
| SonarQube rule simulation | ✅ | ❌ | ❌ | ✅ paid |
| Blast radius analysis | ✅ | ❌ | ❌ | ❌ |
| Regression risk score | ✅ | ❌ | ❌ | ❌ |
| AI-generated code detection | ✅ | ❌ | ❌ | ❌ |
| Architecture drift check | ✅ | ❌ | ❌ | ❌ |
| Works offline (local model) | ✅ | ❌ | ❌ | ❌ |
| Cost | **₹0** | $15/mo | Self-host | Enterprise |
| Supports any LLM provider | ✅ | ❌ | Partial | ❌ |

---

## Quick start

```bash
pip install cascade-review

# Review current changes
git diff | cascade

# Review staged changes
cascade --staged

# Use a specific provider
cascade --provider anthropic --model claude-sonnet-4-6

# Static analysis only (no API key needed)
git diff | cascade --no-llm

# Output as GitHub PR comment
git diff | cascade --output markdown
```

---

## Supported providers

| Provider | Free tier | Notes |
|---|---|---|
| **Ollama** | ✅ Fully free (local) | Offline, private, no quota |
| **Groq** | ✅ 30K TPM | Fast cloud inference |
| **OpenRouter** | ✅ 29 free models | Frontier models at no cost |
| **DeepSeek** | ✅ Free tier | Claude-comparable quality |
| **Anthropic** | Paid | Claude Sonnet / Opus |
| **OpenAI** | Paid | GPT-4o, o1 |
| **Gemini** | Free tier | Gemini Flash / Pro |
| **Mistral** | Free tier | Fast, European |

---

## Configuration

```bash
cascade --init   # auto-detects setup and writes .cascade.yml
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
    provider: anthropic          # openai / gemini / deepseek / openrouter
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY

routing:
  local_max_lines: 50
  mid_max_lines: 200
  force_tier: auto

review:
  severity_threshold: warning
  exclude: [migrations/, vendor/, node_modules/]
```

---

## GitHub Action

```yaml
# .github/workflows/cascade.yml
name: Cascade Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: vyshakhgnair/cascade-review@v1
        with:
          groq_api_key: ${{ secrets.GROQ_API_KEY }}
          output_format: markdown
          fail_on_secrets: true
```

Add `GROQ_API_KEY` to repo secrets (free at [console.groq.com](https://console.groq.com)). Every PR gets reviewed automatically.

---

## What Cascade checks

**Static analysis — instant, works offline, no API key:**
- SonarQube rule simulation (S1192, S2077, S3776, S1481, S112 and more)
- Secret / credential detection (API keys, passwords, tokens)
- Blast radius — which files break if this change fails
- Regression risk score (1–10)
- Architecture drift (naming, layer violations, broad exceptions)

**LLM analysis — requires a model:**
- Plain English change summary (LOGIC / REFACTOR / FEATURE / BUGFIX)
- Bug and logic error detection
- AI-generated code detection
- Fix suggestions

**Output formats:** terminal · markdown · SARIF (GitHub Security tab) · JSON

---

## Smart routing

```
< 50 lines   → local Ollama 3B    (instant, private, zero quota)
50–200 lines → Groq 70B           (fast, free tier)
200+ lines   → OpenRouter/Claude  (full context, deepest reasoning)
```

Auto-fallback when quotas run out. Override anytime: `cascade --tier frontier`

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

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

*Built by [Vyshakh G Nair](https://github.com/vyshakhgnair)*
