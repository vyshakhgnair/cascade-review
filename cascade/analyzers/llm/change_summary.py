from typing import List
from cascade.diff_parser import FileDiff
from cascade.clients.base import BaseClient

PROMPT = """Analyze this git diff and respond in exactly this format — no extra text:
SUMMARY: <2-3 sentence plain English summary of what changed and why>
TYPE: <LOGIC|REFACTOR|FEATURE|BUGFIX|COSMETIC|CONFIG|TEST|DOCS>
RISKS: <comma-separated specific risks, or "None">

Focus on intent, not mechanics. Say what the change accomplishes, not "added lines to file X".

Diff:
{diff}"""

def _build_diff_text(files: List[FileDiff], max_chars: int = 4000) -> str:
    parts = []
    for f in files:
        parts.append(f"--- {f.path} (+{len(f.added_lines)} -{len(f.removed_lines)})")
        if f.changed_functions:
            parts.append(f"  functions: {', '.join(f.changed_functions)}")
        for line in f.removed_lines[:15]:
            parts.append(f"- {line}")
        for line in f.added_lines[:30]:
            parts.append(f"+ {line}")
        parts.append("")
    text = "\n".join(parts)
    return text[:max_chars]

def summarize(files: List[FileDiff], client: BaseClient) -> dict:
    messages = [
        {"role": "system", "content": "You are a senior code reviewer. Be concise and specific. Never guess — if unsure, say so."},
        {"role": "user", "content": PROMPT.format(diff=_build_diff_text(files))},
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
