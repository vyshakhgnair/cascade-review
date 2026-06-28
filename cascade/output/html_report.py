import html
from typing import List


def render(summary, secrets, sonar, blast, risk, bugs, fixes=None,
           breakers=None, conflicts=None, policy_violations=None, drifts=None,
           llm_det=None, routing=None) -> str:

    secret_count = len(secrets) if secrets else 0
    sonar_count = len(sonar) if sonar else 0
    breaker_count = len(breakers) if breakers else 0
    bug_count = len(bugs) if bugs else 0
    drift_count = len(drifts) if drifts else 0
    conflict_count = len(conflicts) if conflicts else 0
    policy_count = len(policy_violations) if policy_violations else 0
    total = secret_count + sonar_count + breaker_count + bug_count + drift_count + conflict_count + policy_count

    sev_colors = {
        "CRITICAL": "#e24b4a", "HIGH": "#e24b4a", "MAJOR": "#ba7517",
        "WARNING": "#ba7517", "MEDIUM": "#ba7517", "MINOR": "#3b82f6",
        "INFO": "#3b82f6", "LOW": "#22c55e",
    }

    def sev_badge(sev):
        color = sev_colors.get(sev, "#888")
        return f'<span class="badge" style="background:{color}">{html.escape(sev)}</span>'

    def e(text):
        return html.escape(str(text))

    sections = []

    # Summary card
    change_type = summary.get("type", "UNKNOWN") if summary else "UNKNOWN"
    summary_text = summary.get("summary", "") if summary else ""
    tier = routing.get("tier", "—") if routing else "—"
    sections.append(f'''
    <div class="cards">
      <div class="card">
        <div class="card-label">Findings</div>
        <div class="card-value {'card-danger' if total > 0 else 'card-ok'}">{total}</div>
      </div>
      <div class="card">
        <div class="card-label">Regression Risk</div>
        <div class="card-value">{risk.score}/10</div>
        <div class="risk-bar"><div class="risk-fill" style="width:{risk.score * 10}%"></div></div>
      </div>
      <div class="card">
        <div class="card-label">Secrets</div>
        <div class="card-value {'card-danger' if secret_count else 'card-ok'}">{secret_count}</div>
      </div>
      <div class="card">
        <div class="card-label">Build Breakers</div>
        <div class="card-value {'card-danger' if breaker_count else 'card-ok'}">{breaker_count}</div>
      </div>
    </div>
    <div class="summary-bar">
      <span><b>Type:</b> {e(change_type)}</span>
      <span><b>Tier:</b> {e(tier)}</span>
      <span><b>Risk:</b> {e(risk.level)}</span>
    </div>
    ''')
    if summary_text:
        sections.append(f'<p class="summary-text">{e(summary_text)}</p>')

    # Secrets
    if secrets:
        rows = "".join(
            f'<tr><td>{sev_badge("CRITICAL")}</td><td><code>{e(s.secret_type)}</code></td>'
            f'<td><code>{e(s.file)}</code></td><td class="mono">{e(s.line_content[:80])}</td></tr>'
            for s in secrets
        )
        sections.append(f'''
        <div class="section danger">
          <h2>⛔ Secrets Detected</h2>
          <p class="warn">Stop. Do not merge. Remove these before pushing.</p>
          <table><thead><tr><th>Severity</th><th>Type</th><th>File</th><th>Content</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </div>''')

    # Build breakers
    if breakers:
        rows = "".join(
            f'<tr><td>{sev_badge(b.severity)}</td><td><code>{e(b.check)}</code></td>'
            f'<td>{e(b.description)}</td><td><code>{e(b.file)}</code></td></tr>'
            for b in breakers
        )
        sections.append(f'''
        <div class="section warning">
          <h2>🚧 Build Breakers</h2>
          <table><thead><tr><th>Severity</th><th>Check</th><th>Issue</th><th>File</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </div>''')

    # Sonar
    if sonar:
        rows = "".join(
            f'<tr><td>{sev_badge(f.severity)}</td><td><code>{e(f.rule_id)}</code></td>'
            f'<td>{e(f.description)}</td><td>{e(f.debt)}</td></tr>'
            for f in sonar
        )
        sections.append(f'''
        <div class="section">
          <h2>SonarQube Simulation</h2>
          <table><thead><tr><th>Severity</th><th>Rule</th><th>Issue</th><th>Est. Fix</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </div>''')

    # Blast radius
    if blast and blast.affected_files:
        rows = "".join(
            f'<tr><td><code>{e(path)}</code></td><td><code>{e(", ".join(syms))}</code></td></tr>'
            for path, syms in list(blast.affected_files.items())[:10]
        )
        sections.append(f'''
        <div class="section">
          <h2>Blast Radius — {sev_badge(blast.risk_level)}</h2>
          {"<p>Changed: <code>" + e(", ".join(blast.changed_symbols)) + "</code></p>" if blast.changed_symbols else ""}
          <table><thead><tr><th>Affected File</th><th>Uses Symbols</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </div>''')

    # Architecture drift
    if drifts:
        rows = "".join(
            f'<tr><td>{sev_badge(d.severity)}</td><td><code>{e(d.file)}</code></td><td>{e(d.description)}</td></tr>'
            for d in drifts
        )
        sections.append(f'''
        <div class="section">
          <h2>Architecture Drift</h2>
          <table><thead><tr><th>Severity</th><th>File</th><th>Issue</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </div>''')

    # Version conflicts
    if conflicts:
        rows = "".join(
            f'<tr><td>{sev_badge(c.severity)}</td><td><code>{e(c.package)}</code></td><td>{e(c.description)}</td></tr>'
            for c in conflicts
        )
        sections.append(f'''
        <div class="section warning">
          <h2>⚠ Version Conflicts</h2>
          <table><thead><tr><th>Severity</th><th>Package</th><th>Details</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </div>''')

    # Policy violations
    if policy_violations:
        rows = "".join(
            f'<tr><td>{sev_badge(v.severity)}</td><td><code>{e(v.rule)}</code></td>'
            f'<td>{e(v.description)}</td><td><code>{e(v.file)}</code></td></tr>'
            for v in policy_violations
        )
        sections.append(f'''
        <div class="section">
          <h2>Policy Violations</h2>
          <table><thead><tr><th>Severity</th><th>Rule</th><th>Issue</th><th>File</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </div>''')

    # Bugs
    if bugs:
        rows = "".join(
            f'<tr><td>{sev_badge(b.get("severity", "WARNING"))}</td><td>{e(b.get("description", ""))}</td></tr>'
            for b in bugs
        )
        sections.append(f'''
        <div class="section">
          <h2>Bugs Found</h2>
          <table><thead><tr><th>Severity</th><th>Description</th></tr></thead>
          <tbody>{rows}</tbody></table>
        </div>''')

    # LLM detection
    if llm_det and llm_det.get("verdict") == "YES":
        sections.append(f'''
        <div class="section warning">
          <h2>AI-Generated Code Suspected</h2>
          <p>Confidence: <b>{e(llm_det.get("confidence", ""))}</b></p>
          <p>{e(llm_det.get("reason", ""))}</p>
        </div>''')

    # Fixes
    if fixes:
        items = "".join(
            f'<li>{e(fix.get("description", ""))} <span class="mono">({e(fix.get("effort", "small"))})</span></li>'
            for fix in fixes
        )
        sections.append(f'''
        <div class="section">
          <h2>Suggested Fixes</h2>
          <ul>{items}</ul>
        </div>''')

    body = "\n".join(sections)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cascade Review Report</title>
