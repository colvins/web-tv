# AGENTS.md

## Project

This project is `web-tv`, a production-oriented web TV/VOD system.

The goal is to build an Apple TV-style multi-device web app first, with a clean path to possible future iOS/tvOS migration.

The system imports external source configs such as JSON, M3U, M3U8, TXT, CatVod/FongMi-style configs, and generic live/VOD sources.

## Global task rules

- Keep every task small and focused.
- Do not rewrite unrelated files.
- Do not refactor large areas unless explicitly requested.
- Prefer minimal, targeted changes.
- Keep prompts, code changes, and final reports concise.
- Use English for task execution notes, commit messages, code comments, and technical summaries unless the user explicitly asks for Chinese.
- If dependencies or tools are missing in the environment, install the required dependency/tool and continue.
- Do not downgrade features, dependencies, architecture, or implementation quality to work around missing tools.
- Do not use temporary design thinking. Use production-oriented structure from the start.
- Do not switch from PostgreSQL/Redis/Docker architecture to SQLite or local-only temporary storage.
- Do not add seed/fake data unless explicitly requested.
- Do not batch-probe channel URLs or external media URLs unless explicitly requested.
- Do not execute spider/JAR/JS/Python/ext code from imported sources.
- Do not load dynamic CatVod/FongMi spider runtime unless a sandboxed runtime design is explicitly requested.
- Analyze unknown source formats safely before deciding how to store or use them.

## Frontend rules

- Maintain an Apple TV-style UI: dark theme, glass panels, premium spacing, smooth focus/hover states, large media-first layout.
- Do not make mobile layouts feel cramped.
- Touch targets must be comfortable on mobile.
- Desktop, tablet, and mobile behavior should be considered separately when layout or playback is affected.
- For multi-platform UI changes, prefer splitting platform-specific logic/styles into clear sections or separate components/files instead of piling everything into one large view file.
- Preserve current playback state unless the user explicitly selects another channel or stops playback.
- Avoid hiding important controls behind hover-only behavior on touch devices.
- Fullscreen playback must not keep rounded-corner clipping.
- Non-fullscreen player cards may keep rounded Apple-style corners.
- Browser fullscreen and mobile Safari native fullscreen behavior should both be considered.

## Playback rules

- Live playback should load only the selected channel URL.
- Do not batch test or probe all channel stream URLs.
- Prefer browser-native playback where possible.
- Use hls.js only when needed for HLS playback in browsers that do not support it natively.
- For TS streams, use the browser video element first; do not introduce a heavy decoder/runtime unless explicitly requested.
- If a stream fails, show a clean user-facing error state without breaking the channel list or current page.
- Do not add server-side media proxy/transcoding unless explicitly requested.

## Source import rules

- Source import must be safe and metadata-first.
- Store enough metadata to inspect source structure later.
- Do not execute imported code.
- Do not fetch nested URLs unless the task explicitly asks for it.
- For FongMi/CatVod-style configs, separate root config analysis, spider artifact analysis, and actual spider runtime work.
- Spider runtime work requires an explicit sandbox design before implementation.

## Backend rules

- Keep APIs small and explicit.
- Prefer read-only inspection endpoints before destructive or execution endpoints.
- Preserve existing database migrations.
- Add migrations only when schema changes are needed.
- Keep import/extract operations idempotent where possible.
- Avoid duplicate rows when re-importing the same source.

## Docker and environment rules

- This project runs under Docker Compose.
- Do not remove volumes or destroy user data.
- Do not change ports, public exposure, Cloudflare/Nginx assumptions, or deployment shape unless explicitly requested.
- If IPv6 is required by a source, keep Docker IPv6 support intact.
- Verification should use the existing Docker Compose environment.

## Verification rules

For normal code changes, run the relevant checks:

- `npm run build` when frontend changes are made.
- Backend import/compile check when backend Python files change.
- `docker compose config`
- `docker compose up -d --build`
- `curl -fsS http://127.0.0.1:8080/api/v1/health`
- Check affected frontend routes with `curl -fsS`, such as `/live`, `/vod`, or `/settings/sources`.

If verification fails:

- Fix the issue and rerun relevant checks.
- Do not commit or push failing work.

## Git rules

- At the beginning of a task, check `git status`.
- Do not overwrite unrelated user changes.
- Commit only files that are part of the requested task.
- Use short English commit messages.
- If the task passes verification, commit the changes.
- Push only when the user explicitly requested push, or when the task request clearly says to commit and push.
- If verification fails, do not commit or push.
- In the final report, include:
  - files changed
  - what changed
  - verification results
  - whether commit/push was performed
  - any known limitation or manual browser check that could not be performed

## Codex task style

- Keep final reports short and factual.
- Mention clearly if browser behavior was not manually verified.
- Mention clearly if no channel URLs were batch-probed.
- Mention clearly if no spider/JAR/JS/Python/ext code was executed.
