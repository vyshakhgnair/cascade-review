import re
from typing import List
from cascade.diff_parser import FileDiff

_COUNTER = 0

def _next_id(prefix: str) -> str:
    global _COUNTER
    _COUNTER += 1
    return f"{prefix}_{_COUNTER}"

def redact_line(line: str) -> str:
    line = re.sub(r'(["\'])(?:(?!\1).)*\1', lambda m: m.group(1) + _next_id("STR") + m.group(1), line)
    line = re.sub(r'(?<![a-zA-Z_])\d+\.?\d*(?![a-zA-Z_])', lambda m: _next_id("NUM"), line)
    return line

def redact_diff(files: List[FileDiff]) -> List[FileDiff]:
    global _COUNTER
    _COUNTER = 0
    redacted = []
    for f in files:
        rf = FileDiff(
            path=f.path,
            language=f.language,
            added_lines=[redact_line(l) for l in f.added_lines],
            removed_lines=[redact_line(l) for l in f.removed_lines],
            hunks=f.hunks,
            changed_functions=f.changed_functions,
            total_changes=f.total_changes,
        )
        redacted.append(rf)
    return redacted
