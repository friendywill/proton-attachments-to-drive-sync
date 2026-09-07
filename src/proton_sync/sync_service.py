"""One sync pass: scan mailboxes, upload any attachments not seen before."""

from __future__ import annotations

import logging
from typing import final

from . import message_parser
from . import naming_proton_drive_paths as drive_paths
from .config import Settings
from .drive_uploader import DriveUploader, UploadError
from .imap_client import ImapError, ReadOnlyImapClient
from .selecting_mailboxes_to_sync import select_targets
from .state_store import StateStore

logger = logging.getLogger(__name__)


@final
class SyncService:
    _settings: Settings
    _state: StateStore
    _uploader: DriveUploader

    def __init__(
        self, settings: Settings, state: StateStore, uploader: DriveUploader
    ) -> None:
        self._settings = settings
        self._state = state
        self._uploader = uploader

    def run_once(self) -> None:
        with ReadOnlyImapClient(
            host=self._settings.imap_host,
            port=self._settings.imap_port,
            username=self._settings.imap_username,
            password=self._settings.imap_password,
            cert_path=self._settings.imap_cert_path,
        ) as client:
            targets = select_targets(
                client.list_mailboxes(),
                excluded_names=self._settings.excluded_mailboxes,
                sent_mailbox_name=self._settings.sent_folder_name,
            )
            logger.info(
                "scanning %d mailbox(es): %s",
                len(targets),
                ", ".join(target.mailbox for target in targets),
            )
            for target in targets:
                try:
                    self._sync_mailbox(client, target.mailbox, sent=target.sent)
                except ImapError:
                    # One unreadable mailbox must not stop the rest of the pass.
                    logger.exception("skipping mailbox %s this pass", target.mailbox)

    def _sync_mailbox(
        self, client: ReadOnlyImapClient, mailbox: str, sent: bool
    ) -> None:
        uid_validity = client.select_readonly(mailbox)
        cursor = self._state.get_cursor(mailbox)

        if cursor is None:
            last_uid = 0
        elif cursor[0] != uid_validity:
            # Proton renumbered the mailbox; rescan from the start. Message-ID
            # dedupe stops anything being uploaded twice.
            logger.warning(
                "UIDVALIDITY for %s changed (%s -> %s), rescanning mailbox",
                mailbox,
                cursor[0],
                uid_validity,
            )
            last_uid = 0
        else:
            last_uid = cursor[1]

        uids = client.uids_after(last_uid)
        if not uids:
            logger.debug("no new messages in %s", mailbox)
            return

        logger.info("%s: %d new message(s) to inspect", mailbox, len(uids))
        for uid in uids:
            try:
                self._process_uid(client, mailbox, uid, sent=sent)
            except UploadError:
                # Leave the cursor behind this UID so the next pass retries it.
                logger.exception("upload failed for %s UID %s", mailbox, uid)
                return
            self._state.set_cursor(mailbox, uid_validity, uid)

    def _process_uid(
        self, client: ReadOnlyImapClient, mailbox: str, uid: int, sent: bool
    ) -> None:
        raw = client.fetch_raw(uid)
        if raw is None:
            return

        message = message_parser.parse(raw)
        identifier = message.message_id or f"{mailbox}:{uid}"

        if self._state.is_processed(identifier):
            logger.debug("%s already processed, skipping", identifier)
            return

        if not message.attachments:
            self._state.mark_processed(identifier, mailbox)
            return

        folder = (
            drive_paths.folder_for_sent(message.subject, message.chain_number)
            if sent
            else drive_paths.folder_for_received(
                message.sender_email, message.subject, message.chain_number
            )
        )

        for attachment in message.attachments:
            self._uploader.upload(
                content=attachment.content,
                folder_segments=folder,
                filename=drive_paths.attachment_filename(attachment.filename),
            )

        self._state.mark_processed(identifier, mailbox)
        logger.info(
            "synced %d attachment(s) from %s to %s",
            len(message.attachments),
            identifier,
            "/".join(folder),
        )
