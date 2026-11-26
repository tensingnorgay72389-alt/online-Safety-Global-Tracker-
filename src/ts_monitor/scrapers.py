"""Official newsroom, media-release and leadership-page scrapers for the regulator map."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

NEWS_PATH_HINTS = (
    "news", "newsroom", "media-release", "media-releases", "press-release",
    "press-releases", "press/", "statement", "statements", "/noticias",
    "berita", "consultation", "consultations", "annonce", "announcements",
    "media/", "news-and", "news_and", "updates",
)

_DATE_ATTR = re.compile(r"^\d{4}-\d{2}-\d{2}")
_DATE_TEXT = re.compile(
    r"\b(\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}\.\d{1,2}\.20\d{2}"
    r"|20\d{2}-\d{2}-\d{2})\b",
    re.I,
)
_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04", "may": "05", "june": "06",
    "july": "07", "august": "08", "september": "09", "october": "10", "november": "11", "december": "12",
}


def _absolute(url: str, base_url: str) -> str | None:
    href = (url or "").strip()
    if not href or href.startswith("#") or href.lower().startswith("javascript:"):
        return None
    if href.startswith("//"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}:{href}"
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(base_url, href)


def _looks_like_article(url: str, text: str) -> bool:
    path = urlparse(url).path.lower()
    blob = f"{path} {text.lower()}"
    if any(hint in path or hint in blob for hint in NEWS_PATH_HINTS):
        return True
    # A reasonably specific path with meaningful anchor text.
    parts = [p for p in path.split("/") if p]
    return bool(text) and len(text) > 20 and len(parts) >= 2


def _normalise_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if _DATE_ATTR.match(value):
        return value[:10]
    match = _DATE_TEXT.search(value)
    if not match:
        return None
    token = match.group(0)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", token):
        return token
    parts = token.replace(",", "").split()
    if len(parts) == 3 and parts[1].lower() in _MONTHS:
        day = parts[0].zfill(2)
        return f"{parts[2]}-{_MONTHS[parts[1].lower()]}-{day}"
    dotted = re.match(r"^(\d{1,2})\.(\d{1,2})\.(20\d{2})$", token)
    if dotted:
        return f"{dotted.group(3)}-{dotted.group(2).zfill(2)}-{dotted.group(1).zfill(2)}"
    return None


def parse_newsroom_html(html: str, base_url: str, limit: int = 40) -> list[dict]:
    """Extract article-like items from an official newsroom or media-release index."""
    soup = BeautifulSoup(html, "html.parser")
    found: list[dict] = []
    seen: set[str] = set()

    def add(url: str | None, title: str, date_value: str | None) -> None:
        if not url or url in seen or url.rstrip("/") == base_url.rstrip("/"):
            return
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 8:
            return
        if not _looks_like_article(url, title):
            return
        seen.add(url)
        found.append({"headline": title, "url": url, "published_date": _normalise_date(date_value)})

    for article in soup.find_all(["article", "li", "div"]):
        link = article.find("a", href=True)
        if not link:
            continue
        url = _absolute(link["href"], base_url)
        title = link.get_text(" ", strip=True) or (article.find(["h2", "h3", "h4"]).get_text(" ", strip=True) if article.find(["h2", "h3", "h4"]) else "")
        time_tag = article.find("time")
        date_value = None
        if time_tag:
            date_value = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)
        if not date_value:
            match = _DATE_TEXT.search(article.get_text(" ", strip=True)[:300])
            date_value = match.group(0) if match else None
        add(url, title, date_value)
        if len(found) >= limit:
            return found

    # Fallback: any remaining news-like links.
    if len(found) < 3:
        for link in soup.find_all("a", href=True):
            url = _absolute(link["href"], base_url)
            add(url, link.get_text(" ", strip=True), None)
            if len(found) >= limit:
                break
    return found[:limit]


def extract_named_officials(html: str) -> list[dict]:
    """
    Conservative helper for tests and review.

    This does not invent names. It only returns explicit title-like heading pairs
    when a heading contains both a person-like name and a role word. If the page
    does not name an official, the list is empty.
    """
    soup = BeautifulSoup(html, "html.parser")
    role_words = re.compile(
        r"\b(minister|secretary of state|commissioner|chair(?:man|woman)?|director-general|"
        r"director|presidente|présidente|chief executive|spokesperson|press officer)\b",
        re.I,
    )
    found: list[dict] = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True))
        if not text or not role_words.search(text):
            continue
        # Require at least two capitalised words to treat the line as naming a person.
        names = re.findall(r"\b[A-Z][A-Za-zÀ-ÿ'\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ'\-]+){1,4}\b", text)
        if not names:
            continue
        found.append({"text": text, "name_candidates": names})
    return found
