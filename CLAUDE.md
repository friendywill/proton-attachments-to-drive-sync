# Proton Mail Attachments Sync to Proton Drive

## Overview

Build system: every attachment ever received in Proton Mail syncs to Proton Drive. Path: Proton Drive > My Files > Proton Mail Attachments > <email_address@example.com> > <Mail Subject (Number which increases based on which email this is in the chain)> > <attachment_name.pdf>.

No attachments = do nothing.

<email_address@example.com> = folder named after sender email address. <Mail Subject (Number...)> = subfolder with email subject + number of that email in chain (third response = 3). <attachment_name.pdf> = original attachment name. Multiple files = multiple files in folder.

Separate folder for sent emails: Proton Drive > My Files > Proton Mail Attachments > My Sent Emails > <Mail Subject (Number which increases based on which email this is in the chain)> > <attachment_name.pdf>.

## Requirements

- Read-only access to Proton emails.
- Proton Drive permissions limited to specific folder.
- Each component runs in docker container, via docker compose.
- Check once every minute.
- Multiple containers OK — e.g. one for mail bridge, one for app.

## Other instructions

- Prefer Python. Deviation needs express permission.
- Use proper logger, not prints.

## Commit Style

Follow conventional commits guide:

Conventional Commits = lightweight convention on top of commit messages. Simple rules for explicit commit history; easier to build automated tools on. Dovetails with SemVer by describing features, fixes, breaking changes.

Structure commit message:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Structural elements communicate intent to library consumers:

- fix: patches bug (= PATCH in SemVer).
- feat: adds new feature (= MINOR in SemVer).
- BREAKING CHANGE: footer BREAKING CHANGE:, or ! after type/scope = breaking API change (= MAJOR in SemVer). Can appear in any type.
- Types other than fix:/feat: allowed. @commitlint/config-conventional (Angular convention) recommends build:, chore:, ci:, docs:, style:, refactor:, perf:, test:, others.
- Footers other than BREAKING CHANGE: <description> allowed, follow git trailer format.

Extra types not mandated by spec, no implicit SemVer effect (unless BREAKING CHANGE). Scope may follow type for context, in parenthesis, e.g. feat(parser): add ability to parse arrays.

## Examples

Description + breaking change footer

```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for extending other
config files
```

! to flag breaking change

```
feat!: send an email to the customer when a product is shipped
```

Scope + ! to flag breaking change

```
feat(api)!: send an email to the customer when a product is shipped
```

Both ! and BREAKING CHANGE footer

```
feat!: drop support for Node 6

BREAKING CHANGE: use JavaScript features not available in Node 6.
```

No body

```
docs: correct spelling of CHANGELOG
```

With scope

```
feat(lang): add Polish language
```

Multi-paragraph body + multiple footers

```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.

Reviewed-by: Z
Refs: #123
```

Specification

Key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", "OPTIONAL" interpreted per RFC 2119.

  1.  Commits MUST be prefixed with type (noun: feat, fix, etc.), then OPTIONAL scope, OPTIONAL !, REQUIRED terminal colon and space.
  2.  Type feat MUST be used when commit adds new feature.
  3.  Type fix MUST be used when commit is bug fix.
  4.  Scope MAY follow type. Scope MUST be noun describing codebase section, in parenthesis, e.g. fix(parser):
  5.  Description MUST immediately follow colon+space after type/scope prefix. Description = short summary of code changes, e.g. fix: array parsing issue when multiple spaces were contained in string.
  6.  Longer body MAY follow short description with more context. Body MUST begin one blank line after description.
  7.  Body free-form, MAY be any number of newline-separated paragraphs.
  8.  One or more footers MAY follow one blank line after body. Each footer MUST be word token, then `:<space>` or `<space>#` separator, then string value (inspired by git trailer convention).
  9.  Footer token MUST use - in place of whitespace, e.g. Acked-by (differentiates footer section from multi-paragraph body). Exception: BREAKING CHANGE, which MAY also be token.
  10. Footer value MAY contain spaces and newlines. Parsing MUST terminate at next valid footer token/separator pair.
  11. Breaking changes MUST be indicated in type/scope prefix or as footer entry.
  12. As footer, breaking change MUST be uppercase BREAKING CHANGE, then colon, space, description, e.g. BREAKING CHANGE: environment variables now take precedence over config files.
  13. In type/scope prefix, breaking changes MUST use ! immediately before :. If ! used, BREAKING CHANGE: MAY be omitted from footer, and description SHALL describe the breaking change.
  14. Types other than feat and fix MAY be used, e.g. docs: update ref docs.
  15. Conventional Commits units MUST NOT be treated as case-sensitive by implementors, except BREAKING CHANGE which MUST be uppercase.
  16. BREAKING-CHANGE MUST be synonymous with BREAKING CHANGE as footer token.

Commit subject ≤50 chars if possible. Column width limit for description = 80 chars; at 80, new line to continue.

## Record all prompts

Record all prompts to Claude and Claude responses in CLAUDE-HISTORY.md.