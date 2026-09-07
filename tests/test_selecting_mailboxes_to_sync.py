from proton_sync.imap_client import Mailbox, parse_list_line
from proton_sync.selecting_mailboxes_to_sync import (
    DEFAULT_EXCLUDED_MAILBOXES,
    SyncTarget,
    select_targets,
)

BRIDGE_LIST_REPLY = [
    rb'(\HasNoChildren \Inbox) "/" "INBOX"',
    rb'(\HasNoChildren \Sent) "/" "Sent"',
    rb'(\HasNoChildren \Drafts) "/" "Drafts"',
    rb'(\HasNoChildren \Trash) "/" "Trash"',
    rb'(\HasNoChildren \Junk) "/" "Spam"',
    rb'(\HasNoChildren \All) "/" "All Mail"',
    rb'(\HasNoChildren \Archive) "/" "Archive"',
    rb'(\HasNoChildren) "/" "Snoozed"',
    rb'(\HasNoChildren) "/" "Starred"',
    rb'(\Noselect \HasChildren) "/" "Folders"',
    rb'(\HasNoChildren) "/" "Folders/Receipts 2024"',
    rb'(\Noselect \HasChildren) "/" "Labels"',
    rb'(\HasNoChildren) "/" "Labels/Important"',
]


def _bridge_mailboxes() -> list[Mailbox]:
    parsed = [parse_list_line(line) for line in BRIDGE_LIST_REPLY]
    return [mailbox for mailbox in parsed if mailbox is not None]


def _selected() -> list[tuple[str, bool]]:
    targets = select_targets(
        _bridge_mailboxes(),
        excluded_names=DEFAULT_EXCLUDED_MAILBOXES,
        sent_mailbox_name="Sent",
    )
    return [(target.mailbox, target.sent) for target in targets]


def test_parses_quoted_name_and_attributes():
    mailbox = parse_list_line(rb'(\HasNoChildren \Junk) "/" "Spam"')
    assert mailbox is not None
    assert mailbox.name == "Spam"
    assert mailbox.attributes == {"\\hasnochildren", "\\junk"}


def test_parses_unquoted_name_and_nil_delimiter():
    mailbox = parse_list_line(rb"(\HasNoChildren) NIL INBOX")
    assert mailbox is not None
    assert mailbox.name == "INBOX"


def test_unparsable_line_is_dropped():
    assert parse_list_line(b"not a list reply") is None


def test_scans_inbox_archive_and_custom_folders():
    assert _selected() == [
        ("INBOX", False),
        ("Sent", True),
        ("Archive", False),
        ("Folders/Receipts 2024", False),
    ]


def test_excludes_snoozed_trash_and_spam():
    scanned = {name for name, _ in _selected()}
    assert not scanned & {"Snoozed", "Trash", "Spam"}


def test_excludes_duplicate_listings():
    scanned = {name for name, _ in _selected()}
    assert not scanned & {"All Mail", "Starred", "Labels/Important"}


def test_excludes_container_only_mailboxes():
    scanned = {name for name, _ in _selected()}
    assert not scanned & {"Folders", "Labels"}


def test_sent_detected_by_attribute_when_name_differs():
    targets = select_targets(
        [Mailbox(name="Enviados", attributes=frozenset({"\\sent"}))],
        excluded_names=(),
        sent_mailbox_name="Sent",
    )
    assert targets == [SyncTarget(mailbox="Enviados", sent=True)]


def test_exclusion_is_case_insensitive():
    targets = select_targets(
        [Mailbox(name="SPAM", attributes=frozenset())],
        excluded_names=("spam",),
        sent_mailbox_name="Sent",
    )
    assert targets == []
