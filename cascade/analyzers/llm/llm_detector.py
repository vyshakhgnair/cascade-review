from typing import List
from cascade.diff_parser import FileDiff
from cascade.clients.base import BaseClient

PROMPT = """Analyze this code for signs of being AI-generated (ChatGPT, Copilot, etc).

Strong signals:
- Over-commented obvious logic ("# initialize the variable")
- Placeholder/generic names (data, result, item, temp, output) used throughout
- Unnecessary try/except wrapping every operation
- Docstrings on every trivial function
- Boilerplate that doesn't match the rest of the codebase style
- "TODO: implement" or "# Add your code here" markers

Weak signals (not enough alone): clean formatting, consistent style, thorough error handling.

Respond in exactly this format — no extra text:
VERDICT: <YES|NO|UNCERTAIN>
CONFIDENCE: <HIGH|MEDIUM|LOW>
REASON: <one sentence explaining the strongest signal>

Code:
{code}"""

def detect(files: List[FileDiff], client: BaseClient) -> dict:
    parts = []
    for f in files:
        parts.append(f"# {f.path}")
        parts.extend(f.added_lines[:40])
        parts.append("")
    code = "\n".join(parts)[:3000]
    messages = [
        {"role": "system", "content": "You are a code reviewer checking for AI-generated code. Err toward NO — only flag YES with strong evidence."},
        {"role": "user", "content": PROMPT.format(code=code)},
    ]
    return _parse(client.chat(messages, max_tokens=256))

def _parse(text: str) -> dict:
    result = {"verdict": "UNCERTAIN", "confidence": "LOW", "reason": ""}
    for line in text.splitlines():
        if line.startswith("VERDICT:"):
            result["verdict"] = line.split(":", 1)[1].strip()
        elif line.startswith("CONFIDENCE:"):
            result["confidence"] = line.split(":", 1)[1].strip()
        elif line.startswith("REASON:"):
            result["reason"] = line.split(":", 1)[1].strip()
    return result
