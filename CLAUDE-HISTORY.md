# Claude History

Record of prompts to Claude and the resulting work, per `CLAUDE.md`.

## 2026-09-05 — Initial scaffold

**Prompt:** "Please take a look at CLAUDE.md and make a start on this project
based on that."

**Response summary:**

Read `CLAUDE.md`, flagged that Proton publishes no official API and no scoped
tokens for Mail or Drive, so the read-only-mail and folder-limited-Drive
requirements can only be enforced in application code. Asked for decisions on
tooling.

**Decisions taken:**

| Question | Answer |
|---|---|
| Mail access | Proton Mail Bridge (official, IMAP) |
| Drive access | rclone `protondrive` backend |
| Dev tooling | ruff + pytest as dev extras |
| Type checking | basedpyright via `uvx`, not added as a dependency |
| Package manager | pixi |
| `naming.py` name | renamed to `naming_proton_drive_paths.py` for clarity |
| Logging | added a rotating file handler alongside stdout, `LOG_DIR` env var |

**Built:**

- `src/proton_sync/` — `config`, `logging_conf`, `imap_client`,
  `message_parser`, `naming_proton_drive_paths`, `state_store`,
  `drive_uploader`, `sync_service`, `main`
- `Dockerfile`, `docker-compose.yml` (bridge + app), `.env.example`
- `tests/` — 9 unit tests over path building and message parsing
- `README.md` with the two interactive bootstrap steps and the access model

**Verification:** `pixi run lint` clean, `pixi run test` 9 passed,
`basedpyright` 0 errors.

**Prompt:** "/caveman:compress" → ran on `CLAUDE.md`; original preserved as
`CLAUDE.original.md`.

## 2026-09-07 — Scan every mailbox, not just INBOX

**Prompt:** "It seems this application only checks my inbox folder, modify the
code to search all folders, excluding snoozed, deleted, and spam."

**Prompt:** "why is this called list_mailboxes? Tell me that before continueing"
→ explained the name follows RFC 3501 (`LIST` returns mailboxes) and the
existing vocabulary in `select_readonly`, `_sync_mailbox` and the
`mailbox_cursor` table. **Decision:** keep `list_mailboxes`.

**Built:**

- `imap_client.list_mailboxes()` + `parse_list_line()` — issues `LIST` and
  parses the reply into `Mailbox(name, attributes)`, keeping the server's
  spelling of the name because `SELECT` needs it back verbatim.
- `selecting_mailboxes_to_sync.py` — filters that list into `SyncTarget`s and
  decides which mailbox is the sent one (`\Sent` attribute, else
  `SENT_FOLDER_NAME`).
- `sync_service.run_once()` loops over the selected mailboxes; an `ImapError`
  on one is logged and the pass continues with the rest.
- `EXCLUDED_MAILBOXES` env var, defaulting to `Snoozed,Trash,Spam,Drafts,All
  Mail,Starred`.

**Decisions taken:**

| Question | Answer |
|---|---|
| Beyond the three requested exclusions | Also skip `All Mail`, `Starred` and `Labels/*` — duplicate listings of mail already scanned in its own folder; scanning them refetches the account every minute |
| Drafts | Excluded by default: unsent mail, and the attachment reappears under a new Message-ID once sent. Overridable |
| Custom folders | `Folders/*` scanned; `\Noselect` containers skipped |

**Verification:** `pixi run lint` clean, `pixi run test` 18 passed,
`basedpyright` 0 errors.
