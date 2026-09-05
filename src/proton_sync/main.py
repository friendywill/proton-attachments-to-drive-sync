"""Entrypoint: run a sync pass on a fixed interval."""

from __future__ import annotations

import logging
import signal
import sys
import threading
from types import FrameType

from .config import Settings
from .drive_uploader import DriveUploader
from .logging_conf import configure_logging
from .state_store import StateStore
from .sync_service import SyncService

logger = logging.getLogger(__name__)

_shutdown = threading.Event()


def _handle_signal(signum: int, _frame: FrameType | None) -> None:
    logger.info("received signal %s, shutting down after current pass", signum)
    _shutdown.set()


def main() -> int:
    settings = Settings.from_env()
    configure_logging(settings.log_level, settings.log_dir)

    _ = signal.signal(signal.SIGTERM, _handle_signal)
    _ = signal.signal(signal.SIGINT, _handle_signal)

    state = StateStore(settings.state_db_path)
    uploader = DriveUploader(
        remote_name=settings.drive_remote_name,
        root_path=settings.drive_root_path,
        rclone_config_path=settings.rclone_config_path,
    )
    service = SyncService(settings, state, uploader)

    logger.info(
        "starting sync loop: every %ss into %s:%s",
        settings.poll_interval_seconds,
        settings.drive_remote_name,
        settings.drive_root_path,
    )

    try:
        while not _shutdown.is_set():
            try:
                service.run_once()
            except Exception:
                logger.exception("sync pass failed, will retry next interval")
            _ = _shutdown.wait(settings.poll_interval_seconds)
    finally:
        state.close()

    logger.info("sync loop stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
