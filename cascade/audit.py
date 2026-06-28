import json
import os
import datetime
from pathlib import Path


def write_audit_log(results: dict, config: dict, provider: str = None, model: str = None,
                    redacted: bool = False, output_path: str = None):
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "version": "0.2.0",
        "provider": provider,
        "model": model,
        "redacted": redacted,
        "files_reviewed": [f["path"] for f in results.get("files", [])],
        "findings": {
            "secrets": len(results.get("secrets", [])),
            "sonar": len(results.get("sonar", [])),
            "build_breakers": len(results.get("build_breakers", [])),
            "architecture": len(results.get("architecture", [])),
            "bugs": len(results.get("bugs", [])),
        },
        "severities": _count_severities(results),
        "regression_risk": results.get("regression_risk", {}),
        "routing": results.get("routing", {}),
    }

    log_path = Path(output_path or _default_log_path())
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return str(log_path)


def _count_severities(results: dict) -> dict:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "WARNING": 0, "LOW": 0, "INFO": 0}
    for s in results.get("secrets", []):
        counts["CRITICAL"] += 1
    for f in results.get("sonar", []):
        sev = f.get("severity", "INFO") if isinstance(f, dict) else getattr(f, "severity", "INFO")
        counts[sev] = counts.get(sev, 0) + 1
    for b in results.get("build_breakers", []):
        sev = b.get("severity", "HIGH") if isinstance(b, dict) else getattr(b, "severity", "HIGH")
        counts[sev] = counts.get(sev, 0) + 1
    return {k: v for k, v in counts.items() if v > 0}


def _default_log_path() -> str:
    return os.path.join(".cascade", "audit.jsonl")
