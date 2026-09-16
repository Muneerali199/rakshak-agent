#!/usr/bin/env python3
"""RakshakAI repo scanner — whole-repo static analysis from the command line.

The ``/scanner`` web page is an interactive single-file demo; this CLI is the
real workflow: scan an entire repository locally, emit JSON + SARIF, gate CI on
NEW findings at/above a severity threshold, and baseline known findings so the
gate fails only on what changed.

Design rules:
  * the deterministic rule engine is the PRIMARY engine — always runs, drives
    the exit code;
  * the 14B model is opt-in (``--model`` / ``--model-url``) and never blocks a
    build — its findings are reported alongside, labelled by engine;
  * the network is never implicit: without ``--model``/``--model-url`` nothing
    leaves the machine (local-only by default);
  * a model timeout or endpoint failure is an explicit ``model_error`` status,
    never a clean scan;
  * the CLI client itself is stdlib-only. (Local 14B inference is NOT covered by
    that claim — running a 14B model requires a model runtime such as vLLM.)

Exit codes:  0 = gate passed (no NEW rule findings at/above the threshold)
             1 = gate failed (new rule findings at/above the threshold)
             2 = scanner or configuration error

Usage:
  python backend/scripts/scan_repo.py backend/api backend/mesh
  python backend/scripts/scan_repo.py . --fail-on HIGH --sarif out.sarif
  python backend/scripts/scan_repo.py . --write-baseline scan_baseline.json
  python backend/scripts/scan_repo.py . --baseline scan_baseline.json
  python backend/scripts/scan_repo.py . --baseline scan_baseline.json --watch   # live re-scan
  python backend/scripts/scan_repo.py . --model            # opt-in 14B, non-blocking

Run from the repository root so file paths in baselines/SARIF are stable.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import scanner as scanner_mod  # noqa: E402  (stdlib-only client)

TOOL_NAME = "RakshakAI repo scanner"
TOOL_VERSION = "1.0.0"

DEFAULT_EXCLUDE_PARTS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    "output", "output-vaults", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".playwright-mcp", ".claude", "coverage", "htmlcov",
}
DEFAULT_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx"}
MAX_FILE_BYTES = 1_048_576          # 1 MiB — larger files are skipped, not scanned
SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
SARIF_LEVEL = {"CRITICAL": "error", "HIGH": "error", "MEDIUM": "warning", "LOW": "note"}


# ────────────────────────────── rule identity ───────────────────────────────

def rule_ids() -> dict[tuple[str, str], str]:
    """Stable rule ids (RA-CWE-89-001…), numbered per-CWE in _RULES order."""
    ids: dict[tuple[str, str], str] = {}
    count: dict[str, int] = {}
    for _rx, cwe, title, *_rest in scanner_mod._RULES:
        count[cwe] = count.get(cwe, 0) + 1
        ids[(cwe, title)] = f"RA-{cwe}-{count[cwe]:03d}"
    return ids


def rule_severities() -> dict[str, str]:
    return {rule_ids()[(cwe, title)]: sev for _rx, cwe, title, sev, *_ in scanner_mod._RULES}


def fingerprint(rel_path: str, rule_id: str, line_text: str) -> str:
    """Stable across runs: content-based, not line-number-based."""
    h = hashlib.sha256(f"{rel_path}\x00{rule_id}\x00{line_text.strip()}".encode("utf-8"))
    return h.hexdigest()[:32]


# ────────────────────────────── file walking ────────────────────────────────

def iter_files(roots: list[Path], exts: set[str], exclude_parts: set[str],
               max_bytes: int) -> tuple[list[Path], dict[str, int]]:
    """Walk roots without following symlinks; skip excluded/binary/oversize files."""
    files: list[Path] = []
    skipped = {"excluded": 0, "binary": 0, "oversize": 0}
    seen: set[Path] = set()

    def take(p: Path) -> None:
        if p in seen:
            return
        seen.add(p)
        if p.suffix.lower() not in exts:
            return
        if any(part in exclude_parts for part in p.parts):
            skipped["excluded"] += 1
            return
        try:
            if p.stat().st_size > max_bytes:
                skipped["oversize"] += 1
                return
            with open(p, "rb") as fh:
                if b"\0" in fh.read(8192):        # binary sniff — deterministic
                    skipped["binary"] += 1
                    return
            files.append(p)
        except OSError:
            skipped["excluded"] += 1

    for root in roots:
        if root.is_file():
            take(root)
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in exclude_parts]
            for name in sorted(filenames):
                take(Path(dirpath) / name)
    return sorted(files), skipped


# ─────────────────────────────── scanning ───────────────────────────────────

def scan_file(path: Path, ids: dict[tuple[str, str], str], use_model: bool,
              model_url: str | None) -> tuple[list[dict], str | None]:
    """One file → rule findings (+ model findings when opted in).

    Returns (findings, model_status) where model_status is None when the model
    was not requested, "ok" / "model_error" / "model_not_configured" otherwise.
    """
    code = path.read_text(encoding="utf-8", errors="replace")
    rel = os.path.relpath(path).replace(os.sep, "/")

    findings: list[dict] = []
    for f in scanner_mod.scan_rules(code):
        rid = ids.get((f["cwe"], f["title"]), f"RA-{f['cwe']}-000")
        findings.append({
            "file": rel, "line": f["line"], "column": f.get("column"),
            "cwe": f["cwe"], "severity": f["severity"], "title": f["title"],
            "snippet": f["snippet"], "reason": f["reason"],
            "remediation": f["remediation"], "engine": "rules", "rule_id": rid,
            "fingerprint": fingerprint(rel, rid, f["snippet"]),
        })

    model_status: str | None = None
    if use_model:
        if model_url:
            scanner_mod.RAKSHAK_AI_URL = model_url
        if not scanner_mod.RAKSHAK_AI_URL:
            model_status = "model_not_configured"
        else:
            model_status = "ok"
            model = scanner_mod.scan_with_model(code)
            if model is None:                     # timeout / unreachable / bad payload
                model_status = "model_error"
            else:
                for f in model:
                    findings.append({
                        "file": rel, "line": f["line"], "column": None,
                        "cwe": f["cwe"], "severity": f["severity"],
                        "title": f["title"], "snippet": f["snippet"],
                        "reason": f["reason"], "remediation": f["remediation"],
                        "engine": "rakshakai-14b",
                        "rule_id": f"RA-{f['cwe']}-model",
                        "fingerprint": fingerprint(rel, f"model:{f['cwe']}", f["snippet"]),
                    })
    findings.sort(key=lambda f: (f["file"], f["line"], f["rule_id"]))
    return findings, model_status


def endpoint_mode(use_model: bool, model_url: str | None) -> str:
    if not use_model:
        return "local-only"                       # no network, ever
    url = model_url or scanner_mod.RAKSHAK_AI_URL
    if not url:
        return "local-only"
    try:
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        return "local" if host in ("localhost", "127.0.0.1", "::1") else "remote"
    except ValueError:
        return "remote"


# ─────────────────────────────── outputs ────────────────────────────────────

def to_sarif(findings: list[dict], files_scanned: int) -> dict:
    rules = []
    for rid, sev in sorted(rule_severities().items()):
        rules.append({
            "id": rid,
            "shortDescription": {"text": f"{rid} ({sev})"},
            "properties": {"severity": sev},
        })
    results = []
    for f in findings:
        region: dict = {"startLine": f["line"]}
        if f.get("column"):
            region["startColumn"] = f["column"]
        results.append({
            "ruleId": f["rule_id"],
            "level": SARIF_LEVEL.get(f["severity"], "note"),
            "message": {"text": f"{f['title']} — {f['reason']} Fix: {f['remediation']}"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f["file"]},
                    "region": region,
                },
            }],
            "fingerprints": {"rakshak/v1": f["fingerprint"]},
            "properties": {
                "engine": f["engine"], "cwe": f["cwe"], "severity": f["severity"],
                "remediation": f["remediation"],
            },
        })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": TOOL_NAME, "version": TOOL_VERSION,
                    "informationUri": "https://huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final",
                    "rules": rules,
                },
            },
            "properties": {"filesScanned": files_scanned},
            "results": results,
        }],
    }


def load_baseline(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["fingerprint"] for row in data.get("findings", [])}


def write_baseline(path: Path, findings: list[dict]) -> None:
    rules_only = [f for f in findings if f["engine"] == "rules"]
    path.write_text(json.dumps({
        "version": 1,
        "generated": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "note": "known findings accepted by the team — the CI gate fails only on NEW findings",
        "findings": [{k: f[k] for k in
                      ("fingerprint", "file", "line", "cwe", "severity", "title", "rule_id")}
                     for f in rules_only],
    }, indent=2) + "\n", encoding="utf-8")


# ──────────────────────────────── runner ────────────────────────────────────

def _run_gate(args: argparse.Namespace, files: list[Path],
              banners: bool = True,
              skipped: dict[str, int] | None = None) -> int:
    """Scan ``files``, gate against the baseline, print the summary.

    Shared by the one-shot CLI and ``--watch`` mode so the live monitor reports
    exactly the same gate the CI job would evaluate. Returns the exit code.
    """
    ids = rule_ids()
    use_model = bool(args.model or args.model_url)
    findings: list[dict] = []
    model_failures = 0
    for path in files:
        try:
            file_findings, mstatus = scan_file(path, ids, use_model, args.model_url)
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            return 2
        findings.extend(file_findings)
        if mstatus == "model_error":
            model_failures += 1

    model_status: str | None = None
    if use_model:
        if not (args.model_url or scanner_mod.RAKSHAK_AI_URL):
            model_status = "model_not_configured"
        else:
            model_status = "model_error" if model_failures else "ok"

    rule_findings = [f for f in findings if f["engine"] == "rules"]
    by_sev = {s: 0 for s in SEVERITY_RANK}
    for f in rule_findings:
        by_sev[f["severity"]] += 1

    baseline_known = 0
    new_findings: list[dict] = list(rule_findings)
    if args.baseline and not args.write_baseline:
        if not args.baseline.exists():
            print(f"error: baseline not found: {args.baseline}", file=sys.stderr)
            return 2
        known = load_baseline(args.baseline)
        new_findings = [f for f in rule_findings if f["fingerprint"] not in known]
        baseline_known = len(rule_findings) - len(new_findings)

    if args.write_baseline:
        write_baseline(args.write_baseline, findings)
        print(f"baseline written: {args.write_baseline} "
              f"({len([f for f in findings if f['engine'] == 'rules'])} rule findings)")
        return 0

    threshold = SEVERITY_RANK[args.fail_on]
    gate_hits = [f for f in new_findings if SEVERITY_RANK[f["severity"]] >= threshold]
    exit_code = 1 if gate_hits else 0

    report = {
        "tool": TOOL_NAME, "version": TOOL_VERSION,
        "mode": {
            "rules": True, "model": use_model,
            "endpoint_mode": endpoint_mode(use_model, args.model_url),
            "model_status": model_status,
        },
        "files_scanned": len(files), "files_skipped": skipped or {},
        "summary": {**by_sev, "total": len(rule_findings)},
        "baseline": ({"path": str(args.baseline), "known": baseline_known,
                      "new": len(new_findings)} if args.baseline else None),
        "fail_on": args.fail_on, "gate": "fail" if gate_hits else "pass",
        "findings": findings,
        "disclosure": "static analysis of source code — detects selected CWE patterns "
                      "before deployment; findings require human review. Not a runtime "
                      "defense; not complete vulnerability coverage.",
    }
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.sarif:
        args.sarif.write_text(json.dumps(to_sarif(findings, len(files)), indent=2) + "\n",
                              encoding="utf-8")

    if banners:
        print(f"{TOOL_NAME} v{TOOL_VERSION}")
        print("engine: rules (deterministic, primary)"
              + (f" + rakshakai-14b (status: {model_status}, "
                 f"endpoint: {endpoint_mode(use_model, args.model_url)})"
                 if use_model else " · local-only, nothing leaves this machine"))
        print(f"scanned {len(files)} file(s) · skipped "
              f"{sum((skipped or {}).values())} (excluded {(skipped or {}).get('excluded', 0)}, "
              f"binary {(skipped or {}).get('binary', 0)}, oversize {(skipped or {}).get('oversize', 0)})")
    print(f"rule findings: {by_sev['CRITICAL']} CRITICAL · {by_sev['HIGH']} HIGH · "
          f"{by_sev['MEDIUM']} MEDIUM · {by_sev['LOW']} LOW")
    if banners:
        for f in sorted(gate_hits, key=lambda x: -SEVERITY_RANK[x["severity"]])[:20]:
            print(f"  NEW {f['severity']:<8} {f['file']}:{f['line']}  {f['rule_id']}  {f['title']}")
    else:
        for f in sorted(gate_hits, key=lambda x: -SEVERITY_RANK[x["severity"]])[:6]:
            print(f"  NEW {f['severity']:<8} {f['file']}:{f['line']}  {f['rule_id']}  {f['title']}")
    if args.baseline:
        print(f"baseline: {baseline_known} known · {len(new_findings)} new")
    print(f"gate: {'FAIL' if gate_hits else 'PASS'} "
          f"(fail-on {args.fail_on}, {len(gate_hits)} new finding(s) at/above threshold)")
    if model_status == "model_error":
        print("note: model endpoint failed on some files — reported as model_error, "
              "NOT a clean scan (rules results stand; model is non-blocking)")
    return exit_code


def run_watch(args: argparse.Namespace, roots: list[Path],
              exts: set[str], exclude_parts: set[str]) -> int:
    """Live watchdog — re-run the gate whenever any in-scope file changes.

    Stdlib-only mtime polling (0.8s): every event re-runs the exact gate the CI
    job uses, so a developer sees, live in their terminal, whether what they just
    saved would pass the pipeline. Ctrl-C stops the watcher; gate failures keep
    the watcher alive so the fix can be proven next.
    """
    last: dict[str, tuple[int, int]] = {}
    print(f"{TOOL_NAME} v{TOOL_VERSION} — watching "
          f"{', '.join(str(r) for r in roots)} (Ctrl-C to stop)")
    try:
        while True:
            files, skipped = iter_files(roots, exts, exclude_parts, MAX_FILE_BYTES)
            snap: dict[str, tuple[int, int]] = {}
            for p in files:
                st = p.stat()
                snap[os.path.relpath(p)] = (st.st_mtime_ns, st.st_size)

            if not last:
                # first pass = initial snapshot: run the gate quietly, no "event"
                last = snap
                if files:
                    _run_gate(args, files, banners=False)
                time.sleep(0.8)
                continue

            changed = sorted(k for k in snap if snap[k] != last.get(k))
            removed = sorted(k for k in last if k not in snap)
            if changed or removed:
                last = snap
                if files:
                    labels = changed + [f"removed: {k}" for k in removed]
                    print(f"\n[{_dt.datetime.now().strftime('%H:%M:%S')}] event: "
                          f"{', '.join(labels[:3])}" + (" …" if len(labels) > 3 else ""))
                    _run_gate(args, files, banners=False)
            time.sleep(0.8)
    except KeyboardInterrupt:
        print("\nwatch stopped — gate ran with the same rules + baseline as the CI job")
        return 0


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="scan_repo", description=TOOL_NAME)
    ap.add_argument("targets", nargs="+", help="files or directories to scan")
    ap.add_argument("--ext", nargs="*", default=sorted(DEFAULT_EXTS),
                    help="file extensions to scan (default: %(default)s)")
    ap.add_argument("--exclude", nargs="*", default=[],
                    help="extra path parts to exclude (on top of the defaults)")
    ap.add_argument("--fail-on", choices=list(SEVERITY_RANK), default="CRITICAL",
                    help="fail (exit 1) on NEW rule findings at/above this severity "
                         "(default: %(default)s)")
    ap.add_argument("--baseline", type=Path, help="baseline JSON — gate fails only on NEW findings")
    ap.add_argument("--write-baseline", type=Path, metavar="PATH",
                    help="write the current rule findings as a baseline and exit 0")
    ap.add_argument("--json", type=Path, metavar="PATH", help="write a full JSON report")
    ap.add_argument("--sarif", type=Path, metavar="PATH", help="write a SARIF 2.1.0 report")
    ap.add_argument("--watch", action="store_true",
                    help="live watch mode: full gate re-run whenever any in-scope file "
                         "changes (Ctrl-C to stop)")
    ap.add_argument("--model", action="store_true",
                    help="ALSO classify with the 14B model (non-blocking; uses $RAKSHAK_AI_URL)")
    ap.add_argument("--model-url", metavar="URL",
                    help="explicit 14B endpoint (overrides $RAKSHAK_AI_URL; enables --model)")
    args = ap.parse_args(argv)

    roots = [Path(t) for t in args.targets]
    missing = [str(r) for r in roots if not r.exists()]
    if missing:
        print(f"error: target does not exist: {missing[0]}", file=sys.stderr)
        return 2

    exts = {e if e.startswith(".") else f".{e}" for e in args.ext}
    exclude_parts = DEFAULT_EXCLUDE_PARTS | set(args.exclude)
    try:
        files, skipped = iter_files(roots, exts, exclude_parts, MAX_FILE_BYTES)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.watch:
        return run_watch(args, roots, exts, exclude_parts)

    return _run_gate(args, files, skipped=skipped)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))