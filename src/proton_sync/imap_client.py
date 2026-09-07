"""Read-only IMAP access to Proton Mail via Proton Mail Bridge.

Read-only is enforced two ways:
  * mailboxes are opened with SELECT ... (readonly=True), so no flag or
    expunge command is accepted by the server for this session;
  * messages are fetched with BODY.PEEK[], which does not set \\Seen.
No command in this module writes to the mailbox.
"""

from __future__ import annotations

import imaplib
import logging
import re
import ssl
from dataclasses import dataclass
from types import TracebackType
from typing import Self, cast, final

logger = logging.getLogger(__name__)

_LIST_LINE = re.compile(
    r"""
    ^\( (?P<attributes>[^)]*) \)        # (\HasNoChildren \Junk)
    \s+ (?: "(?P<delimiter>[^"]*)" | NIL )
    \s+ (?:                             # a name is quoted (Proton's contain
      " (?P<quoted>(?:[^"\\]|\\.)*) "   # spaces) or, rarely, a bare atom
      | (?P<atom>\S+)
    ) \s*$
    """,
    re.VERBOSE,
)


class ImapError(RuntimeError):
    pass


@dataclass(frozen=True)
class Mailbox:
    """A mailbox as the server advertises it in a LIST reply.

    `name` is kept exactly as the server spelled it (modified UTF-7 included)
    because it is what SELECT has to be given back.
    """

    name: str
    attributes: frozenset[str]

    def has_attribute(self, attribute: str) -> bool:
        return attribute.lower() in self.attributes


def parse_list_line(line: bytes) -> Mailbox | None:
    """Turn one raw LIST reply line into a Mailbox, or None if unparsable."""
    match = _LIST_LINE.match(line.decode("ascii", errors="replace").strip())
    if match is None:
        # Literal-form names ({12}\r\n...) arrive as tuples and are handled by
        # the caller; anything else reaching here is a server quirk.
        logger.warning("could not parse LIST reply line: %r", line)
        return None

    quoted = match.group("quoted")
    if quoted is not None:
        name = quoted.replace('\\"', '"').replace("\\\\", "\\")
    else:
        name = cast("str", match.group("atom"))
    attributes = frozenset(
        attribute.lower() for attribute in match.group("attributes").split()
    )
    return Mailbox(name=name, attributes=attributes)


def _build_ssl_context(cert_path: str | None) -> ssl.SSLContext:
    context = ssl.create_default_context()
    if cert_path:
        # Bridge issues its own certificate for 127.0.0.1/localhost, but inside
        # compose we reach it on the service hostname, so pin the certificate
        # and skip the hostname check rather than dropping verification.
        context.check_hostname = False
        context.load_verify_locations(cafile=cert_path)
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        logger.warning(
            "IMAP_CERT_PATH not set: bridge TLS certificate will not be verified"
        )
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


@final
class ReadOnlyImapClient:
    _host: str
    _port: int
    _username: str
    _password: str
    _context: ssl.SSLContext
    _conn: imaplib.IMAP4 | None

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        cert_path: str | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._context = _build_ssl_context(cert_path)
        self._conn = None

    def __enter__(self) -> Self:
        logger.debug("connecting to bridge at %s:%s", self._host, self._port)
        conn = imaplib.IMAP4(self._host, self._port)
        _ = conn.starttls(self._context)
        _ = conn.login(self._username, self._password)
        self._conn = conn
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._conn is None:
            return
        try:
            _ = self._conn.close()
        except imaplib.IMAP4.error:
            logger.debug("no mailbox open at close time")
        try:
            _ = self._conn.logout()
        except imaplib.IMAP4.error:
            logger.warning("IMAP logout failed", exc_info=True)
        self._conn = None

    @property
    def _connection(self) -> imaplib.IMAP4:
        if self._conn is None:
            raise ImapError("IMAP client used outside of its context manager")
        return self._conn

    def list_mailboxes(self) -> list[Mailbox]:
        """Every mailbox the bridge exposes, with its LIST attributes."""
        status, data = self._connection.list()
        if status != "OK":
            raise ImapError(f"LIST failed: {status}")

        mailboxes: list[Mailbox] = []
        for item in cast("list[object]", data):
            if isinstance(item, tuple):
                # Literal form: (b'(\\attrs) "/" {n}', b'name'). Re-quote the
                # name so the line parses like the inline form.
                prefix, raw_name = cast("tuple[bytes, bytes]", item[:2])
                line = (
                    re.sub(rb"\{\d+\}$", b"", prefix.strip()) + b' "' + raw_name + b'"'
                )
            elif isinstance(item, bytes):
                line = item
            else:
                continue

            mailbox = parse_list_line(line)
            if mailbox is not None:
                mailboxes.append(mailbox)
        return mailboxes

    def select_readonly(self, mailbox: str) -> int:
        """Open a mailbox read-only and return its UIDVALIDITY."""
        conn = self._connection
        status, _ = conn.select(f'"{mailbox}"', readonly=True)
        if status != "OK":
            raise ImapError(f"could not select mailbox {mailbox!r}: {status}")

        _, validity = conn.response("UIDVALIDITY")
        raw_validity = cast("list[object]", validity)[0] if validity else None
        if not isinstance(raw_validity, (bytes, str)):
            raise ImapError(f"mailbox {mailbox!r} returned no UIDVALIDITY")
        return int(raw_validity)

    def uids_after(self, last_uid: int) -> list[int]:
        """UIDs greater than last_uid in the currently selected mailbox."""
        status, data = self._connection.uid("SEARCH", f"UID {last_uid + 1}:*")
        if status != "OK":
            raise ImapError(f"UID SEARCH failed: {status}")

        payload = cast("list[object]", data)[0] if data else None
        if not isinstance(payload, (bytes, str)):
            return []
        # "UID n:*" always matches at least the highest UID even when nothing is
        # new, so the range still has to be filtered client-side.
        return sorted(uid for uid in map(int, payload.split()) if uid > last_uid)

    def fetch_raw(self, uid: int) -> bytes | None:
        """Fetch a full message without setting \\Seen."""
        status, data = self._connection.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if status != "OK":
            raise ImapError(f"UID FETCH {uid} failed: {status}")
        for item in cast("list[object]", data):
            if isinstance(item, tuple) and isinstance(item[1], bytes):
                return item[1]
        logger.warning("UID %s returned no message body", uid)
        return None
