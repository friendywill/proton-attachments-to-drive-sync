"""Environment-driven configuration for the sync service."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .selecting_mailboxes_to_sync import DEFAULT_EXCLUDED_MAILBOXES

_ = load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def _excluded_mailboxes() -> tuple[str, ...]:
    """Mailbox names to skip, comma-separated, overriding the defaults."""
    raw = os.environ.get("EXCLUDED_MAILBOXES")
    if raw is None:
        return DEFAULT_EXCLUDED_MAILBOXES
    return tuple(name.strip() for name in raw.split(",") if name.strip())


@dataclass(frozen=True)
class Settings:
    imap_host: str
    imap_port: int
    imap_username: str
    imap_password: str
    imap_cert_path: str | None

    sent_folder_name: str
    excluded_mailboxes: tuple[str, ...]
    poll_interval_seconds: int

    state_db_path: str

    drive_remote_name: str
    drive_root_path: str
    rclone_config_path: str

    log_level: str
    log_dir: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            imap_host=os.environ.get("IMAP_HOST", "bridge"),
            imap_port=int(os.environ.get("IMAP_PORT", "1143")),
            imap_username=_require("IMAP_USERNAME"),
            imap_password=_require("IMAP_PASSWORD"),
            imap_cert_path=os.environ.get("IMAP_CERT_PATH") or None,
            sent_folder_name=os.environ.get("SENT_FOLDER_NAME", "Sent"),
            excluded_mailboxes=_excluded_mailboxes(),
            poll_interval_seconds=int(os.environ.get("POLL_INTERVAL_SECONDS", "60")),
            state_db_path=os.environ.get("STATE_DB_PATH", "/data/state.sqlite3"),
            drive_remote_name=os.environ.get("DRIVE_REMOTE_NAME", "protondrive"),
            drive_root_path=os.environ.get(
                "DRIVE_ROOT_PATH", "My Files/Proton Mail Attachments"
            ),
            rclone_config_path=os.environ.get(
                "RCLONE_CONFIG_PATH", "/config/rclone/rclone.conf"
            ),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            log_dir=os.environ.get("LOG_DIR", "/logs"),
        )
