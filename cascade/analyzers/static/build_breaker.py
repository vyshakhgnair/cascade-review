import re
import os
import json
from dataclasses import dataclass
from typing import List
from pathlib import Path
from cascade.diff_parser import FileDiff

@dataclass
class BuildBreaker:
    check: str
    file: str
    description: str
    severity: str = "HIGH"

def _find_file(root: Path, *names) -> Path | None:
    for n in names:
        p = root / n
        if p.exists():
            return p
    return None

def _check_missing_deps(files: List[FileDiff], root: Path) -> List[BuildBreaker]:
    findings = []

    py_imports = set()
    js_requires = set()
    for f in files:
        added = "\n".join(f.added_lines)
        if f.language == "python":
            py_imports.update(re.findall(r'^\s*(?:import|from)\s+([a-zA-Z_]\w*)', added, re.M))
        elif f.language in ("javascript", "typescript"):
            js_requires.update(re.findall(r'''(?:require\s*\(\s*['"]([^./'"@][^'"]*?)['"]|from\s+['"]([^./'"@][^'"]*?)['"]\s*[;)])''', added))

    if py_imports:
        stdlib = _python_stdlib()
        reqs_file = _find_file(root, "requirements.txt", "requirements/base.txt")
        installed = set()
        if reqs_file:
            for line in reqs_file.read_text(errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    installed.add(re.split(r'[>=<!\[]', line)[0].strip().lower().replace("-", "_"))
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(errors="ignore")
            for dep in re.findall(r'"([a-zA-Z0-9_-]+)(?:[>=<!\[].*?)?"', content):
                installed.add(dep.lower().replace("-", "_"))

        for imp in py_imports:
            normalized = imp.lower().replace("-", "_")
            if normalized not in stdlib and normalized not in installed:
                pkg_dir = root / imp
                if not pkg_dir.is_dir() and not (root / f"{imp}.py").exists():
                    findings.append(BuildBreaker(
                        check="MISSING_DEP", file="requirements.txt",
                        description=f"'{imp}' is imported but not in requirements.txt or pyproject.toml",
                    ))

    if js_requires:
        pkg_json = root / "package.json"
        declared = set()
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text(errors="ignore"))
                for section in ("dependencies", "devDependencies", "peerDependencies"):
                    declared.update(pkg.get(section, {}).keys())
            except Exception:
                pass
        flat = set()
        for match in js_requires:
            name = match[0] or match[1]
            flat.add(name.split("/")[0] if name.startswith("@") else name.split("/")[0])
        for dep in flat:
            if dep and dep not in declared and not dep.startswith("node:"):
                findings.append(BuildBreaker(
                    check="MISSING_DEP", file="package.json",
                    description=f"'{dep}' is required/imported but not in package.json",
                ))

    return findings


def _check_dev_in_prod(files: List[FileDiff], root: Path) -> List[BuildBreaker]:
    findings = []
    pkg_json = root / "package.json"
    if not pkg_json.exists():
        return findings
    try:
        pkg = json.loads(pkg_json.read_text(errors="ignore"))
    except Exception:
        return findings
    dev_only = set(pkg.get("devDependencies", {}).keys())
    prod_deps = set(pkg.get("dependencies", {}).keys())

    for f in files:
        if f.language not in ("javascript", "typescript"):
            continue
        if any(kw in f.path.lower() for kw in ("test", "spec", "jest", "__test", "cypress", "storybook", ".config")):
            continue
        added = "\n".join(f.added_lines)
        for dep in dev_only:
            if dep in prod_deps:
                continue
            if re.search(r'''(?:require\s*\(\s*['"]''' + re.escape(dep) + r'''['"]|from\s+['"]''' + re.escape(dep) + r'''['"])''', added):
                findings.append(BuildBreaker(
                    check="DEV_IN_PROD", file=f.path,
                    description=f"'{dep}' is a devDependency but imported in production code",
                ))
    return findings


