from typing import List
from cascade.diff_parser import FileDiff
from cascade.clients.base import BaseClient

PROMPT = """Analyze this git diff and respond in exactly this format:
SUMMARY: <2-3 sentence plain English summary of what changed>
TYPE: <LOGIC|REFACTOR|FEATURE|BUGFIX|COSMETIC>
RISKS: <comma-separated risks, or "None">

Diff:
{diff}"""

def summarize(files: List[FileDiff], client: BaseClient) -> dict:
    parts = []
    for f in files:
        parts.append(f"File: {f.path} (+{len(f.added_lines)} -{len(f.removed_lines)} lines)")
        if f.changed_functions:
            parts.append(f"Changed functions: {', '.join(f.changed_functions)}")
        parts.extend(f.added_lines[:30])

    messages = [
        {"role": "system", "content": "You are a senior code reviewer. Be concise and specific."},
        {"role": "user", "content": PROMPT.format(diff="\n".join(parts)[:3500])},
    ]
    return _parse(client.chat(messages, max_tokens=512))

def _parse(text: str) -> dict:
    result = {"summary": "", "type": "UNKNOWN", "risks": []}
    for line in text.splitlines():
        if line.startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
        elif line.startswith("TYPE:"):
            result["type"] = line.split(":", 1)[1].strip()
        elif line.startswith("RISKS:"):
            raw = line.split(":", 1)[1].strip()
            result["risks"] = [] if raw.lower() == "none" else [r.strip() for r in raw.split(",")]
    return result
