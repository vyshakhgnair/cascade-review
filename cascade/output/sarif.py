from typing import List
from cascade.analyzers.static.sonar import SonarFinding
from cascade.analyzers.static.secrets import SecretFinding

LEVEL = {"CRITICAL": "error", "MAJOR": "error", "MINOR": "warning", "INFO": "note"}

def render(sonar: List[SonarFinding], secrets: List[SecretFinding]) -> dict:
    results = []
    for f in sonar:
        results.append({
            "ruleId": f"cascade/{f.rule_id}",
            "level": LEVEL.get(f.severity, "warning"),
            "message": {"text": f.description},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": f.file}}}],
        })
    for s in secrets:
        results.append({
            "ruleId": "cascade/SECRET001",
            "level": "error",
            "message": {"text": f"Potential {s.secret_type} detected"},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": s.file}}}],
        })
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{"tool": {"driver": {
            "name": "cascade-review",
            "version": "0.1.0",
            "informationUri": "https://github.com/vyshakhgnair/cascade-review",
            "rules": [],
        }}, "results": results}],
    }
