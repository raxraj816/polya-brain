"""Recognise inputs that are only a link PolyaBrain cannot open."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

# Conversation share pages render client-side or require a signed-in browser.
_SHARE_PAGES = (
    ("chatgpt.com", "/share/", "ChatGPT"),
    ("chat.openai.com", "/share/", "ChatGPT"),
    ("claude.ai", "/share/", "Claude"),
    ("gemini.google.com", "/share/", "Gemini"),
    ("g.co", "/gemini/share/", "Gemini"),
    ("poe.com", "/s/", "Poe"),
    ("perplexity.ai", "/search/", "Perplexity"),
    ("copilot.microsoft.com", "/shares/", "Copilot"),
)


def unreadable_share_link(raw_input: str) -> str | None:
    """Return the product name when the whole input is one conversation share link."""
    text = raw_input.strip()
    if not re.fullmatch(r"https?://\S+", text):
        return None
    parts = urlsplit(text)
    host = (parts.hostname or "").lower().removeprefix("www.")
    for share_host, path_prefix, product in _SHARE_PAGES:
        if host == share_host and parts.path.startswith(path_prefix):
            return product
    return None


def share_link_question(product: str) -> str:
    return (
        f"PolyaBrain cannot open {product} share links: they need a signed-in browser. "
        "Paste the problem or the conversation text you want investigated."
    )
