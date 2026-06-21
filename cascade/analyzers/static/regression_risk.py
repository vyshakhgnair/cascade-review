from dataclasses import dataclass, field
from typing import List
from cascade.diff_parser import FileDiff
from cascade.analyzers.static.blast_radius import BlastRadiusResult

SENSITIVE_PATHS = ["auth", "login", "password", "token", "security", "payment", "crypto", "session"]

@dataclass
class RegressionRisk:
    score: int
    level: str
    reasons: List[str] = field(default_factory=list)

def score(files: List[FileDiff], blast: BlastRadiusResult) -> RegressionRisk:
    points = 0
    reasons = []

    total = sum(f.total_changes for f in files)
    if total > 200:
        points += 3
        reasons.append(f"Large diff: {total} lines changed")
    elif total > 100:
        points += 2
        reasons.append(f"Medium diff: {total} lines changed")
    elif total > 50:
        points += 1

    count = len(blast.affected_files)
    if count >= 5:
        points += 3
        reasons.append(f"{count} files depend on changed symbols")
    elif count >= 2:
        points += 2
        reasons.append(f"{count} files import changed symbols")
    elif count == 1:
        points += 1
        reasons.append("1 file imports changed symbols")

    if blast.changed_symbols:
        points += 1
        reasons.append(f"Functions modified: {', '.join(blast.changed_symbols[:3])}")

    for f in files:
        if any(kw in f.path.lower() for kw in SENSITIVE_PATHS):
            points += 2
            reasons.append(f"Security-sensitive file: {f.path}")
            break

    s = min(10, points)
    level = "CRITICAL" if s >= 8 else "HIGH" if s >= 6 else "MEDIUM" if s >= 4 else "LOW"
    return RegressionRisk(score=s, level=level, reasons=reasons)
