import json
import os
import subprocess


def post_inline_comments(findings: list, repo: str = None, pr_number: int = None,
                         commit_sha: str = None):
    if not pr_number or not repo:
        return []

    comments = []
    for f in findings:
        file_path = f.get("file") or f.get("path", "")
        line = f.get("line", 1)
        body = f"**cascade** [{f.get('severity', 'INFO')}] {f.get('description', '')}"
        if f.get("rule_id") or f.get("check"):
            body += f"\n`{f.get('rule_id') or f.get('check')}`"

        comments.append({
            "path": file_path,
            "line": line,
            "side": "RIGHT",
            "body": body,
        })

    return comments


def format_github_review(comments: list, summary: str = "") -> dict:
    return {
        "body": summary or "## Cascade Review\nAutomated findings from cascade-review.",
        "event": "COMMENT",
        "comments": comments[:50],
    }
