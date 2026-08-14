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

    # S5754: Bare except should re-raise or catch specific exceptions
    # Severity and debt were inferred from codebase patterns (Since rules onSonarQube portal are unavailable)
    # Matches S2077 severity (CRITICAL) as reliability-critical like security issues
    for line in file.added_lines:
        stripped = line.strip()
        if re.match(r'except\s*:\s*', stripped):
            findings.append(SonarFinding(
                rule_id="S5754", file=file.path, severity="CRITICAL", debt="15min",
                description="Bare except catches all exceptions including SystemExit and KeyboardInterrupt — specify exception types or re-raise",
            ))
            break
        if re.match(r'except\s+(BaseException|SystemExit)', stripped):
            findings.append(SonarFinding(
                rule_id="S5754", file=file.path, severity="CRITICAL", debt="15min",
                description="Catching BaseException/SystemExit without re-raising prevents proper program termination",
            ))
            break

    # S1066: Collapsible if statements
    lines = file.added_lines
    for i in range(len(lines) - 1):
        if re.match(r'\s*if\s+.+:\s*$', lines[i]) and re.match(r'\s*if\s+.+:\s*$', lines[i + 1]):
            indent_outer = len(lines[i]) - len(lines[i].lstrip())
            indent_inner = len(lines[i + 1]) - len(lines[i + 1].lstrip())
            if indent_inner > indent_outer:
                findings.append(SonarFinding(
                    rule_id="S1066", file=file.path, severity="MINOR", debt="5min",
                    description="Collapsible if statements — merge with 'and'",
                ))
                break

    # S1874: Deprecated API usage
    deprecated = [r'\.has_key\(', r'\bprint\s+[^(]', r'\bexecfile\(', r'\braw_input\(']
    for pat in deprecated:
        if re.search(pat, added):
            findings.append(SonarFinding(
                rule_id="S1874", file=file.path, severity="WARNING", debt="15min",
                description="Deprecated API usage detected — update to modern equivalent",
            ))
            break

    return findings


def _check_js_ts(file: FileDiff) -> List[SonarFinding]:
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

    # S1134: FIXME/HACK/TODO markers
    for line in file.added_lines:
        if re.search(r'\b(FIXME|HACK|XXX)\b', line):
            findings.append(SonarFinding(
                rule_id="S1134", file=file.path, severity="MAJOR", debt="varies",
                description="FIXME/HACK marker in added code — resolve before merging",
            ))
            break

    # S3776: Cognitive complexity
    branch_kw = ['if ', 'else if ', 'else ', 'for ', 'while ', 'switch ', ' && ', ' || ', '? ']
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

    # S1481: Unused variables
    decls = re.findall(r'\b(?:const|let|var)\s+(\w+)\s*=', added)
    for var in decls:
        if var.startswith('_'):
            continue
        if len(re.findall(r'\b' + re.escape(var) + r'\b', added)) == 1:
            findings.append(SonarFinding(
                rule_id="S1481", file=file.path, severity="MINOR", debt="2min",
                description=f'Variable "{var}" assigned but never used',
            ))

    # S2077: SQL injection via template literals
    if re.search(r'`[^`]*SELECT[^`]*\$\{', added, re.IGNORECASE):
        findings.append(SonarFinding(
            rule_id="S2077", file=file.path, severity="CRITICAL", debt="30min",
            description="SQL query built from template literal — use parameterised queries",
        ))

    # S1066: Collapsible if
    lines = file.added_lines
    for i in range(len(lines) - 1):
        if re.match(r'\s*if\s*\(.+\)\s*\{\s*$', lines[i]) and re.match(r'\s*if\s*\(.+\)\s*\{?\s*$', lines[i + 1]):
            findings.append(SonarFinding(
                rule_id="S1066", file=file.path, severity="MINOR", debt="5min",
                description="Collapsible if statements — merge with &&",
            ))
            break

    # S106: Console.log left in code
    if re.search(r'\bconsole\.(log|debug|info)\(', added):
        findings.append(SonarFinding(
            rule_id="S106", file=file.path, severity="MINOR", debt="2min",
            description="console.log left in code — use a proper logger or remove",
        ))

    # S3504: var usage — prefer const/let
    if re.search(r'\bvar\s+\w+', added):
        findings.append(SonarFinding(
            rule_id="S3504", file=file.path, severity="MINOR", debt="5min",
            description="'var' used — prefer 'const' or 'let'",
        ))

    # S1110: eval() usage
    if re.search(r'\beval\s*\(', added):
        findings.append(SonarFinding(
            rule_id="S1523", file=file.path, severity="CRITICAL", debt="30min",
            description="eval() is a security risk — avoid dynamic code execution",
        ))

    return findings


def scan(files: List[FileDiff]) -> List[SonarFinding]:
    findings = []
    for f in files:
        if f.language == "python":
            findings.extend(_check_python(f))
        elif f.language in ("javascript", "typescript"):
            findings.extend(_check_js_ts(f))
    return findings
