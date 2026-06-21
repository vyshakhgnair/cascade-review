# Contributing to cascade-review

Thanks for your interest. Here's how to get started.

## Setup

```bash
git clone https://github.com/vyshakhgnair/cascade-review
cd cascade-review
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
pytest tests/unit/          # unit tests only
pytest tests/integration/   # requires API keys in env
```

## What to contribute

Good first contributions:
- New SonarQube rules in `cascade/analyzers/static/sonar.py`
- Support for a new language in `cascade/analyzers/static/`
- New secret patterns in `cascade/analyzers/static/secrets.py`
- New provider in `cascade/clients/registry.py` (if OpenAI-compatible, one line)

## Adding a provider

If the provider uses the OpenAI `/v1/chat/completions` format (most do):

```python
# cascade/clients/registry.py
PROVIDERS = {
    ...
    "your-provider": {"cls": OpenAICompatibleClient, "base_url": "https://api.your-provider.com/v1"},
}
```

If it uses a different API format, add a client class in `cascade/clients/` following `base.py`.

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] New features have unit tests
- [ ] `.cascade.yml.example` updated if config keys changed
- [ ] README updated if CLI flags or providers changed

## Reporting bugs

Use [GitHub Issues](https://github.com/vyshakhgnair/cascade-review/issues).  
Include: OS, Python version, command run, full output.
