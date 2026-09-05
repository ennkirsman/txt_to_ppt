from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any

import requests


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "txt-to-ppt-educational-prototype/0.1 (GitHub: ennkirsman/txt_to_ppt)"


@dataclass
class CommonsImage:
    data: bytes
    mime_type: str
    credit: str
    source_url: str
    title: str


def _clean_html(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split())


def search_commons_image(query: str, timeout: int = 15) -> CommonsImage | None:
    if not query.strip():
        return None
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 8,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 1400,
    }
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(COMMONS_API, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    pages = (response.json().get("query") or {}).get("pages") or {}

    for page in pages.values():
        info_list = page.get("imageinfo") or []
        if not info_list:
            continue
        info = info_list[0]
        mime = info.get("mime") or ""
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        image_url = info.get("thumburl") or info.get("url")
        if not image_url:
            continue
        try:
            img = requests.get(image_url, headers=headers, timeout=timeout)
            img.raise_for_status()
        except requests.RequestException:
            continue

        meta: dict[str, Any] = info.get("extmetadata") or {}
        artist = _clean_html((meta.get("Artist") or {}).get("value", ""))
        license_short = _clean_html((meta.get("LicenseShortName") or {}).get("value", ""))
        credit_line = _clean_html((meta.get("Credit") or {}).get("value", ""))
        title = page.get("title", "Wikimedia Commons image")
        source_url = info.get("descriptionurl") or info.get("url") or image_url
        credit_parts = [p for p in [artist, license_short, credit_line] if p]
        credit = " · ".join(dict.fromkeys(credit_parts)) or "Wikimedia Commons"
        return CommonsImage(img.content, mime, credit, source_url, title)
    return None
