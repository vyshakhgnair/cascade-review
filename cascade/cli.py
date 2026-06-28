import sys
import json
import argparse
import subprocess
import os

from cascade.config import load_config, resolve_api_key
from cascade.diff_parser import parse_diff
from cascade.router import route
from cascade.clients.registry import get_client, PROVIDERS
from cascade.analyzers.static import sonar, secrets, blast_radius, regression_risk, arch_check, build_breaker
from cascade.analyzers.static import version_conflict
from cascade.analyzers.llm import change_summary, bug_detector, llm_detector, fix_suggester
from cascade.output import terminal, markdown, sarif, html_report
from cascade.redact import redact_diff
from cascade.audit import write_audit_log
from cascade.policy import evaluate as evaluate_policy


def get_diff_from_git(staged: bool = False) -> str:
    cmd = ["git", "diff", "--staged"] if staged else ["git", "diff", "HEAD"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except Exception:
        return ""


API_KEY_ENV = {
    "groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
    "mistral": "MISTRAL_API_KEY", "together": "TOGETHER_API_KEY",
}

# Privacy: providers that guarantee no training on API inputs (paid tiers / explicit policy)
PROVIDER_PRIVACY = {
    "ollama":     "local",      # runs on your machine, nothing leaves
    "openai":     "no-train",   # API inputs not used for training (paid)
    "anthropic":  "no-train",   # API inputs not used for training
    "groq":       "unclear",    # free tier — check current ToS
    "openrouter": "unclear",    # proxies to other providers, varies by model
    "deepseek":   "unclear",    # free tier — may use inputs for training
    "mistral":    "no-train",   # API inputs not used for training
    "together":   "unclear",    # check current ToS
    "gemini":     "unclear",    # free tier — check current ToS
}

def build_client(config: dict, tier: str, provider_override: str = None, model_override: str = None):
    tier_cfg = config["models"].get(tier, {})
    provider = provider_override or tier_cfg.get("provider", "groq")
    model = model_override or tier_cfg.get("model", "llama-3.3-70b-versatile")
    api_key = resolve_api_key(tier_cfg)
    base_url = tier_cfg.get("base_url")

    if provider != "ollama" and not api_key:
        env_var = API_KEY_ENV.get(provider) or tier_cfg.get("api_key_env", "")
        if env_var and os.environ.get(env_var):
            api_key = os.environ[env_var]
        else:
            hint = f"  Set it with: export {env_var}=<your-key>" if env_var else ""
            raise RuntimeError(f"No API key for provider '{provider}'.{hint}")

    return get_client(provider=provider, model=model, api_key=api_key, base_url=base_url)


def run_list_providers():
    DIM, R, GRN, RED, YLW = "\033[2m", "\033[0m", "\033[92m", "\033[91m", "\033[93m"
    PRIVACY_LABEL = {
        "local":    f"{GRN}✓ local{R}",
        "no-train": f"{GRN}✓ no-train{R}",
        "unclear":  f"{YLW}⚠ check ToS{R}",
    }
    print(f"\n  {'Provider':<14} {'Key Env':<22} {'Privacy':<20} {'Status'}")
    print(f"  {'─' * 72}")
    for name in PROVIDERS:
        env_var = API_KEY_ENV.get(name, "")
        privacy = PRIVACY_LABEL.get(PROVIDER_PRIVACY.get(name, "unclear"), f"{YLW}⚠ check ToS{R}")
        if name == "ollama":
            status = "local (no key needed)"
        elif env_var and os.environ.get(env_var):
            status = f"{GRN}✓ configured{R}"
        elif env_var:
            status = f"{RED}✗ not set{R}"
        else:
            status = f"{YLW}? unknown{R}"
        print(f"  {name:<14} {env_var or '—':<22} {privacy:<30} {status}")
    print(f"\n  {DIM}Privacy: 'local' = runs on your machine, 'no-train' = provider won't train on inputs,{R}")
    print(f"  {DIM}'check ToS' = free tier may use inputs for model training — avoid for proprietary code.{R}")
    print(f"  {DIM}Use --no-llm for static-only analysis (no code sent anywhere).{R}\n")


def _status(msg):
    if sys.stderr.isatty():
        print(f"\033[2m  ⟳ {msg}…\033[0m", file=sys.stderr, flush=True)


def run_init():
    import shutil
    if os.path.exists(".cascade.yml"):
        print(".cascade.yml already exists.")
        return

    template = os.path.join(os.path.dirname(__file__), "..", ".cascade.yml.example")
    if os.path.exists(template):
        shutil.copy(template, ".cascade.yml")
        print("Created .cascade.yml — edit to configure your providers and models.")
    else:
        print("Run: cascade init  (template not found, create .cascade.yml manually)")


HOOK_SCRIPT = """#!/bin/sh
# cascade-review pre-commit hook
echo "Running cascade-review..."
git diff --staged | cascade --no-llm --severity-gate high
"""

def run_hook(action: str):
    hook_path = os.path.join(".git", "hooks", "pre-commit")
    if action == "install":
        if not os.path.isdir(".git"):
            print("Not a git repository.")
            return
        os.makedirs(os.path.dirname(hook_path), exist_ok=True)
        with open(hook_path, "w", newline="\n") as f:
            f.write(HOOK_SCRIPT)
        try:
            os.chmod(hook_path, 0o755)
        except Exception:
            pass
        print(f"Installed pre-commit hook at {hook_path}")
        print("Cascade will run static analysis on staged changes before each commit.")
    elif action == "uninstall":
        if os.path.exists(hook_path):
            with open(hook_path) as f:
                if "cascade-review" in f.read():
                    os.remove(hook_path)
                    print("Removed cascade pre-commit hook.")
                else:
                    print("Pre-commit hook exists but wasn't installed by cascade. Skipping.")
        else:
            print("No pre-commit hook found.")


SEVERITY_ORDER = {"CRITICAL": 5, "HIGH": 4, "MAJOR": 3, "MEDIUM": 3, "WARNING": 2, "MINOR": 1, "LOW": 1, "INFO": 0}

def _gate_check(gate: str, secret_findings, sonar_findings, breakers, drifts) -> bool:
    threshold = {"critical": 5, "high": 4, "medium": 3, "warning": 2, "low": 1}.get(gate, 2)
    for s in secret_findings:
        if SEVERITY_ORDER.get("CRITICAL", 5) >= threshold:
            return True
    for f in sonar_findings:
        if SEVERITY_ORDER.get(f.severity, 0) >= threshold:
            return True
    for b in breakers:
        if SEVERITY_ORDER.get(b.severity, 0) >= threshold:
            return True
    for d in drifts:
        if SEVERITY_ORDER.get(d.severity, 0) >= threshold:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(
        prog="cascade",
        description="AI code reviewer — SonarQube simulation, blast radius, smart model routing.",
    )
    parser.add_argument("--version", action="version", version="cascade-review 0.2.1")
    parser.add_argument("--staged", action="store_true", help="Review staged changes only")
    parser.add_argument("--tier", choices=["local", "mid", "frontier"], help="Force model tier")
    parser.add_argument("--provider", choices=list(PROVIDERS), help="Override provider")
    parser.add_argument("--model", help="Override model name")
    parser.add_argument("--output", choices=["terminal", "markdown", "sarif", "json", "html"], default="terminal")
    parser.add_argument("--no-llm", action="store_true", help="Static analysis only, skip LLM")
    parser.add_argument("--redact", action="store_true", help="Strip literals/values before sending to LLM")
    parser.add_argument("--severity-gate", choices=["critical", "high", "medium", "warning", "low"],
                        help="Exit non-zero if findings at or above this severity exist")
    parser.add_argument("--audit", action="store_true", help="Write audit trail to .cascade/audit.jsonl")
    parser.add_argument("--audit-path", help="Custom path for audit log file")
    parser.add_argument("--explain", action="store_true", help="Add explanations (learning mode)")
    parser.add_argument("--init", action="store_true", help="Create .cascade.yml config")
    parser.add_argument("--hook", choices=["install", "uninstall"], help="Install/remove pre-commit hook")
    parser.add_argument("--list-providers", action="store_true", help="Show supported providers and key status")
    args = parser.parse_args()

    if args.init:
        run_init()
        return

    if args.list_providers:
        run_list_providers()
        return

    if args.hook:
        run_hook(args.hook)
        return

    config = load_config()

    diff_text = sys.stdin.read() if not sys.stdin.isatty() else get_diff_from_git(args.staged)

    if not diff_text.strip():
        print("No changes found.")
        print("Usage: git diff | cascade   or   cascade --staged")
        sys.exit(0)

    files = parse_diff(diff_text)
    if not files:
        print("Could not parse diff.")
        sys.exit(1)

    decision = route(files, config)
    tier = args.tier or decision.tier

    # Static — always runs
    _status("Running static analysis")
    secret_findings = secrets.scan(files)
    sonar_findings = sonar.scan(files)
    blast = blast_radius.analyze(files)
    risk = regression_risk.score(files, blast)
    drifts = arch_check.analyze(files)
    _status("Checking for build breakers")
    breakers = build_breaker.analyze(files)
    _status("Checking version conflicts")
    conflicts = version_conflict.analyze(files)
    _status("Evaluating review policies")
    policy_violations = evaluate_policy(files)

    # LLM — skippable
    summary_result, bug_findings, llm_det, fix_suggestions = {}, [], {}, []
    if not args.no_llm:
        try:
            client = build_client(config, tier, args.provider, args.model)
            tier_cfg = config["models"].get(tier, {})
            provider = args.provider or tier_cfg.get("provider", "groq")
            if PROVIDER_PRIVACY.get(provider) == "unclear" and sys.stderr.isatty():
                print(f"\033[93m  ⚠ Provider '{provider}' may use your code for model training (free tier).\033[0m", file=sys.stderr)
                print(f"\033[2m    Use --no-llm for static-only, or switch to ollama/anthropic/openai for private review.\033[0m", file=sys.stderr)
            llm_files = redact_diff(files) if args.redact else files
            if args.redact:
                _status("Code redacted — sending anonymized diff to LLM")
            _status("Generating change summary")
            summary_result = change_summary.summarize(llm_files, client)
            _status("Scanning for bugs")
            bug_findings = bug_detector.detect(llm_files, client)
            _status("Checking for AI-generated code")
            llm_det = llm_detector.detect(llm_files, client)
            if bug_findings:
                _status("Generating fix suggestions")
                fix_suggestions = fix_suggester.suggest(llm_files, bug_findings, client)
        except Exception as e:
            print(f"[cascade] LLM skipped: {e}", file=sys.stderr)

    # Output
    if args.output == "terminal":
        terminal.print_report(summary_result, secret_findings, sonar_findings,
                              blast, risk, drifts, bug_findings, llm_det, fix_suggestions,
                              breakers, conflicts, policy_violations, config)
    elif args.output == "markdown":
        print(markdown.render(summary_result, secret_findings, sonar_findings, blast, risk,
                              bug_findings, fix_suggestions, breakers, conflicts, policy_violations))
    elif args.output == "html":
        print(html_report.render(summary_result, secret_findings, sonar_findings, blast, risk,
                                 bug_findings, fix_suggestions, breakers, conflicts, policy_violations,
                                 drifts, llm_det, {"tier": tier, "reason": decision.reason}))
    elif args.output == "sarif":
        print(json.dumps(sarif.render(sonar_findings, secret_findings, breakers), indent=2))
    elif args.output == "json":
        print(json.dumps({
            "routing": {"tier": tier, "reason": decision.reason},
            "summary": summary_result,
            "secrets": [vars(s) for s in secret_findings],
            "sonar": [vars(s) for s in sonar_findings],
            "blast_radius": {"symbols": blast.changed_symbols, "affected": blast.affected_files, "risk": blast.risk_level},
            "regression_risk": {"score": risk.score, "level": risk.level, "reasons": risk.reasons},
            "architecture": [vars(d) for d in drifts],
            "build_breakers": [vars(b) for b in breakers],
            "version_conflicts": [vars(c) for c in conflicts],
            "policy_violations": [vars(v) for v in policy_violations],
            "bugs": bug_findings,
            "fix_suggestions": fix_suggestions,
            "llm_detection": llm_det,
        }, indent=2))

    # Audit trail
    if args.audit:
        tier_cfg = config["models"].get(tier, {})
        provider = args.provider or tier_cfg.get("provider", "groq") if not args.no_llm else None
        model = args.model or tier_cfg.get("model") if not args.no_llm else None
        audit_data = {
            "files": [{"path": f.path} for f in files],
            "secrets": [vars(s) for s in secret_findings],
            "sonar": [vars(s) for s in sonar_findings],
            "build_breakers": [vars(b) for b in breakers],
            "architecture": [vars(d) for d in drifts],
            "bugs": bug_findings,
            "regression_risk": {"score": risk.score, "level": risk.level},
            "routing": {"tier": tier, "reason": decision.reason},
        }
        log_path = write_audit_log(audit_data, config, provider=provider, model=model,
                                   redacted=args.redact, output_path=args.audit_path)
        _status(f"Audit log written to {log_path}")

    # Exit codes: severity gate > secrets > clean
    if args.severity_gate and _gate_check(args.severity_gate, secret_findings, sonar_findings, breakers, drifts):
        sys.exit(3)
    if secret_findings:
        sys.exit(2)


if __name__ == "__main__":
    main()
