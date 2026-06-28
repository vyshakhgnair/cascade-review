from cascade.diff_parser import FileDiff
from cascade.redact import redact_diff


def _file(added_lines):
    return [FileDiff(path="test.py", language="python", added_lines=added_lines)]


def test_redacts_strings():
    result = redact_diff(_file(['name = "secret_value"']))
    assert "secret_value" not in result[0].added_lines[0]
    assert "STR_" in result[0].added_lines[0]


def test_redacts_numbers():
    result = redact_diff(_file(["count = 42"]))
    assert "42" not in result[0].added_lines[0]
    assert "NUM_" in result[0].added_lines[0]


def test_preserves_structure():
    result = redact_diff(_file(['x = "hello"']))
    line = result[0].added_lines[0]
    assert line.startswith("x = ")
    assert '"' in line


def test_preserves_path():
    result = redact_diff(_file(["pass"]))
    assert result[0].path == "test.py"
    assert result[0].language == "python"


def test_unique_tokens():
    result = redact_diff(_file(['"aaa"', '"bbb"']))
    tokens = [l for l in result[0].added_lines]
    assert tokens[0] != tokens[1]
