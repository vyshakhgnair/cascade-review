from typing import List
from cascade.diff_parser import FileDiff
from cascade.clients.base import BaseClient

PROMPT = """Analyze this code. Does it show signs of being AI-generated?

Signs: over-commented obvious logic, generic names (data/result/item), unnatural structure,
redundant error handling, boilerplate copy-paste without context.

Respond:
VERDICT: <YES|NO|UNCERTAIN>
CONFIDENCE: <HIGH|MEDIUM|LOW>
REASON: <one sentence>

Code:
{code}"""

def detect(files: List[FileDiff], client: BaseClient) -> dict:
    code = "\n".join(
        f"# {f.path}\n" + "\n".join(f.added_lines[:35])
        for f in files
    )
    messages = [{"role": "user", "content": PROMPT.format(code=code[:2000])}]
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
