from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass(slots=True)
class CBRConfirmation:
    confirmed: bool
    confirmation_url: str | None
    matched_title: str | None
    search_url: str
    matches: list[dict[str, Any]]


class CBRPressReleaseChecker:
    def __init__(self, search_url: str, timeout_seconds: int = 30, user_agent: str | None = None) -> None:
        self.search_url = search_url
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent or "Mozilla/5.0"})

    @retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
    def _get(self, params: dict[str, str]) -> requests.Response:
        response = self.session.get(self.search_url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response

    def confirm(self, auction_date: date, ofz_issue: str) -> CBRConfirmation:
        params = {"text": f"ОФЗ {ofz_issue}", "CategoryIds[0]": "news", "CategoryIds[1]": "press"}
        response = self._get(params)
        soup = BeautifulSoup(response.text, "lxml")
        matches: list[dict[str, Any]] = []
        date_fragments = {
            auction_date.strftime("%d.%m.%Y"),
            auction_date.strftime("%d.%m.%y"),
            f"{auction_date.day}",
        }
        for link in soup.select(".results .title a"):
            href = link.get("href", "")
            title = link.get_text(" ", strip=True)
            card = link.find_parent(class_="search-result") or link.parent.parent
            snippet = card.get_text(" ", strip=True) if card else title
            url = requests.compat.urljoin(self.search_url, href)
            match = {
                "issue": ofz_issue,
                "auction_date": auction_date.isoformat(),
                "title": title,
                "url": url,
                "snippet": snippet,
            }
            matches.append(match)
            if href.startswith("/press/pr/") and ofz_issue in title and any(part in snippet for part in date_fragments):
                return CBRConfirmation(True, url, title, response.url, matches)
        return CBRConfirmation(False, None, None, response.url, matches)
