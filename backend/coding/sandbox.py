"""
Local code execution sandbox for the coding room.

This is a *development* sandbox using subprocess + timeout. For production,
swap this out for Judge0 or a container-based runner. We intentionally keep
the surface (run_code) identical so the backend route doesn't change.

Supported languages: python, javascript (node), c, cpp, java
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecResult:
    status: str           # "Accepted", "Wrong Answer", "Runtime Error",
                          # "Time Limit Exceeded", "Compile Error", "Unsupported Language"
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    time_ms: int = 0
    memory_kb: Optional[int] = None


_DEF_TIME = 5.0  # seconds


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(args, stdin: str, time_limit: float, cwd: Optional[str] = None) -> ExecResult:
    """Run a single subprocess with stdin, capturing output."""
    start = time.time()
    try:
        proc = subprocess.run(
            args,
            input=stdin or "",
            capture_output=True,
            text=True,
            timeout=time_limit,
            cwd=cwd,
        )
        elapsed = int((time.time() - start) * 1000)

        if proc.returncode != 0:
            return ExecResult(
                status="Runtime Error",
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                time_ms=elapsed,
            )

        return ExecResult(
            status="Accepted",
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            time_ms=elapsed,
        )
    except subprocess.TimeoutExpired:
        return ExecResult(
            status="Time Limit Exceeded",
            stderr=f"Execution exceeded {time_limit}s",
            time_ms=int(time_limit * 1000),
        )
    except FileNotFoundError as e:
        return ExecResult(
            status="Unsupported Language",
            stderr=f"Toolchain not installed: {e}",
        )
    except Exception as e:  # noqa: BLE001
        return ExecResult(status="Runtime Error", stderr=str(e))


def _compare(actual: str, expected: str) -> bool:
    """Lenient comparison: trim trailing whitespace per line."""
    a = "\n".join(line.rstrip() for line in (actual or "").rstrip().splitlines())
    e = "\n".join(line.rstrip() for line in (expected or "").rstrip().splitlines())
    return a == e


def run_code(
    source_code: str,
    language: str,
    stdin: str = "",
    expected_output: str = "",
    time_limit: float = _DEF_TIME,
) -> ExecResult:
    """Compile (if needed) and run code, returning structured result."""
    lang = (language or "").lower().strip()
    workdir = tempfile.mkdtemp(prefix=f"proctoai_code_{uuid.uuid4().hex[:8]}_")

    try:
        if lang in ("python", "python3"):
            src = os.path.join(workdir, "main.py")
            with open(src, "w", encoding="utf-8") as f:
                f.write(source_code)
            py = "python" if _have("python") else "python3"
            result = _run([py, "-I", "-B", src], stdin, time_limit, cwd=workdir)

        elif lang in ("javascript", "node", "js"):
            src = os.path.join(workdir, "main.js")
            with open(src, "w", encoding="utf-8") as f:
                f.write(source_code)
            if not _have("node"):
                return ExecResult(status="Unsupported Language", stderr="Node.js not installed")
            result = _run(["node", src], stdin, time_limit, cwd=workdir)

        elif lang in ("c",):
            src = os.path.join(workdir, "main.c")
            exe = os.path.join(workdir, "main.exe" if os.name == "nt" else "main.out")
            with open(src, "w", encoding="utf-8") as f:
                f.write(source_code)
            if not _have("gcc"):
                return ExecResult(status="Unsupported Language", stderr="gcc not installed")
            cc = subprocess.run(
                ["gcc", src, "-O2", "-o", exe],
                capture_output=True, text=True, timeout=15,
            )
            if cc.returncode != 0:
                return ExecResult(status="Compile Error", compile_output=cc.stderr)
            result = _run([exe], stdin, time_limit, cwd=workdir)

        elif lang in ("cpp", "c++"):
            src = os.path.join(workdir, "main.cpp")
            exe = os.path.join(workdir, "main.exe" if os.name == "nt" else "main.out")
            with open(src, "w", encoding="utf-8") as f:
                f.write(source_code)
            if not _have("g++"):
                return ExecResult(status="Unsupported Language", stderr="g++ not installed")
            cc = subprocess.run(
                ["g++", src, "-O2", "-std=c++17", "-o", exe],
                capture_output=True, text=True, timeout=15,
            )
            if cc.returncode != 0:
                return ExecResult(status="Compile Error", compile_output=cc.stderr)
            result = _run([exe], stdin, time_limit, cwd=workdir)

        elif lang == "java":
            src = os.path.join(workdir, "Main.java")
            with open(src, "w", encoding="utf-8") as f:
                f.write(source_code)
            if not _have("javac") or not _have("java"):
                return ExecResult(status="Unsupported Language", stderr="JDK not installed")
            cc = subprocess.run(
                ["javac", src],
                capture_output=True, text=True, timeout=20, cwd=workdir,
            )
            if cc.returncode != 0:
                return ExecResult(status="Compile Error", compile_output=cc.stderr)
            result = _run(["java", "-cp", workdir, "Main"], stdin, time_limit, cwd=workdir)

        else:
            return ExecResult(status="Unsupported Language", stderr=f"'{language}' is not supported in dev sandbox")

        # If we got "Accepted" runtime, verify against expected
        if expected_output and result.status == "Accepted":
            if not _compare(result.stdout, expected_output):
                result.status = "Wrong Answer"
        return result

    finally:
        try:
            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            pass
