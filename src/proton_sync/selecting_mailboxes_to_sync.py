"""Choose which of the bridge's mailboxes a sync pass should scan.

Proton Mail Bridge exposes every Proton location over IMAP: INBOX, the system
mailboxes (Drafts, Sent, Starred, Archive, Spam, Trash, All Mail, Snoozed),
custom folders under "Folders/", and labels under "Labels/". A message lives in
exactly one folder but can carry any number of labels, so three of those groups
are pure duplicates of mail that is already scanned elsewhere:

  * "All Mail" holds a copy of every message in the account;
  * "Labels/<name>" only ever re-lists a message that is also in INBOX,
    Archive or a custom folder;
  * "Starred" is a label too, despite being presented as a system mailbox.

All three are skipped so a pass does not refetch the whole account each minute.
Message-ID dedupe in the state store is the safety net, not the plan.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from .imap_client import Mailbox

logger = logging.getLogger(__name__)

# Excluded by default, matched case-insensitively against the mailbox name.
DEFAULT_EXCLUDED_MAILBOXES: tuple[str, ...] = (
    "Snoozed",
    "Trash",
    "Spam",
    "Drafts",
    "All Mail",
    "Starred",
)

# Servers may advertise the same mailboxes by special-use attribute instead of
# by name, so exclude on either. \Noselect and \NonExistent cannot be SELECTed
# at all -- "Folders" and "Labels" are such container-only entries on bridge.
_EXCLUDED_ATTRIBUTES = frozenset(
    {
        "\\noselect",
        "\\nonexistent",
        "\\trash",
        "\\junk",
        "\\drafts",
        "\\all",
    }
)

_SENT_ATTRIBUTE = "\\sent"
_LABEL_PREFIX = "labels/"


@dataclass(frozen=True)
class SyncTarget:
    """A mailbox to scan, plus where its attachments belong on Drive."""

    mailbox: str
    sent: bool


def _is_label(name: str) -> bool:
    return name.lower().startswith(_LABEL_PREFIX)


def select_targets(
    mailboxes: Iterable[Mailbox],
    excluded_names: Iterable[str],
    sent_mailbox_name: str,
) -> list[SyncTarget]:
    """Filter a LIST result down to the mailboxes worth scanning."""
    excluded = {name.strip().lower() for name in excluded_names if name.strip()}
    targets: list[SyncTarget] = []

    for mailbox in mailboxes:
        name = mailbox.name
        if any(mailbox.has_attribute(attr) for attr in _EXCLUDED_ATTRIBUTES):
            logger.debug("skipping %s: excluded by LIST attribute", name)
            continue
        if name.lower() in excluded:
            logger.debug("skipping %s: excluded by name", name)
            continue
        if _is_label(name):
            logger.debug("skipping %s: label duplicates a folder", name)
            continue

        sent = mailbox.has_attribute(_SENT_ATTRIBUTE) or (
            name.lower() == sent_mailbox_name.strip().lower()
        )
        targets.append(SyncTarget(mailbox=name, sent=sent))

    return targets
