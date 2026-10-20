# Four independent Daily AI editions

The homepage must have exactly GPT industry, GPT academic, MiniMax industry and
MiniMax academic. Read `prompts/AI产品产业每日简报.md` or
`prompts/AI学术每日简报.md` in full. Industry uses `ai-products/{model}`;
academic uses `ai-academic/{model}`. Preserve historical combined `ai-daily/`
pages. Do not display a Claude or combined edition on the homepage.

Run `python scripts/render_portal.py --repo . --workspace ..` after publishing.
It derives each card's date and count from real edition files. Do not use global
date replacement, duplicate cards, placeholder counts or copy a brief over root
`index.html`. Retain the early centered dark homepage design and the original
brief CSS. Do not modify other models' prose without explicit user permission.
Stage only intended files, preserve unrelated changes, redact remote credentials,
and verify Cloudflare page content and internal links after pushing.

Archives: every new dated issue must include archive.json with an event-specific
title (8–100 characters) and content summary (40–200 characters), not a generic
column introduction. Run `python scripts/render_archives.py --repo . --workspace ..`
then `python scripts/render_archives.py --repo . --check`. Preserve the exact
example/archive.html stylesheet and date/title/summary/view-button layout.
The renderer may rebuild shared/derived archives; do not edit other models'
dated prose or archive.json. Keep pre-split mixed history separate from standalone
academic issues, retain missing-original records without broken links, and check
all internal links, ordering, deduplication and mobile layout before publication.
