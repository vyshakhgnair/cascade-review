import re
from dataclasses import dataclass
from typing import List
from cascade.diff_parser import FileDiff

@dataclass
class SonarFinding:
    rule_id: str
    description: str
    file: str
    severity: str
    debt: str

def _check_python(file: FileDiff) -> List[SonarFinding]:
    findings = []
    added = "\n".join(file.added_lines)

    # S1192: Duplicated string literals
    strings = re.findall(r'["\']([^"\']{4,})["\']', added)
    for s in set(strings):
        if strings.count(s) >= 3:
            findings.append(SonarFinding(
                rule_id="S1192", file=file.path, severity="MAJOR", debt="5min",
                description=f'String "{s[:30]}" duplicated {strings.count(s)}x — define a constant',
            ))

    # S1134: FIXME/HACK markers
    for line in file.added_lines:
        if re.search(r'\b(FIXME|HACK|XXX)\b', line):
            findings.append(SonarFinding(
                rule_id="S1134", file=file.path, severity="MAJOR", debt="varies",
                description="FIXME/HACK marker in added code — resolve before merging",
            ))
            break

    # S2077: SQL injection
    for line in file.added_lines:
        if re.search(r'(execute|query|cursor)\s*\(.*\+', line) or re.search(r'f["\'].*SELECT.*\{', line):
            findings.append(SonarFinding(
                rule_id="S2077", file=file.path, severity="CRITICAL", debt="30min",
                description="SQL query built from variable — use parameterised queries",
            ))

    # S1481: Unused variables
    assignments = re.findall(r'^\s*(\w+)\s*=', added, re.MULTILINE)
    for var in assignments:
        if var.startswith('_') or var in ('self', 'cls'):
            continue
        if len(re.findall(r'\b' + re.escape(var) + r'\b', added)) == 1:
            findings.append(SonarFinding(
                rule_id="S1481", file=file.path, severity="MINOR", debt="2min",
                description=f'Variable "{var}" assigned but never used',
            ))

    # S3776: Cognitive complexity
    branch_kw = ['if ', 'elif ', 'else:', 'for ', 'while ', 'except ', ' and ', ' or ']
    complexity = sum(added.count(kw) for kw in branch_kw)
    if complexity > 15:
        findings.append(SonarFinding(
            rule_id="S3776", file=file.path, severity="CRITICAL", debt="1h",
            description=f"Cognitive complexity ~{complexity} exceeds threshold of 15",
        ))
    elif complexity > 10:
        findings.append(SonarFinding(
            rule_id="S3776", file=file.path, severity="MAJOR", debt="30min",
            description=f"Cognitive complexity ~{complexity} — approaching threshold of 15",
        ))

    # S112: Generic exception raised
    if re.search(r'raise\s+Exception\(', added):
        findings.append(SonarFinding(
            rule_id="S112", file=file.path, severity="MAJOR", debt="10min",
            description="Generic Exception raised — use a specific exception class",
        ))

    return findings

def scan(files: List[FileDiff]) -> List[SonarFinding]:
    findings = []
    for f in files:
        if f.language == "python":
            findings.extend(_check_python(f))
    return findings
