"""
EMLParser – extracts structured envelope data from raw .eml files.

Uses only the stdlib `email` package so there are zero native dependencies.
"""

from __future__ import annotations

import email
import email.policy
import email.utils
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.models.schemas import LinkMetadata, RawEmailEnvelope

# Matches most http(s) URLs, including those wrapped in angle brackets.
_URL_RE = re.compile(
    r'https?://[^\s<>"\')\]]+',
    re.IGNORECASE,
)

# Matches <a href="…">…</a> in HTML bodies.
_ANCHOR_RE = re.compile(
    r'<a\b[^>]*href=["\'](?P<url>https?://[^"\']+)["\'][^>]*>'
    r"(?P<text>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)


class EMLParser:
    """
    Stateless parser that converts a `.eml` file path into a
    `RawEmailEnvelope` Pydantic model.

    Usage
    -----
    >>> envelope = EMLParser.parse("path/to/email.eml")
    >>> print(envelope.subject, envelope.sender)
    """

    # ── public API ────────────────────────────────────────────────────

    @staticmethod
    def parse(eml_path: str | Path) -> RawEmailEnvelope:
        """Parse a `.eml` file and return a structured envelope."""
        path = Path(eml_path)
        if not path.exists():
            raise FileNotFoundError(f"EML file not found: {path}")

        raw_bytes = path.read_bytes()
        msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)

        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        recipients = EMLParser._extract_recipients(msg)
        date = EMLParser._parse_date(msg.get("Date"))
        message_id = msg.get("Message-ID")

        body_plain = EMLParser._get_body(msg, "text/plain")
        body_html = EMLParser._get_body(msg, "text/html")

        links = EMLParser._extract_links(body_plain, body_html)
        attachments = EMLParser._extract_attachments(msg)

        return RawEmailEnvelope(
            message_id=message_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            date=date,
            body_plain=body_plain,
            body_html=body_html,
            links=links,
            attachments=attachments,
        )

    # ── internal helpers ──────────────────────────────────────────────

    @staticmethod
    def _extract_recipients(msg: email.message.Message) -> list[str]:
        """Collect all To / Cc / Bcc addresses."""
        addrs: list[str] = []
        for header in ("To", "Cc", "Bcc"):
            value = msg.get_all(header, [])
            for v in value:
                # Handles both "Name <addr>" and bare addresses.
                if isinstance(v, str):
                    addrs.append(v.strip())
        return addrs

    @staticmethod
    def _parse_date(raw: Optional[str]) -> Optional[datetime]:
        """Best-effort date parsing from RFC-2822 header."""
        if not raw:
            return None
        try:
            parsed = email.utils.parsedate_to_datetime(raw)
            # Normalise to UTC if timezone-aware.
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc)
            return parsed
        except Exception:
            return None

    @staticmethod
    def _get_body(msg: email.message.Message, content_type: str) -> str:
        """Walk MIME parts and return decoded text for the given type."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == content_type:
                    payload = part.get_content()
                    return payload if isinstance(payload, str) else ""
        else:
            if msg.get_content_type() == content_type:
                payload = msg.get_content()
                return payload if isinstance(payload, str) else ""
        return ""

    @staticmethod
    def _extract_links(plain: str, html: str) -> list[LinkMetadata]:
        """
        Pull unique URLs from both plain-text and HTML bodies.
        When an anchor tag is available, attach its visible text.
        """
        seen: set[str] = set()
        links: list[LinkMetadata] = []

        # 1) Anchored links from HTML get priority (they carry anchor text).
        for match in _ANCHOR_RE.finditer(html):
            url = match.group("url").strip()
            anchor = match.group("text").strip() or None
            if url not in seen:
                seen.add(url)
                links.append(LinkMetadata(url=url, anchor_text=anchor))

        # 2) Bare URLs from plain text.
        for url in _URL_RE.findall(plain):
            url = url.rstrip(".,;:!?)")
            if url not in seen:
                seen.add(url)
                links.append(LinkMetadata(url=url, anchor_text=None))

        # 3) Any remaining bare URLs in HTML that weren't in <a> tags.
        for url in _URL_RE.findall(html):
            url = url.rstrip(".,;:!?)")
            if url not in seen:
                seen.add(url)
                links.append(LinkMetadata(url=url, anchor_text=None))

        return links

    @staticmethod
    def _extract_attachments(msg: email.message.Message) -> list[str]:
        """Return filenames of all non-inline attachments."""
        names: list[str] = []
        for part in msg.walk():
            disp = part.get_content_disposition()
            if disp == "attachment":
                fn = part.get_filename()
                if fn:
                    names.append(fn)
        return names
