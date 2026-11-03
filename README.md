# mystuff-py

## Layer Separation
Routes → Services → Repositories → Models

## Editor snapshot sync

The editor-facing note index is `GET /api/notes/editor-documents`. It returns
the browser's camel-case document timestamps and editor document, plus
`hasEditorDocument`, `requiresMigration`, pin, folder, and color metadata.
Supports `folder_id`, `q`, `pinned_only`, `limit` (maximum 100), and `offset`.
Legacy note bodies are returned as metadata with `document: null` and
`requiresMigration: true`; they are never converted or overwritten implicitly.

The note editor uses `PUT /api/notes/{note_id}/editor-snapshot` to create or
replace a complete editor document. Send JSON with `baseRevision` and
`document`; the response includes the new server `revision`. Use
`GET /api/notes/{note_id}/editor-snapshot` to fetch the current document.
Both endpoints use the existing `access_token` cookie and note owner/share
permissions. A stale `baseRevision` returns `409` with the current revision
and snapshot so clients do not silently overwrite concurrent edits. Legacy
notes with existing plaintext content are not replaced automatically; the
snapshot endpoint reports that migration is required.

The WebSocket requires a valid `access_token` cookie. A handshake rejected
with HTTP 403 is logged with a reason such as `origin_not_allowed`,
`missing_access_token`, or `invalid_access_token`; never work around this by
putting the token in the WebSocket URL. For local development, use the same
hostname (`localhost`, not a mix of `localhost` and `127.0.0.1`) for the
frontend and API, sign in so the API cookie is set, and allow the frontend's
exact origin in `ALLOWED_ORIGINS`.
For plain-HTTP local development, set `DEBUG=true` so the auth cookie is not
marked `Secure`; keep `DEBUG=false` and HTTPS in production.

For realtime updates, connect to `/ws/sync/{note_id}` with the same
`access_token` cookie. WebSocket origins must exactly match `ALLOWED_ORIGINS`.
The connection exchanges full document snapshots with optimistic revisions;
it does not merge simultaneous character-level edits. Room membership is
currently process-local, so run a single API worker until a shared pub/sub
backend is configured.

Set a stable, randomly generated `NOTE_ENCRYPTION_KEY` in the API environment.
It must be a separate secret from `SECRET_KEY` and at least 32 characters
(for example, generate a value with `openssl rand -hex 32`). The server uses
AES-256-GCM to encrypt editor document JSON in the existing `notes.content`
column, so no schema migration is needed. The note title remains plaintext for
existing list/search behavior. The server decrypts snapshots for authorized
users, so this is encryption at rest, not end-to-end encryption. Do not rotate
the key without first re-encrypting existing snapshots; a missing or invalid
key causes sync requests to fail explicitly.

Reminder
uv run python ...
uv run pytest
uv sync --all-groups