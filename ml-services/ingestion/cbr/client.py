from __future__ import annotations

from datetime import date
import logging
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingestion.cbr.exceptions import CbrClientError


LOGGER = logging.getLogger(__name__)


class CbrClient:
    base_url = "https://www.cbr.ru"

    def __init__(self, timeout: float = 20.0, user_agent: str = "RU-Liquidity-Sentinel/1.0") -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    @staticmethod
    def _format_cbr_date(value: date) -> str:
        return value.strftime("%d.%m.%Y")

    def build_url(self, path: str, date_from: date, date_to: date, extra_params: dict[str, str] | None = None) -> str:
        params = {
            "UniDbQuery.From": self._format_cbr_date(date_from),
            "UniDbQuery.To": self._format_cbr_date(date_to),
            "UniDbQuery.Posted": "True",
        }
        if extra_params:
            params.update(extra_params)
        return f"{self.base_url}{path}?{urlencode(params)}"

    def get(self, path: str, date_from: date, date_to: date, extra_params: dict[str, str] | None = None) -> str:
        url = self.build_url(path, date_from, date_to, extra_params=extra_params)
        LOGGER.info("fetching CBR url=%s from=%s to=%s", url, date_from.isoformat(), date_to.isoformat())
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise CbrClientError(f"request to CBR failed: {url}") from exc

        if response.status_code >= 400:
            raise CbrClientError(f"CBR returned HTTP {response.status_code} for {url}")
        response.encoding = response.encoding or "utf-8"
        return response.text
