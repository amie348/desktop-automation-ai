"""Utility to run shell commands asynchronously with a timeout."""

import asyncio

TRUNCATED_MESSAGE: str = "<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>"
MAX_RESPONSE_LEN: int = 16000


def maybe_truncate(content: str, truncate_after: int | None = MAX_RESPONSE_LEN):
    """Truncate content and append a notice if content exceeds the specified length."""
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


async def run(
    cmd: str,
    timeout: float | None = 120.0,  # seconds
    truncate_after: int | None = MAX_RESPONSE_LEN,
):
    """Run a shell command asynchronously with a timeout."""
    import sys
    
    # Windows-specific subprocess creation to avoid NotImplementedError
    if sys.platform == "win32":
        import subprocess
        # Use synchronous subprocess for Windows to avoid asyncio issues
        try:
            process_result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                timeout=timeout,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return (
                process_result.returncode or 0,
                maybe_truncate(process_result.stdout or "", truncate_after=truncate_after),
                maybe_truncate(process_result.stderr or "", truncate_after=truncate_after),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"Command '{cmd}' timed out after {timeout} seconds"
            ) from exc
    else:
        # Unix/Linux - use async subprocess
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return (
                process.returncode or 0,
                maybe_truncate(stdout.decode(), truncate_after=truncate_after),
                maybe_truncate(stderr.decode(), truncate_after=truncate_after),
            )
        except asyncio.TimeoutError as exc:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            raise TimeoutError(
                f"Command '{cmd}' timed out after {timeout} seconds"
            ) from exc
