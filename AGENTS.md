# AGENTS.md (Repo Instructions)

## Scope

- Default to minimal, scoped diffs.
- Do not modify `frontend/` or `backend/` unless the task explicitly requires it.
- Prefer adding AI experiment scaffolding/docs under `ai/` before adding code or dependencies.

## Style

- Keep documentation concise and operational (what, where, how to run).
- Use ASCII unless a file already uses non-ASCII.
- Reuse existing naming patterns in `ai/` (versioned prompt/seeds/runbook files).

## Safety

- Do not add heavy ML dependencies or training code unless explicitly requested.
- Do not delete user data, datasets, or experiment outputs.
- Remove obvious junk files only when clearly unrelated (temporary exports, accidental binaries).

## Validation

- For AI-doc-only changes, run lightweight checks only (file existence, formatting, syntax checks if code changed).
- If backend files are touched, prefer non-invasive validation (for example `node --check` on changed JS files) before running servers.
- Summarize changed paths and any checks performed in the final response.