def _check_case_sensitivity(files: List[FileDiff], root: Path) -> List[BuildBreaker]:
    findings = []
    for f in files:
        added = "\n".join(f.added_lines)
        if f.language == "python":
            imports = re.findall(r'from\s+(\S+)\s+import|import\s+(\S+)', added)
            for match in imports:
                mod = match[0] or match[1]
                parts = mod.split(".")
                path = root
                for part in parts:
                    candidates = list(path.glob(f"{part}*")) if path.is_dir() else []
                    real = [c for c in candidates if c.stem == part]
                    case_mismatch = [c for c in candidates if c.stem.lower() == part.lower() and c.stem != part]
                    if case_mismatch and not real:
                        findings.append(BuildBreaker(
                            check="CASE_SENSITIVITY", file=f.path,
                            description=f"Import '{mod}' — actual file is '{case_mismatch[0].name}' (case mismatch, breaks on Linux CI)",
                            severity="CRITICAL",
                        ))
                    if real:
                        path = real[0]
                    else:
                        break

        elif f.language in ("javascript", "typescript"):
            local_imports = re.findall(r'''(?:require\s*\(\s*['"](\./[^'"]+)['"]|from\s+['"](\./[^'"]+)['"]\s*[;)])''', added)
            for match in local_imports:
                rel = match[0] or match[1]
                target = (Path(f.path).parent / rel)
                for ext in ("", ".js", ".ts", ".tsx", ".jsx"):
                    check_path = root / f"{target}{ext}"
                    if check_path.exists():
                        break
                    parent = check_path.parent
                    if parent.is_dir():
                        stem = check_path.stem
                        case_mismatch = [c for c in parent.iterdir() if c.stem.lower() == stem.lower() and c.stem != stem]
                        if case_mismatch:
                            findings.append(BuildBreaker(
                                check="CASE_SENSITIVITY", file=f.path,
                                description=f"Import '{rel}' — actual file is '{case_mismatch[0].name}' (case mismatch, breaks on Linux CI)",
                                severity="CRITICAL",
                            ))
                            break
    return findings


def _check_deleted_imports(files: List[FileDiff], root: Path) -> List[BuildBreaker]:
    findings = []
    deleted_symbols = set()
    for f in files:
        for line in f.removed_lines:
            for m in re.finditer(r'\bdef\s+(\w+)|class\s+(\w+)|(?:function|const|let|var)\s+(\w+)', line):
                name = next((g for g in m.groups() if g), None)
                if name:
                    deleted_symbols.add((name, f.path))

    if not deleted_symbols:
        return findings

    changed_paths = {f.path for f in files}
    added_text = {f.path: "\n".join(f.added_lines) for f in files}

    for sym, origin in deleted_symbols:
        if sym in added_text.get(origin, ""):
            continue
        for glob in ("*.py", "*.js", "*.ts", "*.tsx", "*.jsx"):
            for src in root.rglob(glob):
                if "node_modules" in src.parts or "vendor" in src.parts:
                    continue
                rel = str(src.relative_to(root))
                if rel == origin:
                    continue
                try:
                    content = src.read_text(encoding="utf-8", errors="ignore")
                    if re.search(r'\b' + re.escape(sym) + r'\b', content):
                        origin_module = Path(origin).stem
                        if re.search(r'(?:from|import)\s+.*' + re.escape(origin_module), content):
                            findings.append(BuildBreaker(
                                check="DELETED_SYMBOL", file=rel,
                                description=f"'{sym}' was removed from {origin} but is still imported in {rel}",
                                severity="CRITICAL",
                            ))
                except Exception:
                    continue
    return findings


def _check_platform_paths(files: List[FileDiff]) -> List[BuildBreaker]:
    findings = []
    for f in files:
        added = "\n".join(f.added_lines)
        if re.search(r'["\'][A-Z]:\\\\', added):
            findings.append(BuildBreaker(
                check="PLATFORM_PATH", file=f.path,
                description="Hardcoded Windows path (C:\\\\) — will break on Linux/Mac CI",
            ))
        if re.search(r'["\']/Users/\w+', added) or re.search(r'["\']/home/\w+', added):
            findings.append(BuildBreaker(
                check="PLATFORM_PATH", file=f.path,
                description="Hardcoded user home path — use os.path.expanduser or $HOME",
            ))
        if f.language == "python" and re.search(r'''['"][^'"]*\\[^\\nrt'"0]''', added):
            if not re.search(r'''r['"]''', added):
                backslash_paths = re.findall(r'''['"]([^'"]*\\[^\\nrt'"0][^'"]*?)['"]''', added)
                for bp in backslash_paths:
                    if "\\" in bp and ("/" not in bp):
                        findings.append(BuildBreaker(
                            check="PLATFORM_PATH", file=f.path,
                            description=f"Backslash in string '{bp[:40]}' — use pathlib or forward slashes",
                        ))
                        break
    return findings


