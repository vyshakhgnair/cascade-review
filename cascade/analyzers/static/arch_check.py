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

GOD_CLASS_THRESHOLD = 15

def _check_python(f: FileDiff, added: str) -> List[ArchDrift]:
    drifts = []

    if any(kw in f.path.lower() for kw in SERVICE_LAYERS):
        if re.search(DB_PATTERNS, added):
            drifts.append(ArchDrift(
                file=f.path,
                description="Direct DB access in service/controller — consider repository pattern",
            ))

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

    if re.search(r'except\s*:', added) or re.search(r'except\s+Exception\s*:', added):
        drifts.append(ArchDrift(
            file=f.path,
            description="Broad exception catch — catch specific exceptions",
        ))

    if "cli" not in f.path.lower() and re.search(r'\bprint\(', added):
        drifts.append(ArchDrift(
            file=f.path,
            description="print() in non-CLI code — use logging instead",
            severity="INFO",
        ))

    method_count = len(re.findall(r'\bdef\s+\w+', added))
    if method_count >= GOD_CLASS_THRESHOLD:
        drifts.append(ArchDrift(
            file=f.path,
            description=f"God class suspect — {method_count} methods in one file, consider splitting",
        ))

    imports = re.findall(r'from\s+(\S+)\s+import', added)
    module_name = f.path.replace("/", ".").replace("\\", ".").removesuffix(".py")
    for imp in imports:
        if imp == module_name or imp.endswith("." + module_name.split(".")[-1]):
            drifts.append(ArchDrift(
                file=f.path,
                description=f"Possible circular import: {module_name} imports from {imp}",
                severity="WARNING",
            ))

    return drifts


def _check_js_ts(f: FileDiff, added: str) -> List[ArchDrift]:
    drifts = []

    if any(kw in f.path.lower() for kw in SERVICE_LAYERS):
        if re.search(r'\b(query|execute|\.raw\(|knex|prisma\.\$queryRaw)', added):
            drifts.append(ArchDrift(
                file=f.path,
                description="Direct DB access in service/controller — consider repository pattern",
            ))

    if re.search(r'\bcatch\s*\(\s*\w*\s*\)\s*\{\s*\}', added):
        drifts.append(ArchDrift(
            file=f.path,
            description="Empty catch block — handle or log the error",
        ))

    if re.search(r'\bconsole\.(log|debug|info)\(', added) and "test" not in f.path.lower():
        drifts.append(ArchDrift(
            file=f.path,
            description="console.log in non-test code — use a proper logger",
            severity="INFO",
        ))

    method_count = len(re.findall(r'\b(?:function\s+\w+|(?:async\s+)?\w+\s*\([^)]*\)\s*\{)', added))
    if method_count >= GOD_CLASS_THRESHOLD:
        drifts.append(ArchDrift(
            file=f.path,
            description=f"God class suspect — {method_count} functions in one file, consider splitting",
        ))

    return drifts


def analyze(files: List[FileDiff], repo_root: str = ".") -> List[ArchDrift]:
    drifts = []
    for f in files:
        added = "\n".join(f.added_lines)
        if f.language == "python":
            drifts.extend(_check_python(f, added))
        elif f.language in ("javascript", "typescript"):
            drifts.extend(_check_js_ts(f, added))
    return drifts
