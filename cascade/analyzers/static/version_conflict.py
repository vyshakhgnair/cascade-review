import json
import re
from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path
from cascade.diff_parser import FileDiff


@dataclass
class VersionConflict:
    package: str
    locations: Dict[str, str]
    description: str
    severity: str = "HIGH"


def _parse_version(spec: str) -> str:
    return re.sub(r'^[~^>=<! ]+', '', spec.strip()).split(',')[0].strip()


def _scan_package_jsons(root: Path) -> Dict[str, Dict[str, str]]:
    registry = {}
    for pkg_file in root.rglob("package.json"):
        if "node_modules" in pkg_file.parts:
            continue
        try:
            pkg = json.loads(pkg_file.read_text(errors="ignore"))
        except Exception:
            continue
        rel = str(pkg_file.relative_to(root))
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name, version in pkg.get(section, {}).items():
                if name not in registry:
                    registry[name] = {}
                registry[name][rel] = _parse_version(version)
    return registry


def _scan_requirements(root: Path) -> Dict[str, Dict[str, str]]:
    registry = {}
    for req_file in root.rglob("requirements*.txt"):
        if "node_modules" in req_file.parts or "vendor" in req_file.parts:
            continue
        rel = str(req_file.relative_to(root))
        for line in req_file.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            m = re.match(r'([a-zA-Z0-9_-]+)\s*([>=<~!]+.+)?', line)
            if m:
                name = m.group(1).lower().replace("-", "_")
                version = _parse_version(m.group(2)) if m.group(2) else "*"
                if name not in registry:
                    registry[name] = {}
                registry[name][rel] = version
    return registry


def analyze(files: List[FileDiff], repo_root: str = ".") -> List[VersionConflict]:
    root = Path(repo_root)
    conflicts = []

    changed_paths = {f.path for f in files}
    has_dep_change = any(
        "package.json" in p or "requirements" in p or "pyproject.toml" in p
        for p in changed_paths
    )
    if not has_dep_change:
        return conflicts

    js_reg = _scan_package_jsons(root)
    for pkg, locations in js_reg.items():
        versions = set(locations.values())
        versions.discard("*")
        if len(versions) > 1:
            loc_str = ", ".join(f"{f}: {v}" for f, v in locations.items())
            conflicts.append(VersionConflict(
                package=pkg,
                locations=locations,
                description=f"'{pkg}' has conflicting versions across workspaces: {loc_str}",
            ))

    py_reg = _scan_requirements(root)
    for pkg, locations in py_reg.items():
        versions = set(locations.values())
        versions.discard("*")
        if len(versions) > 1:
            loc_str = ", ".join(f"{f}: {v}" for f, v in locations.items())
            conflicts.append(VersionConflict(
                package=pkg,
                locations=locations,
                description=f"'{pkg}' has conflicting versions: {loc_str}",
            ))

    return conflicts
