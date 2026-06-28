import os
import tempfile
import yaml
from cascade.diff_parser import FileDiff
from cascade.policy import evaluate


def _file(path, added_lines):
    return FileDiff(path=path, language="python", added_lines=added_lines)


def _with_rules(rules, files):
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = os.path.join(tmpdir, ".cascade-rules.yml")
        with open(rules_path, "w") as f:
            yaml.dump({"rules": rules}, f)
        return evaluate(files, repo_root=tmpdir)


def test_pattern_match():
    violations = _with_rules(
        [{"name": "no-todo", "pattern": "TODO", "message": "No TODOs", "severity": "WARNING"}],
        [_file("app.py", ["# TODO: fix this"])],
    )
    assert len(violations) == 1
    assert violations[0].rule == "no-todo"


def test_pattern_no_match():
    violations = _with_rules(
        [{"name": "no-todo", "pattern": "TODO", "message": "No TODOs"}],
        [_file("app.py", ["# all good here"])],
    )
    assert len(violations) == 0


def test_file_filter():
    violations = _with_rules(
        [{"name": "no-console", "pattern": "console\\.log", "files": "\\.js$", "message": "No console.log"}],
        [_file("app.py", ["console.log('test')"]), _file("index.js", ["console.log('test')"])],
    )
    assert len(violations) == 1
    assert violations[0].file == "index.js"


def test_forbidden_imports():
    violations = _with_rules(
        [{"name": "no-axios", "forbidden_imports": ["axios"], "files": "services/", "message": "Use shared client"}],
        [_file("services/api.js", ["const axios = require('axios')"])],
    )
    assert len(violations) == 1
    assert "forbidden import" in violations[0].description


def test_max_lines():
    violations = _with_rules(
        [{"name": "max-size", "max_lines": 5, "message": "File too large"}],
        [_file("big.py", ["line"] * 10)],
    )
    assert len(violations) == 1
    assert "10 lines" in violations[0].description


def test_require_pattern():
    violations = _with_rules(
        [{"name": "needs-assert", "require": "assert", "files": "test_", "message": "Tests need assertions", "severity": "HIGH"}],
        [_file("test_foo.py", ["def test_foo():", "    pass"])],
    )
    assert len(violations) == 1
    assert violations[0].severity == "HIGH"


def test_no_rules_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        violations = evaluate([_file("app.py", ["TODO"])], repo_root=tmpdir)
    assert violations == []
