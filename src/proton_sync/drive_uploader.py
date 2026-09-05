"""Upload attachments to Proton Drive through rclone's protondrive backend.

Proton has no folder-scoped credentials, so the folder restriction is enforced
here: every destination is built under the configured root and path segments
that could escape it are rejected.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import final

logger = logging.getLogger(__name__)

_FORBIDDEN_SEGMENTS = {"", ".", ".."}


class UploadError(RuntimeError):
    pass


@final
class DriveUploader:
    _remote_name: str
    _root_path: str
    _config_path: str
    _binary: str

    def __init__(
        self,
        remote_name: str,
        root_path: str,
        rclone_config_path: str,
        rclone_binary: str = "rclone",
    ) -> None:
        self._remote_name = remote_name
        self._root_path = root_path.strip("/")
        self._config_path = rclone_config_path
        self._binary = rclone_binary

    def _remote_target(self, folder_segments: list[str], filename: str) -> str:
        for segment in [*folder_segments, filename]:
            if segment.strip() in _FORBIDDEN_SEGMENTS or "/" in segment or "\\" in segment:
                raise UploadError(f"unsafe path segment: {segment!r}")
        path = "/".join([self._root_path, *folder_segments, filename])
        return f"{self._remote_name}:{path}"

    def upload(self, content: bytes, folder_segments: list[str], filename: str) -> None:
        target = self._remote_target(folder_segments, filename)

        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path = Path(tmp_dir) / filename
            _ = local_path.write_bytes(content)

            command = [
                self._binary,
                "--config",
                self._config_path,
                "copyto",
                str(local_path),
                target,
            ]
            logger.info("uploading %s (%d bytes)", target, len(content))
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )

        if result.returncode != 0:
            raise UploadError(
                f"rclone copyto failed for {target}: {result.stderr.strip()}"
            )
        logger.debug("rclone finished: %s", result.stdout.strip())
