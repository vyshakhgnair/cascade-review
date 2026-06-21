import re
from dataclasses import dataclass
from typing import List
from cascade.diff_parser import FileDiff

@dataclass
class ArchDrift:
    description: str
    file: str
    severity: str = "WARNING"

SERVICE_LAYERS = ["service", "controller", "view", "route", "handler", "endpoint"]
DB_PATTERNS = r'\b(execute|cursor\.execute|Session\(\)|db\.query|\.filter\(|\.all\(\))\b'

def analyze(files: List[FileDiff], repo_root: str = ".") -> List[ArchDrift]:
    drifts = []
    for f in files:
        if f.language != "python":
            continue
        added = "\n".join(f.added_lines)

        # Direct DB access in service/controller layer
        if any(kw in f.path.lower() for kw in SERVICE_LAYERS):
            if re.search(DB_PATTERNS, added):
                drifts.append(ArchDrift(
                    file=f.path,
                    description="Direct DB access in service/controller — consider repository pattern",
                ))

        # Mixed naming conventions
        camel_fns = re.findall(r'\bdef ([a-z]+[A-Z]\w+)', added)
        snake_fns = re.findall(r'\bdef ([a-z]+_[a-z]\w+)', added)
        if camel_fns and snake_fns:
            drifts.append(ArchDrift(
                file=f.path,
                description=f"Mixed naming: camelCase and snake_case in same file ({', '.join(camel_fns[:2])})",
                severity="INFO",
            ))
        elif camel_fns:
            drifts.append(ArchDrift(
                file=f.path,
                description=f"camelCase functions in Python — use snake_case: {', '.join(camel_fns[:3])}",
            ))

        # Broad exception catch
        if re.search(r'except\s*:', added) or re.search(r'except\s+Exception\s*:', added):
            drifts.append(ArchDrift(
                file=f.path,
                description="Broad exception catch — catch specific exceptions",
            ))

        # Print statements in non-CLI files
        if "cli" not in f.path.lower() and re.search(r'^\+\s*print\(', "\n".join(f.added_lines), re.MULTILINE):
            drifts.append(ArchDrift(
                file=f.path,
                description="print() in non-CLI code — use logging instead",
                severity="INFO",
            ))

    return drifts
