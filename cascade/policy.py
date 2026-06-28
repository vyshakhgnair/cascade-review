import re
import yaml
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from cascade.diff_parser import FileDiff


@dataclass
class PolicyViolation:
    rule: str
    file: str
    description: str
    severity: str = "WARNING"


def _load_rules(repo_root: str = ".") -> Optional[dict]:
    for name in (".cascade-rules.yml", ".cascade-rules.yaml"):
        path = Path(repo_root) / name
        if path.exists():
            try:
                return yaml.safe_load(path.read_text(errors="ignore")) or {}
            except Exception:
                return None
    return None


def evaluate(files: List[FileDiff], repo_root: str = ".") -> List[PolicyViolation]:
    rules = _load_rules(repo_root)
    if not rules:
        return []

    violations = []

    for rule in rules.get("rules", []):
        name = rule.get("name", "unnamed")
        severity = rule.get("severity", "WARNING").upper()
        message = rule.get("message", f"Policy violation: {name}")

        pattern = rule.get("pattern")
        file_match = rule.get("files")
        forbidden_imports = rule.get("forbidden_imports", [])
        max_lines = rule.get("max_lines")
        require_pattern = rule.get("require")

        for f in files:
            if file_match and not re.search(file_match, f.path):
                continue

            added = "\n".join(f.added_lines)

            if pattern and re.search(pattern, added):
                violations.append(PolicyViolation(
                    rule=name, file=f.path, description=message, severity=severity,
                ))

            for imp in forbidden_imports:
                if re.search(r'\b' + re.escape(imp) + r'\b', added):
                    violations.append(PolicyViolation(
                        rule=name, file=f.path,
                        description=f"{message} — forbidden import: {imp}",
                        severity=severity,
                    ))

            if max_lines and len(f.added_lines) > max_lines:
                violations.append(PolicyViolation(
                    rule=name, file=f.path,
                    description=f"{message} — file adds {len(f.added_lines)} lines (max {max_lines})",
                    severity=severity,
                ))

            if require_pattern and not re.search(require_pattern, added):
                violations.append(PolicyViolation(
                    rule=name, file=f.path,
                    description=f"{message} — required pattern not found",
                    severity=severity,
                ))

    return violations
