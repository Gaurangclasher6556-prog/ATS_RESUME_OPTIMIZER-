"""
code_executor.py — Real code execution via the public Piston API.

The mock-interview coding round previously *simulated* execution by asking the
LLM to pretend to be a judge — which means it could hallucinate that buggy code
passed. This module runs the user's code for real against the public Piston
sandbox (https://github.com/engineer-man/piston), returning genuine stdout /
stderr / compile output. If the network call fails, the caller can fall back to
the LLM simulation so the feature degrades gracefully.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error

PISTON_URL = "https://emkc.org/api/v2/piston/execute"

# Map the app's UI language labels to Piston language identifiers + versions.
# Versions are the ones Piston exposes on its public instance.
LANG_MAP = {
    "python":     ("python", "3.10.0",  "main.py"),
    "javascript": ("javascript", "18.15.0", "main.js"),
    "typescript": ("typescript", "5.0.3", "main.ts"),
    "java":       ("java", "15.0.2", "Main.java"),
    "c++":        ("c++", "10.2.0", "main.cpp"),
    "c#":         ("csharp", "6.12.0", "main.cs"),
    "go":         ("go", "1.16.2", "main.go"),
    "rust":       ("rust", "1.68.2", "main.rs"),
    "ruby":       ("ruby", "3.0.1", "main.rb"),
    "swift":      ("swift", "5.3.3", "main.swift"),
    "kotlin":     ("kotlin", "1.8.20", "main.kt"),
    "php":        ("php", "8.2.3", "main.php"),
}


class CodeExecutionError(Exception):
    """Raised when the remote execution service cannot be reached."""


def is_supported(language: str) -> bool:
    return language.lower() in LANG_MAP


def run_code(code: str, language: str = "Python", stdin: str = "",
             timeout: int = 20) -> dict:
    """
    Execute code on the Piston sandbox.

    Returns a dict:
      {
        "ok": bool,                 # True if the run completed (compiled & ran)
        "stdout": str,
        "stderr": str,
        "compile_output": str,
        "exit_code": int | None,
        "language": str,
        "version": str,
      }

    Raises CodeExecutionError if the service is unreachable (caller may then
    fall back to the LLM-simulated judge).
    """
    key = language.lower()
    if key not in LANG_MAP:
        raise CodeExecutionError(f"Language '{language}' not supported by sandbox.")

    lang_id, version, filename = LANG_MAP[key]
    payload = {
        "language": lang_id,
        "version": version,
        "files": [{"name": filename, "content": code or ""}],
        "stdin": stdin or "",
        "run_timeout": timeout * 1000,
        "compile_timeout": timeout * 1000,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        PISTON_URL, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        raise CodeExecutionError(f"Could not reach execution sandbox: {e}")

    run = result.get("run", {}) or {}
    compile_stage = result.get("compile", {}) or {}
    return {
        "ok": run.get("code", 1) == 0 and not compile_stage.get("stderr"),
        "stdout": run.get("stdout", "") or "",
        "stderr": run.get("stderr", "") or "",
        "compile_output": compile_stage.get("stderr", "") or "",
        "exit_code": run.get("code"),
        "language": result.get("language", lang_id),
        "version": result.get("version", version),
    }


def format_terminal(result: dict) -> str:
    """Render an execution result as a readable terminal log."""
    lines = [f"$ run ({result['language']} {result['version']})"]
    if result.get("compile_output"):
        lines.append("── compile ──")
        lines.append(result["compile_output"].rstrip())
    if result.get("stdout"):
        lines.append("── stdout ──")
        lines.append(result["stdout"].rstrip())
    if result.get("stderr"):
        lines.append("── stderr ──")
        lines.append(result["stderr"].rstrip())
    code = result.get("exit_code")
    lines.append(f"\n[process exited with code {code}]")
    return "\n".join(lines)
