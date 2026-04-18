"""
LinkChecker – evaluates URLs extracted from emails and assigns
a Trust Score (1-10) based on domain reputation heuristics.

This is a *fast, offline-first* scorer:
  • TLD quality and known-good domain lists are checked synchronously.
  • Optional HTTP HEAD probes run via ``httpx`` when network is available.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Optional
from urllib.parse import urlparse

import httpx
import tldextract
from bs4 import BeautifulSoup
from groq import AsyncGroq

from src.models.schemas import (
    LinkMetadata,
    LinkTrust,
    RequirementStatus,
    SiteAnalysis,
    UserProfile,
)

# ── Static reputation lists ──────────────────────────────────────────

# Domains that are almost always trustworthy.
_TRUSTED_DOMAINS: set[str] = {
    "google.com", "github.com", "linkedin.com", "microsoft.com",
    "apple.com", "amazon.com", "edu", "gov", "ac.uk", "stanford.edu",
    "mit.edu", "harvard.edu", "nust.edu.pk", "lums.edu.pk",
    "nu.edu.pk", "hec.gov.pk",
    "zoom.us", "teams.microsoft.com", "docs.google.com",
    "forms.gle", "eventbrite.com", "meetup.com",
}

# TLDs associated with higher spam/phishing risk.
_RISKY_TLDS: set[str] = {
    "xyz", "top", "club", "work", "buzz", "loan",
    "click", "gdn", "men", "racing", "review",
}

# URL shorteners (neutral, but reduce trust slightly).
_SHORTENERS: set[str] = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "is.gd", "buff.ly", "rebrand.ly", "bl.ink",
}


class LinkChecker:
    """
    Evaluate a list of `LinkMetadata` and return `LinkTrust` objects.

    Usage
    -----
    >>> checker = LinkChecker()
    >>> trusts = checker.check(envelope.links)
    >>> for t in trusts:
    ...     print(t.url, t.trust_score, t.reasons)
    """

    def __init__(self, *, enable_http_probe: bool = False, timeout: float = 5.0):
        """
        Parameters
        ----------
        enable_http_probe : If ``True``, perform async HTTP HEAD requests to
                           verify link reachability.  Disabled by default to
                           keep hackathon runs fast.
        timeout           : Seconds to wait per HTTP probe.
        """
        self._probe = enable_http_probe
        self._timeout = timeout
        api_key = os.getenv("GROQ_API_KEY")
        self._llm_client = AsyncGroq(api_key=api_key) if api_key else None
        self._model_name = os.getenv("LLM_MODEL", "llama-4-scout")

    # ── public API ────────────────────────────────────────────────────

    def check(
        self, links: list[LinkMetadata], user_profile: Optional[UserProfile] = None
    ) -> list[LinkTrust]:
        """Synchronous wrapper - safe to call from non-async code."""
        return asyncio.run(self._check_all(links, user_profile))

    async def check_async(
        self, links: list[LinkMetadata], user_profile: Optional[UserProfile] = None
    ) -> list[LinkTrust]:
        """Async entry point (for use inside an existing event loop)."""
        return await self._check_all(links, user_profile)

    # ── internals ─────────────────────────────────────────────────────

    async def _check_all(
        self, links: list[LinkMetadata], user_profile: Optional[UserProfile] = None
    ) -> list[LinkTrust]:
        tasks = [self._evaluate(lnk, user_profile) for lnk in links]
        return await asyncio.gather(*tasks)

    async def _evaluate(
        self, link: LinkMetadata, user_profile: Optional[UserProfile] = None
    ) -> LinkTrust:
        url = link.url
        score = 5.0  # neutral baseline
        reasons: list[str] = []
        is_reachable = True
        site_analysis = None

        ext = tldextract.extract(url)
        registered = f"{ext.domain}.{ext.suffix}".lower()
        tld = ext.suffix.lower()

        # ── Rule 1: Trusted domain bonus
        if registered in _TRUSTED_DOMAINS or tld in ("edu", "gov"):
            score += 3.0
            reasons.append(f"Trusted domain: {registered}")

        # ── Rule 2: Risky TLD penalty
        if tld in _RISKY_TLDS:
            score -= 3.0
            reasons.append(f"Risky TLD: .{tld}")

        # ── Rule 3: URL shortener
        if registered in _SHORTENERS:
            score -= 1.0
            reasons.append("URL shortener (destination unknown)")

        # ── Rule 4: HTTPS presence
        parsed = urlparse(url)
        if parsed.scheme == "https":
            score += 1.0
            reasons.append("Uses HTTPS")
        else:
            score -= 1.5
            reasons.append("No HTTPS – connection not encrypted")

        # ── Rule 5: Suspicious patterns in URL path
        suspicious_patterns = [
            r"login", r"signin", r"verify", r"account",
            r"password", r"secure.*update", r"confirm.*identity",
        ]
        path_lower = (parsed.path + "?" + (parsed.query or "")).lower()
        for pat in suspicious_patterns:
            if re.search(pat, path_lower):
                score -= 1.5
                reasons.append(f"Suspicious keyword in URL: '{pat}'")
                break

        # ── Rule 6: Excessively long URL
        if len(url) > 200:
            score -= 0.5
            reasons.append("Unusually long URL")

        # ── Rule 7: IP-address host
        if re.match(r"\d{1,3}(\.\d{1,3}){3}", ext.domain):
            score -= 2.0
            reasons.append("Host is a raw IP address")

        # ── Optional HTTP probe and Site Analysis
        if self._probe:
            is_reachable = await self._http_probe(url)
            if not is_reachable:
                score -= 1.0
                reasons.append("HTTP probe failed – link may be dead")
            elif user_profile and self._llm_client:
                try:
                    site_analysis = await self._analyze_site(url, user_profile)
                    if site_analysis and site_analysis.match_status:
                        if site_analysis.match_status.met:
                            score += 2.0
                            reasons.append("Site requirements matched user profile")
                        else:
                            score -= 1.0
                            reasons.append("Site requirements did not match user profile")
                except Exception as exc:
                    reasons.append(f"Site analysis failed: {exc}")
        elif user_profile:
            reasons.append("Profile-aware site analysis skipped (HTTP probe disabled)")

        # Clamp to [1, 10]
        score = round(max(1.0, min(10.0, score)), 1)

        return LinkTrust(
            url=url,
            trust_score=score,
            reasons=reasons,
            is_reachable=is_reachable,
            site_analysis=site_analysis,
        )

    async def _http_probe(self, url: str) -> bool:
        """Send a HEAD request and return True if the server responds."""
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self._timeout,
            ) as client:
                resp = await client.head(url)
                return resp.status_code < 400
        except Exception:
            return False

    async def _analyze_site(
        self, url: str, user_profile: UserProfile
    ) -> Optional[SiteAnalysis]:
        """Fetch site HTML, extract text, and use LLM to compare against user profile."""
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=10.0
            ) as client:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    return None
                html = resp.text
        except Exception:
            return None

        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts, styles
        for ele in soup(["script", "style", "nav", "footer", "header"]):
            ele.extract()
        text = soup.get_text(separator=" ", strip=True)
        # truncate text to prevent token limits
        text = text[:8000]

        prompt = f'''
        You are an expert requirements analyst.
        Analyze the following text extracted from a webpage ({url}) and match it against the provided User Profile.
        
        USER PROFILE:
        {user_profile.model_dump_json()}
        
        WEBPAGE TEXT:
        {text}
        
        Extract the requirements from the webpage and deterministically compare them with the user profile.
        Output ONLY a JSON object exactly matching the schema below. Fill in all fields:
        {{
            "summary": "Brief 1-2 sentence summary of what this page is offering/talking about",
            "extracted_requirements": ["list of explicit requirements mentioned on site"],
            "match_status": {{
                "met": true,
                "met_requirements": ["requirements the user explicitly meets based on their profile"],
                "missing_requirements": ["requirements the user explicitly lacks based on their profile"]
            }}
        }}
        '''
        
        # Async Groq LLM call
        response = await self._llm_client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            return SiteAnalysis.model_validate(data)
        except Exception:
            return None
