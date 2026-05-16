"""
Judge0 client — sends code to the sandbox and polls for results.

Judge0 API docs: https://judge0.com/
We use the self-hosted version via Docker.
"""

import logging
import time
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("coding-svc.judge0")

# Judge0 language IDs (subset — extend as needed)
LANGUAGE_IDS = {
    "python": 71,       # Python 3.8.1
    "python3": 71,
    "javascript": 63,   # Node.js 12.14.0
    "typescript": 74,   # TypeScript 3.7.4
    "java": 62,         # Java 13.0.1
    "c": 50,            # C (GCC 9.2.0)
    "cpp": 54,          # C++ (GCC 9.2.0)
    "c++": 54,
    "go": 60,           # Go 1.13.5
    "rust": 73,         # Rust 1.40.0
    "ruby": 72,         # Ruby 2.7.0
    "csharp": 51,       # C# (Mono 6.6.0)
    "c#": 51,
    "php": 68,          # PHP 7.4.1
    "swift": 83,        # Swift 5.2.3
    "kotlin": 78,       # Kotlin 1.3.70
}


def get_language_id(language: str) -> Optional[int]:
    return LANGUAGE_IDS.get(language.lower().strip())


async def submit_to_judge0(
    source_code: str,
    language: str,
    stdin: str = "",
    expected_output: str = "",
    time_limit: float = 5.0,
    memory_limit: int = 256000,
) -> dict:
    """
    Submit code to Judge0 and wait for result.

    Returns:
        {
            "status": "Accepted" | "Wrong Answer" | "Time Limit Exceeded" | ...,
            "stdout": "...",
            "stderr": "...",
            "compile_output": "...",
            "time": "0.01",
            "memory": 1234,
        }
    """
    settings = get_settings()
    lang_id = get_language_id(language)
    if lang_id is None:
        return {"status": "Unsupported Language", "stderr": f"Language '{language}' not supported"}

    payload = {
        "source_code": source_code,
        "language_id": lang_id,
        "stdin": stdin,
        "expected_output": expected_output if expected_output else None,
        "cpu_time_limit": time_limit,
        "memory_limit": memory_limit,
    }

    headers = {}
    if settings.JUDGE0_API_KEY:
        headers["X-Auth-Token"] = settings.JUDGE0_API_KEY

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create submission
        resp = await client.post(
            f"{settings.JUDGE0_URL}/submissions?base64_encoded=false&wait=false",
            json=payload,
            headers=headers,
        )
        if resp.status_code != 201:
            logger.error(f"Judge0 submit failed: {resp.status_code} {resp.text}")
            return {"status": "Judge Error", "stderr": resp.text}

        token = resp.json().get("token")
        if not token:
            return {"status": "Judge Error", "stderr": "No token returned"}

        # Poll for result (max 30s)
        for _ in range(60):
            time.sleep(0.5)
            result_resp = await client.get(
                f"{settings.JUDGE0_URL}/submissions/{token}?base64_encoded=false",
                headers=headers,
            )
            if result_resp.status_code != 200:
                continue

            data = result_resp.json()
            status_obj = data.get("status", {})
            # Status ID 1=In Queue, 2=Processing
            if status_obj.get("id", 0) <= 2:
                continue

            return {
                "status": status_obj.get("description", "Unknown"),
                "stdout": data.get("stdout") or "",
                "stderr": data.get("stderr") or "",
                "compile_output": data.get("compile_output") or "",
                "time": data.get("time"),
                "memory": data.get("memory"),
            }

        return {"status": "Timeout", "stderr": "Judge0 did not respond in time"}
