import os
import typing as tp
from asyncio.subprocess import PIPE, create_subprocess_exec
from pathlib import Path
from subprocess import CalledProcessError


async def _execute_command(cmd: tp.List[str], cwd: Path) -> tp.Tuple[int, str, str]:
    """Execute the command in the provided directory

    Args:
        cmd: Command line to execute
        cwd: Current working directory for the command

    Returns:
        Process return code, stdout, stderr

    Raises:
        CalledProcessError if the return code is non-zero
    """
    process = await create_subprocess_exec(
        *cmd, cwd=cwd, stdout=PIPE, stderr=PIPE, env=os.environ
    )
    output, error = await process.communicate()

    if process.returncode != 0:
        raise CalledProcessError(
            process.returncode,
            " ".join(cmd),
            output.decode("utf-8"),
            error.decode("utf-8"),
        )

    return process.returncode, output.decode("utf-8"), error.decode("utf-8")


async def update_git_repository(
    template_root_dir: str, template_dir: str = ".", git_url: tp.Optional[str] = None
) -> tp.NoReturn:
    """Create and update the git repository.

    Args:
        template_root_dir: Templates project folder
        template_dir: Templates folder relative to its root (default: ".")
        git_url: Git repository URL (default: None)
    """
    template_root_dir = Path(template_root_dir)

    if not template_root_dir.exists():
        template_root_dir.parent.mkdir(parents=True, exist_ok=True)

        if git_url is not None:
            await _execute_command(
                ("git", "clone", git_url, str(template_root_dir)),
                cwd=str(template_root_dir.parent),
            )
        else:
            (template_root_dir / template_dir).resolve().mkdir(
                parents=True, exist_ok=True
            )

    if git_url is not None:  # Update reports repository
        await _execute_command(
            ("git", "checkout", "--", "*"), cwd=str(template_root_dir)
        )
        await _execute_command(("git", "clean", "-fdq"), cwd=str(template_root_dir))
        await _execute_command(
            ("git", "checkout", "master"), cwd=str(template_root_dir)
        )
        await _execute_command(
            ("git", "pull", git_url, "master"), cwd=str(template_root_dir)
        )
