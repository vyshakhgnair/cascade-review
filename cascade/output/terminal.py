from typing import List
from cascade.analyzers.static.secrets import SecretFinding
from cascade.analyzers.static.sonar import SonarFinding
from cascade.analyzers.static.blast_radius import BlastRadiusResult
from cascade.analyzers.static.regression_risk import RegressionRisk
from cascade.analyzers.static.arch_check import ArchDrift

R = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
YLW = "\033[93m"
BLU = "\033[94m"
GRN = "\033[92m"
CYN = "\033[96m"

SEVERITY_COLOR = {
    "CRITICAL": RED, "HIGH": RED, "MAJOR": YLW,
    "WARNING": YLW, "MEDIUM": YLW, "MINOR": BLU,
    "INFO": BLU, "LOW": GRN,
}

def clr(text, sev): return f"{SEVERITY_COLOR.get(sev, '')}{text}{R}"
def hdr(title): print(f"\n{DIM}{'─' * 58}{R}\n  {BOLD}{title}{R}")

def print_report(summary, secrets, sonar, blast, risk, drifts, bugs, llm_det, config):
    print(f"\n{BOLD}  cascade-review{R}  {DIM}github.com/vyshakhgnair/cascade-review{R}")

    # Change summary
    hdr("CHANGE SUMMARY")
    if summary.get("summary"):
        print(f"  {summary['summary']}")
    change_type = summary.get("type", "UNKNOWN")
    print(f"  Type: {CYN}{change_type}{R}")
    for r in summary.get("risks", []):
        print(f"  {YLW}⚠{R}  {r}")

    # Secrets — never filtered
    if secrets:
        hdr(f"{RED}⛔ SECRETS DETECTED{R}")
        for s in secrets:
            print(f"  {clr('CRITICAL', 'CRITICAL')}  [{s.secret_type}] in {s.file}")
            print(f"  {DIM}{s.line_content}{R}")

    # Regression risk
    hdr("REGRESSION RISK")
    bar = "█" * risk.score + "░" * (10 - risk.score)
    print(f"  {clr(str(risk.score) + '/10', risk.level)}  {bar}  {clr(risk.level, risk.level)}")
    for r in risk.reasons:
        print(f"  {DIM}›{R} {r}")

    # Blast radius
    hdr("BLAST RADIUS")
    if blast.changed_symbols:
        print(f"  Changed: {CYN}{', '.join(blast.changed_symbols)}{R}")
    if blast.affected_files:
        print(f"  Risk: {clr(blast.risk_level, blast.risk_level)}")
        for path, syms in list(blast.affected_files.items())[:6]:
            print(f"  {DIM}→{R} {path}  uses {CYN}{', '.join(syms)}{R}")
    else:
        print(f"  {GRN}✓ No downstream dependencies affected{R}")

    # SonarQube
    if sonar:
        hdr("SONARQUBE SIMULATION")
        for f in sonar:
            print(f"  {clr(f.severity, f.severity):<22} {DIM}{f.rule_id}{R}  {f.description}  {DIM}[{f.debt}]{R}")

    # Architecture drift
    if drifts:
        hdr("ARCHITECTURE DRIFT")
        for d in drifts:
            print(f"  {clr(d.severity, 'WARNING')}  {d.file}")
            print(f"  {DIM}›{R} {d.description}")

    # LLM detection
    if llm_det.get("verdict") == "YES":
        hdr("AI-GENERATED CODE SUSPECTED")
        print(f"  Confidence: {clr(llm_det.get('confidence', ''), 'WARNING')}")
        print(f"  {llm_det.get('reason', '')}")
        print(f"  {DIM}Verify this logic matches your intent before committing.{R}")

    # Bugs
    if bugs:
        hdr("BUGS FOUND")
        for b in bugs:
            print(f"  {clr(b.get('severity', 'WARNING'), b.get('severity', 'WARNING'))}  {b['description']}")

    print(f"\n{DIM}{'─' * 58}{R}\n")
