from email.message import EmailMessage

from proton_sync import message_parser


def _message(*, references: str | None = None, attachments: bool = True) -> bytes:
    msg = EmailMessage()
    msg["From"] = "Bob <bob@example.com>"
    msg["Subject"] = "Invoice"
    msg["Message-ID"] = "<abc@example.com>"
    if references:
        msg["References"] = references
    msg.set_content("body")
    if attachments:
        msg.add_attachment(
            b"%PDF-1.4",
            maintype="application",
            subtype="pdf",
            filename="invoice.pdf",
        )
    return msg.as_bytes()


def test_parses_sender_subject_and_attachment():
    parsed = message_parser.parse(_message())
    assert parsed.sender_email == "bob@example.com"
    assert parsed.subject == "Invoice"
    assert [a.filename for a in parsed.attachments] == ["invoice.pdf"]
    assert parsed.attachments[0].content == b"%PDF-1.4"


def test_chain_number_defaults_to_one():
    assert message_parser.parse(_message()).chain_number == 1


def test_chain_number_counts_references():
    raw = _message(references="<a@x> <b@x>")
    assert message_parser.parse(raw).chain_number == 3


def test_message_without_attachments():
    assert message_parser.parse(_message(attachments=False)).attachments == []
