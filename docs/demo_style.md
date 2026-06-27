# Demo Style

Use this style for local terminal demos in this repository.

## Goals

- Make enforcement understandable on first read.
- Keep the flow calm, direct, and operator-friendly.
- Prefer short factual lines over hype or story framing.
- Use ASCII structure where possible so logs remain readable anywhere.

## Output shape

- Start with a short title.
- Show the flow in one line: `plan -> gate -> tools -> receipts -> verify`.
- Use one small legend for statuses.
- Keep sections short and separated by blank lines.
- Prefer concise labels over long paragraphs.

## Status language

- `ALLOW` means the action matched signed scope.
- `CHECKPOINT` means the action is expected but requires human sign-off.
- `BLOCK` means the action is outside signed scope and must not continue.

## Visual rules

- Blue: headers and plan framing.
- Green: allow / verified.
- Yellow: checkpoint / fallback notices.
- Red: block / failures.
- Dim gray: explanation lines and file paths.

## Narrative rules

- Explain what changed from a normal agent in 1-2 lines only.
- Explain signing and tamper evidence in plain language.
- Avoid dramatic language, sales language, or anthropomorphic phrasing.
- Do not hide degraded or mocked paths; label them clearly.
