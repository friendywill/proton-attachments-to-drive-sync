# Proton Mail Attachments → Proton Drive

Copies every attachment from Proton Mail into Proton Drive, one folder per
sender and one subfolder per message in a thread.

```
My Files/Proton Mail Attachments/
├── sender@example.com/
│   └── Invoice (3)/
│       └── invoice.pdf
└── My Sent Emails/
    └── Quote (1)/
        └── quote.pdf
```

Messages with no attachments are recorded as seen and otherwise ignored.

## How it works

| Container | Role |
|---|---|
| `bridge` | Proton Mail Bridge. Exposes Proton Mail as local IMAP. |
| `app` | Python sync loop. Reads IMAP, uploads via `rclone`. |

Every 60 seconds the app asks the bridge for its mailbox list and scans each one
for UIDs above the last one it processed, parses attachments out of each new
message, and uploads them with `rclone copyto`. Processed Message-IDs are
recorded in SQLite, so a rescan never re-uploads.

Mail found in the mailbox tagged `\Sent` (or named `SENT_FOLDER_NAME`) goes to
`My Sent Emails/`; everything else is filed under the sender's address.

### Which mailboxes are scanned

`INBOX`, `Archive`, `Sent` and every custom folder under `Folders/`. Skipped by
default, and overridable with `EXCLUDED_MAILBOXES`:

| Skipped | Why |
|---|---|
| `Snoozed`, `Trash`, `Spam` | Requested exclusions. |
| `Drafts` | Unsent mail; the same attachment arrives again, under a different Message-ID, once the mail is actually sent. |
| `All Mail`, `Starred`, `Labels/*` | Duplicate listings — a Proton message lives in one folder but carries any number of labels, and `Starred` is a label. Scanning them would refetch the whole account every minute. |

## Access model — read this before running

Proton has **no public API and no scoped tokens** for Mail or Drive. Both
requirements in `CLAUDE.md` are therefore enforced by this application, not by
Proton:

- **Read-only mail** — mailboxes are opened with `SELECT ... (readonly)` and
  messages fetched with `BODY.PEEK[]`, so no flag is set and no message is
  modified or deleted. No write command exists in `imap_client.py`.
- **Folder-limited Drive** — `drive_uploader.py` builds every destination under
  `DRIVE_ROOT_PATH` and rejects path segments containing `/`, `\` or `..`. The
  rclone remote itself has full account access; nothing outside that root is
  ever written by this app.

Both bootstrap steps below hand full account credentials to a container. Keep
`.env` and `config/rclone/` out of version control (both are gitignored).

## Setup

### 1. Bridge login (one time, interactive)

Proton Mail Bridge cannot complete a first login headlessly.

```bash
docker compose build bridge
docker compose up -d bridge
docker compose exec bridge protonmail-bridge --cli
```

In the bridge CLI: `login`, then `info` to print the IMAP username, the
bridge-generated password and the port and connection mode in use. Those
credentials go in `.env` — they are not your Proton account password.

Restart the bridge afterwards (`docker compose restart bridge`) so the
long-running process picks the account up.

`bridge/Dockerfile` adds `libfido2-1` to the base image. Bridge updates itself
into its volume, and builds from 3.20 onwards need that library; without it the
updated binary exits with `libfido2.so.1: cannot open shared object file` and
the IMAP port answers connections but never sends a greeting, which surfaces in
the app as `imaplib.IMAP4.abort: socket error: EOF`.

### 2. rclone remote (one time, interactive)

If you require 2FA:

  1. ensure the `.env` file is ready,
  2. run the config command as shown below,
  3. when entering the TOTP code, ensure the code has just been refreshed, and;
  4. quickly run `docker compose up -d`, so the TOTP does not expire.
     This will not need to be done again.

```bash
docker compose run --rm \
  -v ./config/rclone:/config/rclone \
  app rclone --config /config/rclone/rclone.conf config
```

Create a remote named `protondrive` using the `protondrive` backend.

### 3. Configure and run

```bash
cp .env.example .env   # fill in the bridge credentials
docker compose up -d
```

Logs go to stdout and to `./logs/proton-sync.log` (10 MB × 5 rotation).

## Local development

```bash
pixi run test    # pytest
pixi run lint    # ruff check
pixi run fmt     # ruff format
```

## Known limitations

- **Chain number** is derived from the `References` header (ancestors + 1),
  because IMAP exposes no thread depth. A client that omits `References`
  produces a less accurate number.
- **Bridge TLS certificate** — set `IMAP_CERT_PATH` to the bridge certificate
  inside the container to pin it. Left unset, the TLS connection to the bridge
  is unverified; it stays on the internal compose network either way. Confirm
  the certificate path against the bridge image in use.
- The **rclone protondrive backend is experimental** upstream.
