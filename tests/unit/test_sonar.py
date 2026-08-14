
from cascade.diff_parser import FileDiff
from cascade.analyzers.static.sonar import _check_python

def test_S5754():
    findings = _check_python(
        FileDiff(path="test.py", language="python", 
                 added_lines=['try:', '    call()', 'except:'])
    )
    assert any(f.rule_id == "S5754" for f in findings)

def test_S5754_specific_exception():
    findings = _check_python(
        FileDiff(path="test.py", language="python", 
                 added_lines=['try:', '    call()', 'except ValueError:'])
    )
    assert not any(f.rule_id == "S5754" for f in findings)