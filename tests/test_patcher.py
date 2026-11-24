import subprocess
import sys
import tempfile
from pathlib import Path

patcher = Path(__file__).resolve().parent.parent / "scripts" / "patcher.py"
assert patcher.exists(), f"Missing patcher: {patcher}"

print(f"Testing patcher engine ({patcher.name})...")

with tempfile.TemporaryDirectory() as td:
    tpath = Path(td) / "test.py"
    tpath.write_text(
        "def foo():\n    print(1)\n    return 1\n\ndef bar():\n    print(2)\n    return 2\n",
        encoding="utf-8",
    )

    pfile = Path(td) / "patch.txt"
    pfile.write_text(
        "def foo():\n    print('updated')\n    return 42\n",
        encoding="utf-8",
    )

    # Test 1: Normal inclusive
    res = subprocess.run(
        [
            sys.executable,
            str(patcher),
            "-t",
            str(tpath),
            "-s",
            "def foo():",
            "-e",
            "return 1\n",
            "-p",
            str(pfile),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Test 1 failed: {res.stderr}\n{res.stdout}"
    assert "updated" in tpath.read_text(encoding="utf-8")
    assert (Path(td) / "test.py.bak").exists()
    print("[PASS] Test 1: Normal replacement and backup creation.")

    # Test 2: Generic end anchor rejection
    res2 = subprocess.run(
        [
            sys.executable,
            str(patcher),
            "-t",
            str(tpath),
            "-s",
            "def bar():",
            "-e",
            "}",
            "-p",
            str(pfile),
        ],
        capture_output=True,
        text=True,
    )
    assert res2.returncode == 1, "Test 2 should fail on generic anchor"
    assert "too generic" in res2.stderr
    print("[PASS] Test 2: Generic anchor rejection.")

    # Test 3: Unbalanced brackets
    bad_patch = Path(td) / "bad.txt"
    bad_patch.write_text("def bar():\n    if True: {\n    return 2\n", encoding="utf-8")
    res3 = subprocess.run(
        [
            sys.executable,
            str(patcher),
            "-t",
            str(tpath),
            "-s",
            "def bar():",
            "-e",
            "return 2\n",
            "-p",
            str(bad_patch),
        ],
        capture_output=True,
        text=True,
    )
    assert res3.returncode == 1, "Test 3 should fail on unbalanced braces"
    assert "unbalanced" in res3.stderr
    print("[PASS] Test 3: Delimiter balance detection.")

    # Test 4: Shrink guard
    empty_patch = Path(td) / "empty.txt"
    empty_patch.write_text("", encoding="utf-8")
    res4 = subprocess.run(
        [
            sys.executable,
            str(patcher),
            "-t",
            str(tpath),
            "-s",
            "def foo():",
            "-e",
            "return 2\n",
            "-p",
            str(empty_patch),
        ],
        capture_output=True,
        text=True,
    )
    assert res4.returncode == 1, "Test 4 should fail on shrink"
    assert "shrank" in res4.stderr
    print("[PASS] Test 4: Truncation and shrink guard.")

    # Test 5: Allow shrink override
    res5 = subprocess.run(
        [
            sys.executable,
            str(patcher),
            "-t",
            str(tpath),
            "-s",
            "def foo():",
            "-e",
            "return 2\n",
            "-p",
            str(empty_patch),
            "--allow-shrink",
            "--syntax-check",
            "none",
        ],
        capture_output=True,
        text=True,
    )
    assert res5.returncode == 0, f"Test 5 failed: {res5.stderr}"
    print("[PASS] Test 5: Shrink threshold override.")

    # Test 6: Python AST syntax check
    bad_syntax = Path(td) / "bad_syntax.txt"
    bad_syntax.write_text("def foo():\n    return (\n", encoding="utf-8")
    tpath.write_text("def foo():\n    return 1\n", encoding="utf-8")
    res6 = subprocess.run(
        [
            sys.executable,
            str(patcher),
            "-t",
            str(tpath),
            "-s",
            "def foo():",
            "-e",
            "return 1\n",
            "-p",
            str(bad_syntax),
        ],
        capture_output=True,
        text=True,
    )
    assert res6.returncode == 1, "Test 6 should fail on Python SyntaxError"
    assert "SyntaxError" in res6.stderr or "Syntax safety" in res6.stderr
    print("[PASS] Test 6: AST syntax validation.")

print("\nStatus: All test cases passed successfully.")
