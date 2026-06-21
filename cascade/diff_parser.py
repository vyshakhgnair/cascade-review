import re
from dataclasses import dataclass, field
from typing import List

@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[str] = field(default_factory=list)

@dataclass
class FileDiff:
    path: str
    language: str
    added_lines: List[str] = field(default_factory=list)
    removed_lines: List[str] = field(default_factory=list)
    hunks: List[DiffHunk] = field(default_factory=list)
    changed_functions: List[str] = field(default_factory=list)
    total_changes: int = 0

LANGUAGE_MAP = {
    '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
    '.java': 'java', '.go': 'go', '.rs': 'rust', '.cpp': 'cpp',
    '.c': 'c', '.cs': 'csharp', '.rb': 'ruby', '.php': 'php',
    '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
}

FUNCTION_PATTERNS = {
    'python':     r'^\+\s*(?:async\s+)?def\s+(\w+)',
    'javascript': r'^\+\s*(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\())',
    'typescript': r'^\+\s*(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=)',
    'java':       r'^\+\s*(?:public|private|protected|static|\s)+\w+\s+(\w+)\s*\(',
    'go':         r'^\+func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)',
}

def detect_language(path: str) -> str:
    for ext, lang in LANGUAGE_MAP.items():
        if path.endswith(ext):
            return lang
    return 'unknown'

def extract_changed_functions(lines: List[str], language: str) -> List[str]:
    pattern = FUNCTION_PATTERNS.get(language, r'^\+\s*(?:def|function|func)\s+(\w+)')
    functions = []
    for line in lines:
        match = re.search(pattern, line)
        if match:
            name = next((g for g in match.groups() if g), None) if match.groups() else match.group(1)
            if name:
                functions.append(name)
    return list(set(functions))

def parse_diff(diff_text: str) -> List[FileDiff]:
    files: List[FileDiff] = []
    current_file: FileDiff = None
    current_hunk: DiffHunk = None

    for line in diff_text.splitlines():
        if line.startswith('diff --git'):
            if current_file:
                files.append(current_file)
            path_match = re.search(r'b/(.+)$', line)
            path = path_match.group(1) if path_match else 'unknown'
            current_file = FileDiff(path=path, language=detect_language(path))
            current_hunk = None

        elif line.startswith('@@') and current_file:
            m = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if m:
                current_hunk = DiffHunk(
                    old_start=int(m.group(1)), old_count=int(m.group(2) or 1),
                    new_start=int(m.group(3)), new_count=int(m.group(4) or 1),
                )
                current_file.hunks.append(current_hunk)

        elif current_file and current_hunk:
            if line.startswith('+') and not line.startswith('+++'):
                current_file.added_lines.append(line[1:])
                current_hunk.lines.append(line)
            elif line.startswith('-') and not line.startswith('---'):
                current_file.removed_lines.append(line[1:])
                current_hunk.lines.append(line)

    if current_file:
        files.append(current_file)

    for f in files:
        f.total_changes = len(f.added_lines) + len(f.removed_lines)
        f.changed_functions = extract_changed_functions(f.added_lines, f.language)

    return files
