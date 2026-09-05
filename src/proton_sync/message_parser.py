"""Parse RFC822 messages into the bits the sync needs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from email import message_from_bytes, policy
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.utils import parseaddr

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes


@dataclass(frozen=True)
class ParsedMessage:
    message_id: str
    sender_email: str
    subject: str
    chain_number: int
    attachments: list[Attachment]


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (UnicodeDecodeError, LookupError, ValueError):
        logger.warning("could not decode header, falling back to raw value")
        return value


def chain_number(message: Message) -> int:
    """Position of this message within its thread.

    Proton exposes no thread depth over IMAP, so this is derived from the
    References header: each ancestor contributes one Message-ID, and this
    message is the next link in the chain.
    """
    references = message.get("References", "")
    ancestors = [ref for ref in references.split() if ref.strip()]
    if not ancestors:
        # A reply whose client omitted References is still at least the second
        # message in its chain.
        return 2 if message.get("In-Reply-To") else 1
    return len(ancestors) + 1


def extract_attachments(message: EmailMessage) -> list[Attachment]:
    attachments: list[Attachment] = []
    for part in message.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if not filename:
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            logger.warning("attachment %s has no decodable payload, skipping", filename)
            continue
        attachments.append(Attachment(filename=_decode(filename), content=payload))
    return attachments


def parse(raw: bytes) -> ParsedMessage:
    # policy.default makes message_from_bytes return an EmailMessage.
    message = message_from_bytes(raw, policy=policy.default)
    _, sender_email = parseaddr(_decode(message.get("From")))

    return ParsedMessage(
        message_id=(message.get("Message-ID") or "").strip(),
        sender_email=sender_email,
        subject=_decode(message.get("Subject")),
        chain_number=chain_number(message),
        attachments=extract_attachments(message),
    )
