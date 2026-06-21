from typing import List
from cascade.diff_parser import FileDiff
from cascade.clients.base import BaseClient

PROMPT = """Review this code diff for bugs, logic errors, and issues.
For each issue, respond with one line:
ISSUE: <description> | SEVERITY: <CRITICAL|WARNING|INFO>

If none found, respond: NO_ISSUES

Diff:
{diff}"""

def detect(files: List[FileDiff], client: BaseClient) -> List[dict]:
    diff = "\n".join(
        f"# {f.path}\n" + "\n".join(f"+ {l}" for l in f.added_lines[:40])
        for f in files
    )
    messages = [
        {"role": "system", "content": "You are a senior engineer doing code review. Be specific and concise."},
        {"role": "user", "content": PROMPT.format(diff=diff[:3000])},
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
