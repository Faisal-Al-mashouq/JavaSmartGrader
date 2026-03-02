import asyncio
import logging
import re
import shutil
import uuid
from pathlib import Path

SANDBOX_DIR = Path(__file__).parent
SANDBOX_TMP_DIR = Path(__file__).parent / "tmp"

logger = logging.getLogger(__name__)


async def _docker_build_image(tag: str, dockerfile_path: Path) -> None:
    logger.info("Building Docker image '%s' from %s", tag, dockerfile_path.name)
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
        logger.error("Failed to build Docker image '%s': %s", tag, stderr.decode())
        raise RuntimeError(f"Failed to build {tag}: {stderr.decode()}")
    logger.info("Docker image '%s' built successfully", tag)


async def docker_build_images():
    logger.info("Building sandbox Docker images...")
    await asyncio.gather(
        _docker_build_image("compiler-image", SANDBOX_DIR / "Dockerfile.compiler"),
        _docker_build_image("executer-image", SANDBOX_DIR / "Dockerfile.executer"),
    )
    logger.info("All sandbox Docker images built successfully")


def _extract_class_name(java_code: str) -> str:
    match = re.search(r"public\s+class\s+(\w+)", java_code)
    if not match:
        logger.error("Could not find public class name in Java code")
        raise ValueError("Could not find public class name in Java code")
    class_name = match.group(1)
    logger.debug("Extracted class name: %s", class_name)
    return class_name


def _create_workspace(job_id: uuid.UUID) -> Path:
    workspace = SANDBOX_TMP_DIR / str(job_id)
    logger.info("Creating workspace for job %s at %s", job_id, workspace)
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "compiled").mkdir(exist_ok=True)
    (workspace / "input").mkdir(exist_ok=True)
    (workspace / "out").mkdir(exist_ok=True)
    logger.debug("Workspace directories created for job %s", job_id)
    return workspace


def _cleanup_workspace(job_id: uuid.UUID):
    workspace = SANDBOX_TMP_DIR / str(job_id)
    if workspace.exists():
        shutil.rmtree(workspace)
        logger.info("Workspace cleaned up for job %s", job_id)
    else:
        logger.debug("No workspace to clean up for job %s", job_id)


async def run_container(cmd: list[str]) -> tuple[int, str, str]:
    logger.debug("Running container: %s", " ".join(cmd[:6]))
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    logger.debug("Container exited with code %d", proc.returncode)
    return proc.returncode, stdout.decode(), stderr.decode()


async def _run_execution_container(
    workspace: Path, class_name: str
) -> tuple[int, str, str]:
    logger.debug("Running execution container for class '%s'", class_name)
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
