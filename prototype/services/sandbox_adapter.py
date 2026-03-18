from __future__ import annotations

from typing import Any


def run(code_text: str) -> dict[str, Any]:
    """
    Thin sandbox adapter.

    Replace this with your real sandbox execution service.
    Requirements for real implementation:
    - single-run model
    - stdin blocked/null
    - capture stdout + stderr + return code
    """
    lowered = code_text.lower()
    if "syntax_error" in lowered:
        stdout = ""
        stderr = "Compilation failed: simulated syntax error."
        return_code = 1
    elif "1/0" in code_text or "division by zero" in lowered:
        stdout = ""
        stderr = "Runtime error: division by zero."
        return_code = 1
    elif "demo-level: mid" in lowered:
        stdout = "MID\n"
        stderr = ""
        return_code = 0
    elif "demo-level: high" in lowered:
        stdout = "HIGH\n"
        stderr = ""
        return_code = 0
    else:
        stdout = "Program executed in placeholder sandbox.\n"
        stderr = ""
        return_code = 0

    logs = (
        "Sandbox execution (single-run, stdin disabled)\n"
        f"return_code: {return_code}\n"
        f"stdout:\n{stdout}\n"
        f"stderr:\n{stderr}\n"
    )
    return {
        "stdout": stdout,
        "stderr": stderr,
        "return_code": return_code,
        "logs": logs,
    }
