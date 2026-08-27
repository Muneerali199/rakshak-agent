"""RakshakAI code scanner — the platform's self-security layer (paper §18).

MVP engine: deterministic, line-based rules for the CWE classes that dominate
government-web compromises (SQLi, command injection, XSS, hardcoded secrets,
weak hashing, path traversal). Honest labeling: results carry
``engine: "rule-based-fallback"`` until the fine-tuned 14B model
(``RAKSHAK_AI_URL`` → vLLM OpenAI-compatible endpoint) is configured, in which
case the model's classification is used with rule-based results as the
verified fallback. Pure standard library.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

RAKSHAK_AI_URL = os.getenv("RAKSHAK_AI_URL", "").strip()
MODEL_TIMEOUT_S = 10


class Finding(dict):
    pass


def _finding(cwe: str, title: str, severity: str, line_no: int, line: str,
             why: str, fix: str) -> Finding:
    return Finding(
        cwe=cwe, title=title, severity=severity, line=line_no,
        snippet=line.strip()[:160], reason=why, remediation=fix,
    )


# (compiled regex, cwe, title, severity, why, fix)
_RULES = [
    (
        re.compile(r"f[\"'][^\"']*\b(select|insert|update|delete|drop)\b", re.I),
        "CWE-89", "SQL Injection via f-string", "CRITICAL",
        "f-string interpolates untrusted input directly into a SQL statement.",
        'Use parameterized queries: cursor.execute("… WHERE id=%s", (id,))',
    ),
    (
        re.compile(r"[\"'][^\"']*\b(select|insert|update|delete)\b[^\"']*[\"']\s*\+", re.I),
        "CWE-89", "SQL Injection via string concatenation", "CRITICAL",
        "SQL built by concatenation accepts injected fragments as syntax.",
        "Use parameterized queries instead of concatenating user input.",
    ),
    (
        re.compile(r"execute\s*\(\s*([\"']).*?\1\s*\+", re.I),
        "CWE-89", "SQL Injection via string concatenation", "CRITICAL",
        "execute() receives a concatenated string; user input becomes SQL syntax.",
        "Use parameterized queries: cursor.execute(sql, (value,))",
    ),
    (
        re.compile(r"execute\s*\(\s*[^,)]*\.format\s*\(", re.I),
        "CWE-89", "SQL Injection via .format()", "CRITICAL",
        ".format() substitutes user input into the SQL text before execution.",
        "Use parameterized queries: cursor.execute(sql, (value,))",
    ),
    (
        re.compile(r"\bos\.(system|popen)\s*\("),
        "CWE-78", "OS command injection", "CRITICAL",
        "os.system/popen runs a shell command; any interpolated input is executable.",
        "Use subprocess.run([...], shell=False) with an argument list.",
    ),
    (
        re.compile(r"shell\s*=\s*True"),
        "CWE-78", "Shell invocation enabled", "CRITICAL",
        "shell=True passes the command through the shell; metacharacters become commands.",
        "Pass an argument list and use shell=False.",
    ),
    (
        re.compile(r"render_template_string\s*\("),
        "CWE-79", "XSS via template string", "HIGH",
        "Rendering a runtime-built template string executes injected markup.",
        "Render static templates and pass user data as context variables.",
    ),
    (
        re.compile(r"\.innerHTML\s*=", re.I),
        "CWE-79", "XSS via innerHTML", "HIGH",
        "Assigning unsanitized content to innerHTML executes embedded scripts.",
        "Use textContent or sanitize with DOMPurify before injecting markup.",
    ),
    (
        re.compile(r"\b(password|passwd|secret|api_key|apikey|token|access_key)\s*=\s*[\"'][^\"']{4,}[\"']", re.I),
        "CWE-798", "Hardcoded credential", "HIGH",
        "A credential literal is embedded in source; it leaks via VCS and builds.",
        "Load secrets from environment variables or a secrets manager.",
    ),
    (
        re.compile(r"hashlib\.(md5|sha1)\s*\("),
        "CWE-327", "Weak hash algorithm", "MEDIUM",
        "MD5/SHA-1 are collision-broken and unfit for passwords or signatures.",
        "Use hashlib.sha256+salt for integrity; bcrypt/argon2 for passwords.",
    ),
    (
        re.compile(r"open\s*\(\s*f[\"']"),
        "CWE-22", "Path traversal via f-string", "HIGH",
        "An interpolated filename can escape the intended directory with ../.",
        "Validate against an allowlist and resolve with os.path.realpath.",
    ),
]

_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def scan_rules(code: str) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple] = set()
    for line_no, line in enumerate(code.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):                    # comments are not execution paths
            continue
        for rx, cwe, title, sev, why, fix in _RULES:
            if rx.search(line) and (cwe, title, line_no) not in seen:
                seen.add((cwe, title, line_no))
                findings.append(_finding(cwe, title, sev, line_no, line, why, fix))
    findings.sort(key=lambda f: (f["line"], _SEVERITY_ORDER[f["severity"]]))
    return findings


def scan_with_model(code: str) -> list[Finding] | None:
    """Ask the fine-tuned 14B model (vLLM, OpenAI-compatible) to classify the code.

    Returns None when the hook is not configured or unreachable — the caller then
    falls back to the deterministic rule engine and discloses it.
    """
    if not RAKSHAK_AI_URL:
        return None
    payload = json.dumps({
        "messages": [
            {"role": "system", "content":
                "You are RakshakAI, a CWE vulnerability classifier. Respond with ONLY a JSON "
                "array: [{\"cwe\":\"CWE-89\",\"title\":str,\"severity\":\"CRITICAL|HIGH|MEDIUM|LOW\","
                "\"line\":int,\"reason\":str,\"remediation\":str}]"},
            {"role": "user", "content": code[:6000]},
        ],
        "temperature": 0,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            RAKSHAK_AI_URL.rstrip("/") + "/v1/chat/completions",
            data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=MODEL_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        arr = json.loads(content[content.index("["):content.rindex("]") + 1])
        out = []
        for f in arr:
            line_no = int(f.get("line", 0)) or 1
            lines = code.splitlines()
            out.append(Finding(
                cwe=f.get("cwe", "CWE-?"), title=f.get("title", "vulnerability"),
                severity=f.get("severity", "MEDIUM").upper(),
                line=line_no, snippet=lines[line_no - 1].strip()[:160] if line_no <= len(lines) else "",
                reason=f.get("reason", ""), remediation=f.get("remediation", ""),
            ))
        return out
    except Exception:
        return None                                      # offline → deterministic fallback


def summarize(findings: list[Finding]) -> dict:
    by_sev: dict[str, int] = {}
    by_cwe: dict[str, int] = {}
    for f in findings:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
        by_cwe[f["cwe"]] = by_cwe.get(f["cwe"], 0) + 1
    return {"total": len(findings), "by_severity": by_sev, "by_cwe": by_cwe}


def scan(code: str) -> dict:
    """Model first (when configured), rule engine as verified fallback — always disclosed."""
    model = scan_with_model(code)
    if model is not None:
        engine, findings, note = "rakshakai-14b", model, "classified by the fine-tuned 14B model"
    else:
        engine, findings, note = "rule-based-fallback", scan_rules(code), \
            "deterministic rule engine (set RAKSHAK_AI_URL to serve the fine-tuned 14B model)"
    return {
        "engine": engine,
        "engine_note": note,
        "findings": findings,
        "summary": summarize(findings),
        "scanned_lines": len(code.splitlines()),
        "disclosure": "static analysis on pasted code — findings require human review "
                      "before any action (same HITL policy as the intelligence graph)",
    }