def _check_lockfile_drift(files: List[FileDiff], root: Path) -> List[BuildBreaker]:
    findings = []
    changed_paths = {f.path for f in files}

    if "package.json" in changed_paths:
        has_lock = any(n in changed_paths for n in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml"))
        lock_exists = any((root / n).exists() for n in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml"))
        if not has_lock and lock_exists:
            findings.append(BuildBreaker(
                check="LOCKFILE_DRIFT", file="package.json",
                description="package.json changed but lock file not updated — run npm install / yarn",
            ))

    if "pyproject.toml" in changed_paths or "setup.py" in changed_paths or "requirements.txt" in changed_paths:
        lock_names = ("poetry.lock", "Pipfile.lock", "pdm.lock")
        has_lock = any(n in changed_paths for n in lock_names)
        lock_exists = any((root / n).exists() for n in lock_names)
        if not has_lock and lock_exists:
            findings.append(BuildBreaker(
                check="LOCKFILE_DRIFT", file="pyproject.toml",
                description="Dependencies changed but lock file not updated — run poetry lock / pipenv lock",
            ))

    return findings


def _check_large_files(files: List[FileDiff]) -> List[BuildBreaker]:
    findings = []
    BINARY_EXTS = {".exe", ".dll", ".so", ".dylib", ".zip", ".tar", ".gz", ".jar",
                   ".bin", ".dat", ".db", ".sqlite", ".sqlite3", ".whl", ".pkl",
                   ".h5", ".hdf5", ".parquet", ".feather", ".model", ".onnx",
                   ".mp4", ".mov", ".avi", ".mp3", ".wav", ".psd", ".ai"}
    for f in files:
        ext = Path(f.path).suffix.lower()
        if ext in BINARY_EXTS:
            findings.append(BuildBreaker(
                check="LARGE_FILE", file=f.path,
                description=f"Binary file '{f.path}' committed — use .gitignore or Git LFS",
                severity="WARNING",
            ))
        if f.total_changes > 5000:
            findings.append(BuildBreaker(
                check="LARGE_FILE", file=f.path,
                description=f"Extremely large diff ({f.total_changes} lines) — possible data dump or generated file",
                severity="WARNING",
            ))
    return findings


def _check_env_vars(files: List[FileDiff], root: Path) -> List[BuildBreaker]:
    findings = []
    new_env_refs = set()
    for f in files:
        added = "\n".join(f.added_lines)
        new_env_refs.update(re.findall(r'os\.environ\[[\'"]([\w]+)[\'"]\]', added))
        new_env_refs.update(re.findall(r'os\.getenv\([\'"]([\w]+)[\'"]', added))
        new_env_refs.update(re.findall(r'process\.env\.([\w]+)', added))

    if not new_env_refs:
        return findings

    documented = set()
    for name in (".env.example", ".env.sample", ".env.template"):
        env_file = root / name
        if env_file.exists():
            for line in env_file.read_text(errors="ignore").splitlines():
                m = re.match(r'(\w+)\s*=', line)
                if m:
                    documented.add(m.group(1))

    for var in new_env_refs:
        if var not in documented and var not in ("PATH", "HOME", "USER", "SHELL", "PWD", "TERM", "LANG", "NODE_ENV", "DEBUG"):
            findings.append(BuildBreaker(
                check="MISSING_ENV_VAR", file=".env.example",
                description=f"Env var '{var}' used in code but not documented in .env.example",
                severity="WARNING",
            ))

    return findings


def _python_stdlib() -> set:
    return {
        "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio", "asyncore",
        "atexit", "audioop", "base64", "bdb", "binascii", "binhex", "bisect",
        "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd",
        "code", "codecs", "codeop", "collections", "colorsys", "compileall",
        "concurrent", "configparser", "contextlib", "contextvars", "copy", "copyreg",
        "cProfile", "crypt", "csv", "ctypes", "curses", "dataclasses", "datetime",
        "dbm", "decimal", "difflib", "dis", "distutils", "doctest", "email",
        "encodings", "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
        "fnmatch", "formatter", "fractions", "ftplib", "functools", "gc", "getopt",
        "getpass", "gettext", "glob", "grp", "gzip", "hashlib", "heapq", "hmac",
        "html", "http", "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect",
        "io", "ipaddress", "itertools", "json", "keyword", "lib2to3", "linecache",
        "locale", "logging", "lzma", "mailbox", "mailcap", "marshal", "math",
        "mimetypes", "mmap", "modulefinder", "multiprocessing", "netrc", "nis",
        "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev",
        "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
        "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
        "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random",
        "re", "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
        "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
        "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
        "sqlite3", "ssl", "stat", "statistics", "string", "stringprep", "struct",
        "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog", "tabnanny",
        "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap", "threading",
        "time", "timeit", "tkinter", "token", "tokenize", "tomllib", "trace",
        "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types",
        "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
        "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport",
        "zlib", "_thread",
    }


def analyze(files: List[FileDiff], repo_root: str = ".") -> List[BuildBreaker]:
    root = Path(repo_root)
    findings = []
    findings.extend(_check_missing_deps(files, root))
    findings.extend(_check_dev_in_prod(files, root))
    findings.extend(_check_case_sensitivity(files, root))
    findings.extend(_check_deleted_imports(files, root))
    findings.extend(_check_platform_paths(files))
    findings.extend(_check_lockfile_drift(files, root))
    findings.extend(_check_large_files(files))
    findings.extend(_check_env_vars(files, root))
    return findings
