"""Build the Proton Drive folder path for a message's attachments.

Received mail:
    <root>/<sender@example.com>/<Subject (N)>/<attachment.pdf>
Sent mail:
    <root>/My Sent Emails/<Subject (N)>/<attachment.pdf>
"""

from __future__ import annotations

import re

SENT_FOLDER = "My Sent Emails"

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")

MAX_SEGMENT_LENGTH = 120


def sanitise(name: str, fallback: str) -> str:
    """Make one path segment safe for Drive, Windows and POSIX clients."""
    cleaned = _ILLEGAL_CHARS.sub("_", name)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    cleaned = cleaned.rstrip(". ")
    if len(cleaned) > MAX_SEGMENT_LENGTH:
        cleaned = cleaned[:MAX_SEGMENT_LENGTH].rstrip(". ")
    return cleaned or fallback


def sender_folder(sender_email: str) -> str:
    return sanitise(sender_email.strip().lower(), fallback="unknown-sender")


def thread_folder(subject: str, chain_number: int) -> str:
    """Subject folder, suffixed with the message's position in its chain."""
    return f"{sanitise(subject, fallback='no-subject')} ({chain_number})"


def attachment_filename(filename: str) -> str:
    return sanitise(filename, fallback="attachment")


def folder_for_received(sender_email: str, subject: str, chain_number: int) -> list[str]:
    return [sender_folder(sender_email), thread_folder(subject, chain_number)]


def folder_for_sent(subject: str, chain_number: int) -> list[str]:
    return [SENT_FOLDER, thread_folder(subject, chain_number)]
