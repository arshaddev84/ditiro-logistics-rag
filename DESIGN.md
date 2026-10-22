# Design

## Primary Experience

The homepage is a single evidence-retrieval chat, styled as a quiet, ChatGPT-like conversation. Settings is a bottom-of-page control that opens a modal; it is not a separate dashboard view.

## Chat

- Keep the prompt and conversation centered with a restrained maximum width.
- Offer a few suggested logistics questions only when the conversation is empty.
- Submit on Enter and preserve Shift+Enter for a new line.
- Expand source rows to inspect retrieved text, source location, and similarity percentage.
- Clearly label similarity as a ranking signal, not accuracy.
- Show errors and no-evidence responses without fabricating citations.

## Settings Modal

- Show PostgreSQL, Qdrant, and Ollama status, plus active generation/embedding model names.
- Show total indexed documents, a small source preview, and the number of indexed PostgreSQL records.
- Provide re-index and forget controls with progress, result messages, and confirmation before forgetting.
- Clarify that forgetting removes indexed copies only, not source files or operational database rows.
- Close on Escape, close-button activation, or backdrop click; on mobile, present as a bottom sheet.

## Visual System

- Retain the green, copper, off-white, and white palette already used in the application.
- Use restrained serif headings and readable sans-serif interface text.
- Keep source evidence expandable and layouts responsive.
- Use lucide icons and accessible labels for icon-only controls.
- Maintain visible focus states and live announcements for chat and action status.
