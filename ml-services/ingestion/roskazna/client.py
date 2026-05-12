from __future__ import annotations

import logging
import tempfile
import warnings
from pathlib import Path

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry


LOGGER = logging.getLogger(__name__)
CUSTOM_CA_BUNDLE_FILENAME = "roskazna_ca_bundle.pem"
CUSTOM_CA_BUNDLE_PATH = Path(__file__).with_name("certs") / CUSTOM_CA_BUNDLE_FILENAME


class RoskaznaClientError(RuntimeError):
    pass


class RoskaznaClient:
    base_url = "https://roskazna.gov.ru"

    def __init__(self, timeout: float = 20.0, user_agent: str = "RU-Liquidity-Sentinel/1.0") -> None:
        self.timeout = timeout
        self.ca_bundle = self._build_ca_bundle()
        self._logged_insecure_fallback = False
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

    def _build_ca_bundle(self) -> str:
        if not CUSTOM_CA_BUNDLE_PATH.exists():
            return certifi.where()

        combined_bundle = Path(tempfile.gettempdir()) / CUSTOM_CA_BUNDLE_FILENAME
        certifi_bundle = Path(certifi.where()).read_text(encoding="utf-8")
        custom_bundle = CUSTOM_CA_BUNDLE_PATH.read_text(encoding="utf-8")
        combined_bundle.write_text(f"{certifi_bundle.rstrip()}\n{custom_bundle.lstrip()}", encoding="utf-8")
        return str(combined_bundle)

    def _request(self, url: str, *, binary: bool = False) -> tuple[bytes | str, bool]:
        used_insecure_fallback = False
        try:
            response = self.session.get(url, timeout=self.timeout, verify=self.ca_bundle)
        except requests.exceptions.SSLError:
            used_insecure_fallback = True
            if not self._logged_insecure_fallback:
                LOGGER.warning(
                    "Roskazna TLS verification failed with configured CA bundle; using temporary insecure fallback for this run"
                )
                self._logged_insecure_fallback = True
            warnings.simplefilter("ignore", InsecureRequestWarning)
            response = self.session.get(url, timeout=self.timeout, verify=False)
        except requests.RequestException as exc:
            raise RoskaznaClientError(f"request to Roskazna failed: {url}") from exc

        if response.status_code >= 400:
            raise RoskaznaClientError(f"Roskazna returned HTTP {response.status_code} for {url}")
        if binary:
            return response.content, used_insecure_fallback
        response.encoding = response.encoding or "utf-8"
        return response.text, used_insecure_fallback

    def get(self, url: str, *, binary: bool = False) -> bytes | str:
        payload, _ = self._request(url, binary=binary)
        return payload

    def get_with_fallback_meta(self, url: str, *, binary: bool = False) -> tuple[bytes | str, bool]:
        return self._request(url, binary=binary)
