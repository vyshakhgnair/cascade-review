from typing import List
from cascade.diff_parser import FileDiff
from cascade.clients.base import BaseClient

PROMPT = """Given this code diff and the issues found, suggest concrete fixes.

For each fix, respond with one line in this exact format:
FIX: <file>: <what to change and how> | EFFORT: <trivial|small|medium|large>

Only suggest fixes for real problems. Max 5 fixes. If nothing to fix, respond: NO_FIXES

Issues found:
{issues}

Diff:
{diff}"""


def suggest(files: List[FileDiff], issues: List[dict], client: BaseClient) -> List[dict]:
    if not issues:
        return []

    issue_text = "\n".join(
        f"- [{i.get('severity', 'WARNING')}] {i['description']}" for i in issues[:8]
    )
    parts = []
    for f in files:
        parts.append(f"--- {f.path}")
        for line in f.added_lines[:30]:
            parts.append(f"+ {line}")
        parts.append("")
    diff = "\n".join(parts)[:3000]

    messages = [
        {"role": "system", "content": "You are a senior engineer. Suggest specific, actionable fixes — not vague advice."},
        {"role": "user", "content": PROMPT.format(issues=issue_text, diff=diff)},
    ]
    return _parse(client.chat(messages, max_tokens=1024))


def _parse(text: str) -> List[dict]:
    if "NO_FIXES" in text:
        return []
    fixes = []
    for line in text.splitlines():
        if not line.startswith("FIX:"):
            continue
        parts = {p.split(":", 1)[0].strip(): p.split(":", 1)[1].strip()
                 for p in line.split("|") if ":" in p}
        fixes.append({
            "description": parts.get("FIX", line),
            "effort": parts.get("EFFORT", "small"),
        })
    return fixes
