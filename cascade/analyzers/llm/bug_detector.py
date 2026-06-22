from typing import List
from cascade.diff_parser import FileDiff
from cascade.clients.base import BaseClient

PROMPT = """Review this code diff for real bugs only — logic errors, off-by-ones, null/undefined access,
race conditions, resource leaks, missing error handling on external calls, security flaws.

Do NOT flag style issues, naming, or missing comments.

For each bug, respond with one line in this exact format:
ISSUE: <file>: <specific description> | SEVERITY: <CRITICAL|WARNING|INFO>

If no real bugs found, respond exactly: NO_ISSUES

Diff:
{diff}"""

def detect(files: List[FileDiff], client: BaseClient) -> List[dict]:
    parts = []
    for f in files:
        parts.append(f"--- {f.path}")
        for line in f.removed_lines[:20]:
            parts.append(f"- {line}")
        for line in f.added_lines[:40]:
            parts.append(f"+ {line}")
        parts.append("")
    diff = "\n".join(parts)[:4000]
    messages = [
        {"role": "system", "content": "You are a senior engineer doing code review. Only flag real bugs — false positives waste the developer's time."},
        {"role": "user", "content": PROMPT.format(diff=diff)},
    ]
    return _parse(client.chat(messages, max_tokens=1024))

def _parse(text: str) -> List[dict]:
    if "NO_ISSUES" in text:
        return []
    issues = []
    for line in text.splitlines():
        if not line.startswith("ISSUE:"):
            continue
        parts = {p.split(":", 1)[0].strip(): p.split(":", 1)[1].strip()
                 for p in line.split("|") if ":" in p}
        issues.append({
            "description": parts.get("ISSUE", line),
            "severity": parts.get("SEVERITY", "WARNING"),
        })
    return issues
