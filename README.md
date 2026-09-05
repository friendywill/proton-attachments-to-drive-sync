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

Every 60 seconds the app scans `INBOX` and `Sent` for UIDs above the last one
it processed, parses attachments out of each new message, and uploads them with
`rclone copyto`. Processed Message-IDs are recorded in SQLite, so a rescan
never re-uploads.

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
docker compose up -d bridge
docker compose exec bridge bridge --cli
```

In the bridge CLI: `login`, then `info` to print the IMAP username and the
bridge-generated password. Those go in `.env` — they are not your Proton
account password.

### 2. rclone remote (one time, interactive)

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