<style>
:root {{
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #e6edf3; --text-dim: #8b949e; --accent: #58a6ff;
  --danger: #e24b4a; --warn: #ba7517; --ok: #22c55e;
}}
@media (prefers-color-scheme: light) {{
  :root {{
    --bg: #f6f8fa; --surface: #fff; --border: #d0d7de;
    --text: #1f2328; --text-dim: #656d76; --accent: #0969da;
    --danger: #cf222e; --warn: #9a6700; --ok: #1a7f37;
  }}
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6; padding: 24px; max-width: 960px; margin: 0 auto; }}
h1 {{ font-size: 20px; margin-bottom: 4px; }}
h2 {{ font-size: 16px; margin-bottom: 12px; }}
.header {{ margin-bottom: 24px; }}
.header small {{ color: var(--text-dim); font-size: 13px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; text-align: center; }}
.card-label {{ font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; }}
.card-value {{ font-size: 28px; font-weight: 600; margin: 4px 0; }}
.card-danger {{ color: var(--danger); }}
.card-ok {{ color: var(--ok); }}
.risk-bar {{ height: 6px; background: var(--border); border-radius: 3px; margin-top: 6px; }}
.risk-fill {{ height: 100%; border-radius: 3px; background: linear-gradient(90deg, var(--ok), var(--warn), var(--danger)); }}
.summary-bar {{ display: flex; gap: 20px; font-size: 14px; color: var(--text-dim); margin-bottom: 12px; flex-wrap: wrap; }}
.summary-text {{ font-size: 14px; color: var(--text-dim); margin-bottom: 20px; }}
.section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
.section.danger {{ border-color: var(--danger); }}
.section.warning {{ border-color: var(--warn); }}
.warn {{ color: var(--danger); font-weight: 600; margin-bottom: 10px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); color: var(--text-dim);
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }}
tr:last-child td {{ border-bottom: none; }}
code {{ font-size: 12px; background: var(--bg); padding: 2px 5px; border-radius: 3px; }}
.mono {{ font-family: monospace; font-size: 12px; color: var(--text-dim); }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; color: #fff;
  font-size: 11px; font-weight: 600; text-transform: uppercase; }}
ul {{ padding-left: 20px; font-size: 14px; }}
li {{ margin-bottom: 6px; }}
.footer {{ text-align: center; color: var(--text-dim); font-size: 12px; margin-top: 24px; padding-top: 16px;
  border-top: 1px solid var(--border); }}
.footer a {{ color: var(--accent); text-decoration: none; }}
</style>
</head>
<body>
<div class="header">
  <h1>Cascade Review Report</h1>
  <small>Generated by cascade-review v0.2.0</small>
</div>
{body}
<div class="footer">
  <a href="https://github.com/vyshakhgnair/cascade-review">cascade-review</a> — free AI code reviewer
</div>
</body>
</html>'''
