import asyncio
import re
import shutil
import uuid
from pathlib import Path

SANDBOX_DIR = Path(__file__).parent
SANDBOX_TMP_DIR = Path(__file__).parent / "tmp"


async def _docker_build_image(tag: str, dockerfile_path: Path) -> None:
    proc = await asyncio.create_subprocess_exec(
        "docker",
        "build",
        "-t",
        tag,
        "-f",
        str(dockerfile_path),
        str(SANDBOX_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to build {tag}: {stderr.decode()}")


async def docker_build_images():
    await asyncio.gather(
        _docker_build_image("compiler-image", SANDBOX_DIR / "Dockerfile.compiler"),
        _docker_build_image("executer-image", SANDBOX_DIR / "Dockerfile.executer"),
    )


def _extract_class_name(java_code: str) -> str:
    match = re.search(r"public\s+class\s+(\w+)", java_code)
    if not match:
        raise ValueError("Could not find public class name in Java code")
    return match.group(1)


def _create_workspace(job_id: uuid.UUID) -> Path:
    workspace = SANDBOX_TMP_DIR / str(job_id)
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "compiled").mkdir(exist_ok=True)
    (workspace / "input").mkdir(exist_ok=True)
    (workspace / "out").mkdir(exist_ok=True)
    return workspace


def _cleanup_workspace(job_id: uuid.UUID):
    workspace = SANDBOX_TMP_DIR / str(job_id)
    if workspace.exists():
        shutil.rmtree(workspace)


async def run_container(cmd: list[str]) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def _run_execution_container(
    workspace: Path, class_name: str
) -> tuple[int, str, str]:
    return await run_container(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{workspace}:/workspace",
            "--memory=256m",
            "--network=none",
            "--pids-limit=50",
            "--read-only",
            "executer-image",
            "sh",
            "/scripts/execute.sh",
            class_name,
        ]
    )
