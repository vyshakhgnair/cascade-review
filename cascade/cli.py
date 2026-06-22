import sys
import json
import argparse
import subprocess
import os

from cascade.config import load_config, resolve_api_key
from cascade.diff_parser import parse_diff
from cascade.router import route
from cascade.clients.registry import get_client, PROVIDERS
from cascade.analyzers.static import sonar, secrets, blast_radius, regression_risk, arch_check
from cascade.analyzers.llm import change_summary, bug_detector, llm_detector, fix_suggester
from cascade.output import terminal, markdown, sarif


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
    print(f"\n  {'Provider':<14} {'Type':<10} {'API Key Env':<22} {'Status'}")
    print(f"  {'─' * 60}")
    for name, entry in PROVIDERS.items():
        env_var = API_KEY_ENV.get(name, "")
        if name == "ollama":
            status = "local (no key needed)"
        elif env_var and os.environ.get(env_var):
            status = "\033[92m✓ configured\033[0m"
        elif env_var:
            status = "\033[91m✗ not set\033[0m"
        else:
            status = "\033[93m? unknown\033[0m"
        ptype = "local" if name == "ollama" else "cloud"
        print(f"  {name:<14} {ptype:<10} {env_var or '—':<22} {status}")
    print()


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


def main():
    parser = argparse.ArgumentParser(
        prog="cascade",
        description="AI code reviewer — SonarQube simulation, blast radius, smart model routing.",
    )
    parser.add_argument("--version", action="version", version="cascade-review 0.1.0")
    parser.add_argument("--staged", action="store_true", help="Review staged changes only")
    parser.add_argument("--tier", choices=["local", "mid", "frontier"], help="Force model tier")
    parser.add_argument("--provider", choices=list(PROVIDERS), help="Override provider")
    parser.add_argument("--model", help="Override model name")
    parser.add_argument("--output", choices=["terminal", "markdown", "sarif", "json"], default="terminal")
    parser.add_argument("--no-llm", action="store_true", help="Static analysis only, skip LLM")
    parser.add_argument("--explain", action="store_true", help="Add explanations (learning mode)")
    parser.add_argument("--init", action="store_true", help="Create .cascade.yml config")
    parser.add_argument("--list-providers", action="store_true", help="Show supported providers and key status")
    args = parser.parse_args()

    if args.init:
        run_init()
        return

    if args.list_providers:
        run_list_providers()
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
    secret_findings = secrets.scan(files)
    sonar_findings = sonar.scan(files)
    blast = blast_radius.analyze(files)
    risk = regression_risk.score(files, blast)
    drifts = arch_check.analyze(files)

    # LLM — skippable
    summary_result, bug_findings, llm_det, fix_suggestions = {}, [], {}, []
    if not args.no_llm:
        try:
            client = build_client(config, tier, args.provider, args.model)
            _status("Generating change summary")
            summary_result = change_summary.summarize(files, client)
            _status("Scanning for bugs")
            bug_findings = bug_detector.detect(files, client)
            _status("Checking for AI-generated code")
            llm_det = llm_detector.detect(files, client)
            if bug_findings:
                _status("Generating fix suggestions")
                fix_suggestions = fix_suggester.suggest(files, bug_findings, client)
        except Exception as e:
            print(f"[cascade] LLM skipped: {e}", file=sys.stderr)

    # Output
    if args.output == "terminal":
        terminal.print_report(summary_result, secret_findings, sonar_findings,
                              blast, risk, drifts, bug_findings, llm_det, fix_suggestions, config)
    elif args.output == "markdown":
        print(markdown.render(summary_result, secret_findings, sonar_findings, blast, risk, bug_findings, fix_suggestions))
    elif args.output == "sarif":
        print(json.dumps(sarif.render(sonar_findings, secret_findings), indent=2))
    elif args.output == "json":
        print(json.dumps({
            "routing": {"tier": tier, "reason": decision.reason},
            "summary": summary_result,
            "secrets": [vars(s) for s in secret_findings],
            "sonar": [vars(s) for s in sonar_findings],
            "blast_radius": {"symbols": blast.changed_symbols, "affected": blast.affected_files, "risk": blast.risk_level},
            "regression_risk": {"score": risk.score, "level": risk.level, "reasons": risk.reasons},
            "architecture": [vars(d) for d in drifts],
            "bugs": bug_findings,
            "fix_suggestions": fix_suggestions,
            "llm_detection": llm_det,
        }, indent=2))

    if secret_findings:
        sys.exit(2)


if __name__ == "__main__":
    main()
