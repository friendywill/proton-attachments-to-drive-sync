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
