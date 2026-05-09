from __future__ import annotations

import logging
import warnings

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry


LOGGER = logging.getLogger(__name__)


class RoskaznaClientError(RuntimeError):
    pass


class RoskaznaClient:
    base_url = "https://roskazna.gov.ru"

    def __init__(self, timeout: float = 20.0, user_agent: str = "RU-Liquidity-Sentinel/1.0") -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Language": "ru,en;q=0.9",
            }
        )
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

    def get(self, url: str, *, binary: bool = False) -> bytes | str:
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.exceptions.SSLError:
            LOGGER.warning("Roskazna TLS verification failed for %s, retrying without verification", url)
            warnings.simplefilter("ignore", InsecureRequestWarning)
            response = self.session.get(url, timeout=self.timeout, verify=False)
        except requests.RequestException as exc:
            raise RoskaznaClientError(f"request to Roskazna failed: {url}") from exc

        if response.status_code >= 400:
            raise RoskaznaClientError(f"Roskazna returned HTTP {response.status_code} for {url}")
        if binary:
            return response.content
        response.encoding = response.encoding or "utf-8"
        return response.text
