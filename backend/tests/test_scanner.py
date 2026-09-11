"""RakshakAI scanner tests (paper §18 — secure-by-design self-scanning).

The first case is the exact vulnerable endpoint from the research proposal:
it must be flagged CRITICAL CWE-89 with a parameterized-query remediation.

    python3 tests/test_scanner.py   # standalone
    pytest -q tests/test_scanner.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.scanner import scan, scan_rules   # noqa: E402

PAPER_EXAMPLE = '''@app.get("/citizen/{id}")
def get_citizen(id):
    # VULNERABLE: Direct string interpolation
    return db.execute(
        f"SELECT * FROM citizens WHERE id={id}"
    )
'''


def test_paper_example_is_critical_cwe89():
    out = scan(PAPER_EXAMPLE)
    assert out["engine"] == "rules"                     # honest label: rules are the primary engine
    sqli = [f for f in out["findings"] if f["cwe"] == "CWE-89"]
    assert sqli, "paper's vulnerable endpoint was not flagged"
    top = sqli[0]
    assert top["severity"] == "CRITICAL"
    assert "parameterized" in top["remediation"].lower()
    assert top["line"] == 5                            # the f-string line


def test_clean_code_has_no_findings():
    clean = '''@app.get("/citizen/{id}")
def get_citizen(id: int):
    return db.fetch_one("SELECT * FROM citizens WHERE id=%s", (id,))
'''
    out = scan(clean)
    assert out["summary"]["total"] == 0, f"false positives: {out['findings']}"


def test_command_injection_and_shell_true():
    code = 'import os\nos.system("ping " + host)\nr = subprocess.run(cmd, shell=True)\n'
    out = scan(code)
    cwes = {f["cwe"] for f in out["findings"]}
    assert "CWE-78" in cwes
    assert all(f["severity"] == "CRITICAL" for f in out["findings"] if f["cwe"] == "CWE-78")


def test_hardcoded_credential_detected():
    code = 'API_KEY = "sk-live-1234567890"\npassword = "hunter2secret"\n'
    out = scan_rules(code)
    assert any(f["cwe"] == "CWE-798" for f in out)


def test_weak_hash_and_path_traversal():
    code = 'h = hashlib.md5(data)\nf = open(f"/data/{name}.txt")\n'
    out = scan_rules(code)
    cwes = {f["cwe"] for f in out}
    assert "CWE-327" in cwes and "CWE-22" in cwes


def test_comments_are_not_flagged():
    code = '# os.system("rm -rf /")\n# password = "hunter2"\n'
    assert scan_rules(code) == []


def test_api_scan_endpoint_roundtrip():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import api.main as apimod
    from fastapi.testclient import TestClient
    import tempfile
    from pathlib import Path

    apimod.BENCH_DIR = Path(tempfile.mkdtemp()) / "bench"
    with TestClient(apimod.app) as c:
        r = c.post("/api/scan", json={"code": PAPER_EXAMPLE, "filename": "api/routes.py"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["engine"] == "rules"
        assert d["summary"]["by_cwe"].get("CWE-89", 0) >= 1
        assert "human review" in d["disclosure"]


if __name__ == "__main__":
    import traceback

    tests = {k: v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)}
    passed = 0
    for name, fn in tests.items():
        try:
            fn()
            print(f"  ok    {name}")
            passed += 1
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    raise SystemExit(0 if passed == len(tests) else 1)
