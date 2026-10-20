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
