"""RakshakAI repo-scanner CLI tests — walker, gate exit codes, SARIF, baseline,
explicit model failure. Loads scan_repo.py from backend/scripts (no package).

    python3 tests/test_scan_repo.py   # standalone
    pytest -q tests/test_scan_repo.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

_spec = importlib.util.spec_from_file_location(
    "scan_repo", BACKEND / "scripts" / "scan_repo.py")
scan_repo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan_repo)

from api import scanner as scanner_mod  # noqa: E402

VULN_CODE = (
    'import os\n'
    'API_KEY = "sk-live-98231-hunter2"\n'
    'def get_citizen(id):\n'
    '    return db.execute(f"SELECT * FROM citizens WHERE id={id}")\n'
)

CLEAN_CODE = (
    'def add(a: int, b: int) -> int:\n'
    '    return a + b\n'
)


def _vuln_file(tmp_path: Path, name: str = "vuln.py") -> Path:
    p = tmp_path / name
    p.write_text(VULN_CODE, encoding="utf-8")
    return p


def _json_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ───────────────────────────── exclusions & skipping ─────────────────────────

def test_walk_excludes_node_modules_and_binary(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skipme.py").write_text(VULN_CODE, encoding="utf-8")
    (tmp_path / "keep.py").write_text(CLEAN_CODE, encoding="utf-8")
    binfile = tmp_path / "binary.py"
    binfile.write_bytes(b"\x00\x01\x02" + VULN_CODE.encode("utf-8"))

    files, skipped = scan_repo.iter_files(
        [tmp_path], {".py"}, scan_repo.DEFAULT_EXCLUDE_PARTS, scan_repo.MAX_FILE_BYTES)

    names = {f.name for f in files}
    assert names == {"keep.py"}                     # node_modules pruned, binary skipped
    assert skipped["binary"] == 1


def test_walk_skips_oversize(tmp_path, monkeypatch):
    monkeypatch.setattr(scan_repo, "MAX_FILE_BYTES", 64)
    big = tmp_path / "big.py"
    big.write_text("# " + "x" * 200 + "\n", encoding="utf-8")

    files, skipped = scan_repo.iter_files(
        [tmp_path], {".py"}, set(), scan_repo.MAX_FILE_BYTES)
    assert files == [] and skipped["oversize"] == 1


# ───────────────────────────── gate exit codes ───────────────────────────────

def test_exit_1_on_vulnerable_file(tmp_path, capsys):
    _vuln_file(tmp_path)
    rc = scan_repo.run([str(tmp_path)])
    assert rc == 1
    assert "gate: FAIL" in capsys.readouterr().out


def test_exit_0_on_clean_file(tmp_path):
    (tmp_path / "clean.py").write_text(CLEAN_CODE, encoding="utf-8")
    assert scan_repo.run([str(tmp_path)]) == 0


def test_exit_2_on_missing_target(tmp_path):
    assert scan_repo.run([str(tmp_path / "nope")]) == 2


def test_exit_2_on_missing_baseline(tmp_path):
    _vuln_file(tmp_path)
    rc = scan_repo.run([str(tmp_path), "--baseline", str(tmp_path / "no_base.json")])
    assert rc == 2


# ───────────────────────────── SARIF output ──────────────────────────────────

def test_sarif_structure_and_levels(tmp_path):
    _vuln_file(tmp_path)
    sarif_path = tmp_path / "out.sarif"
    assert scan_repo.run([str(tmp_path), "--sarif", str(sarif_path)]) == 1

    s = json.loads(sarif_path.read_text(encoding="utf-8"))
    assert s["version"] == "2.1.0"
    run = s["runs"][0]
    assert run["tool"]["driver"]["name"] == "RakshakAI repo scanner"
    assert run["properties"]["filesScanned"] >= 1
    results = run["results"]
    assert results, "vulnerable file must produce SARIF results"
    for r in results:
        assert r["ruleId"].startswith("RA-CWE-")
        assert r["level"] in ("error", "warning", "note")
        assert r["fingerprints"]["rakshak/v1"]
        assert r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"].endswith(".py")
    # CRITICAL findings map to level=error
    assert any(r["level"] == "error" for r in results)


def test_sarif_fingerprints_stable_across_runs(tmp_path):
    _vuln_file(tmp_path)
    s1, s2 = tmp_path / "a.sarif", tmp_path / "b.sarif"
    scan_repo.run([str(tmp_path), "--sarif", str(s1)])
    scan_repo.run([str(tmp_path), "--sarif", str(s2)])
    r1 = json.loads(s1.read_text())["runs"][0]["results"]
    r2 = json.loads(s2.read_text())["runs"][0]["results"]
    fp1 = {r["fingerprints"]["rakshak/v1"] for r in r1}
    fp2 = {r["fingerprints"]["rakshak/v1"] for r in r2}
    assert fp1 == fp2 and fp1


# ───────────────────────────── baseline mode ─────────────────────────────────

def test_baseline_known_then_new_finding(tmp_path):
    _vuln_file(tmp_path, "known.py")
    base = tmp_path / "base.json"

    assert scan_repo.run([str(tmp_path), "--write-baseline", str(base)]) == 0
    # same finding is now known → PASS
    assert scan_repo.run([str(tmp_path), "--baseline", str(base)]) == 0
    # a NEW vulnerable file → FAIL
    _vuln_file(tmp_path, "new.py")
    assert scan_repo.run([str(tmp_path), "--baseline", str(base)]) == 1

    data = json.loads(base.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert all("fingerprint" in row for row in data["findings"])


# ───────────────────────────── model is opt-in ───────────────────────────────

def test_local_only_by_default(tmp_path):
    _vuln_file(tmp_path)
    rep = tmp_path / "rep.json"
    scan_repo.run([str(tmp_path), "--json", str(rep)])
    m = _json_report(rep)["mode"]
    assert m["model"] is False
    assert m["endpoint_mode"] == "local-only"
    assert m["model_status"] is None


def test_model_failure_is_explicit_not_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(scanner_mod, "RAKSHAK_AI_URL", "http://127.0.0.1:9")  # dead port
    _vuln_file(tmp_path)
    rep = tmp_path / "rep.json"
    scan_repo.run([str(tmp_path), "--model", "--json", str(rep)])
    m = _json_report(rep)["mode"]
    assert m["model"] is True
    assert m["model_status"] == "model_error"          # explicit, never a clean scan
    assert m["endpoint_mode"] == "local"               # localhost host disclosed
    # rules still drove the gate (vulnerable file present)
    assert _json_report(rep)["gate"] == "fail"


def test_model_not_configured_status(tmp_path, monkeypatch):
    monkeypatch.setattr(scanner_mod, "RAKSHAK_AI_URL", "")
    _vuln_file(tmp_path)
    rep = tmp_path / "rep.json"
    scan_repo.run([str(tmp_path), "--model", "--json", str(rep)])
    assert _json_report(rep)["mode"]["model_status"] == "model_not_configured"


# ───────────────────────────── disclosures ───────────────────────────────────

def test_report_carries_honest_disclosure(tmp_path):
    _vuln_file(tmp_path)
    rep = tmp_path / "rep.json"
    scan_repo.run([str(tmp_path), "--json", str(rep)])
    r = _json_report(rep)
    assert "not a runtime defense" in r["disclosure"].lower()
    assert r["mode"]["rules"] is True                  # rules always primary


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
