import re
from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path
from cascade.diff_parser import FileDiff

@dataclass
class BlastRadiusResult:
    changed_symbols: List[str] = field(default_factory=list)
    affected_files: Dict[str, List[str]] = field(default_factory=dict)
    risk_level: str = "LOW"

def _scan_repo(root: Path, symbols: List[str]) -> Dict[str, List[str]]:
    affected = {}
    for py_file in root.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            matched = [s for s in symbols if re.search(r'\b' + re.escape(s) + r'\b', content)]
            if matched:
                affected[str(py_file.relative_to(root))] = matched
        except Exception:
            continue
    return affected

def analyze(files: List[FileDiff], repo_root: str = ".") -> BlastRadiusResult:
    symbols = list({fn for f in files for fn in f.changed_functions})
    affected: Dict[str, List[str]] = {}

    if symbols:
        try:
            raw = _scan_repo(Path(repo_root), symbols)
            changed_paths = {f.path for f in files}
            affected = {k: v for k, v in raw.items() if k not in changed_paths}
        except Exception:
            pass

    count = len(affected)
    risk = "LOW" if count == 0 else "MEDIUM" if count <= 2 else "HIGH" if count <= 5 else "CRITICAL"

    return BlastRadiusResult(changed_symbols=symbols, affected_files=affected, risk_level=risk)
