import re
from dataclasses import dataclass
from typing import List
from cascade.diff_parser import FileDiff

@dataclass
class SecretFinding:
    file: str
    line_content: str
    secret_type: str
    severity: str = "CRITICAL"

SECRET_PATTERNS = [
    (r'(?i)(api_key|apikey|api-key)\s*=\s*["\']([A-Za-z0-9_\-]{20,})["\']', "API Key"),
    (r'(?i)(password|passwd|pwd)\s*=\s*["\']([^"\']{8,})["\']', "Password"),
    (r'(?i)(secret|token)\s*=\s*["\']([A-Za-z0-9_\-]{20,})["\']', "Secret Token"),
    (r'sk-[A-Za-z0-9]{48}', "OpenAI API Key"),
    (r'gsk_[A-Za-z0-9]{52}', "Groq API Key"),
    (r'AIza[0-9A-Za-z\-_]{35}', "Google API Key"),
    (r'(?i)aws_access_key_id\s*=\s*["\']?([A-Z0-9]{20})["\']?', "AWS Access Key"),
    (r'(?i)aws_secret_access_key\s*=\s*["\']?([A-Za-z0-9/+=]{40})["\']?', "AWS Secret Key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub Personal Token"),
    (r'(?i)private_key\s*=\s*["\']-----BEGIN', "Private Key"),
    (r'(?i)bearer\s+[A-Za-z0-9\-_]{20,}', "Bearer Token"),
]

def scan(files: List[FileDiff]) -> List[SecretFinding]:
    findings = []
    for f in files:
        for line in f.added_lines:
            for pattern, secret_type in SECRET_PATTERNS:
                if re.search(pattern, line):
                    preview = line.strip()
                    if len(preview) > 80:
                        preview = preview[:77] + "..."
                    findings.append(SecretFinding(
                        file=f.path,
                        line_content=preview,
                        secret_type=secret_type,
                    ))
                    break
    return findings
