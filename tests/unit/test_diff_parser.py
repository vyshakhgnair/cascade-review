from cascade.diff_parser import parse_diff, detect_language

def test_detect_language():
    assert detect_language("app.py") == "python"
    assert detect_language("index.js") == "javascript"
    assert detect_language("main.go") == "go"
    assert detect_language("Makefile") == "unknown"

def test_parse_empty_diff():
    assert parse_diff("") == []

def test_parse_simple_diff():
    diff = """diff --git a/app.py b/app.py
index 000000..111111 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,5 @@
 def hello():
+    name = "world"
+    return name
-    pass
"""
    files = parse_diff(diff)
    assert len(files) == 1
    assert files[0].path == "app.py"
    assert files[0].language == "python"
    assert len(files[0].added_lines) == 2
