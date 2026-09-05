from proton_sync import naming_proton_drive_paths as drive_paths


def test_illegal_characters_are_replaced():
    assert drive_paths.sanitise('in/voice:2024?', "x") == "in_voice_2024_"


def test_empty_name_falls_back():
    assert drive_paths.sanitise("   ", "no-subject") == "no-subject"


def test_long_name_is_truncated():
    assert len(drive_paths.sanitise("a" * 500, "x")) == drive_paths.MAX_SEGMENT_LENGTH


def test_received_folder_layout():
    assert drive_paths.folder_for_received("Bob@Example.COM", "Invoice", 3) == [
        "bob@example.com",
        "Invoice (3)",
    ]


def test_sent_folder_layout():
    assert drive_paths.folder_for_sent("Invoice", 1) == [
        "My Sent Emails",
        "Invoice (1)",
    ]
