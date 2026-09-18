"""HTTP client for the Northwind payments API.

Every resource module goes through :class:`PaymentsClient`. The client owns
authentication, retries, idempotency and pagination so the resource wrappers
stay thin.
"""

import uuid

import requests

BASE_URL = "https://api.northwind-pay.example/v2"
DEFAULT_TIMEOUT = 10
MAX_PAGE_SIZE = 100

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class PaymentsClient:
    def __init__(self, api_key, base_url=BASE_URL, timeout=DEFAULT_TIMEOUT):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": "Bearer %s" % api_key})

    def _url(self, path):
        return "%s/%s" % (self.base_url.rstrip("/"), path.lstrip("/"))

    def request(self, method, path, params=None, json=None, idempotency_key=None, timeout=None):
        """Issue one request and return the decoded body."""
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        response = self.session.request(
            method,
            self._url(path),
            params=params,
            json=json,
            headers=headers,
            timeout=timeout or self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get(self, path, params=None, timeout=None):
        return self.request("GET", path, params=params, timeout=timeout)

    def post(self, path, json=None, idempotency_key=None, timeout=None):
        return self.request(
            "POST", path, json=json, idempotency_key=idempotency_key, timeout=timeout
        )

    def delete(self, path, timeout=None):
        return self.request("DELETE", path, timeout=timeout)

    def new_idempotency_key(self):
        return str(uuid.uuid4())

    def paginate(self, path, params=None, page_size=MAX_PAGE_SIZE):
        """Yield every item across every page of a list endpoint."""
        params = dict(params or {})
        params["limit"] = page_size
        cursor = None

        while True:
            if cursor:
                params["starting_after"] = cursor
            page = self.get(path, params=params)
            items = page.get("data", [])
            for item in items:
                yield item
            if not page.get("has_more"):
                return
            cursor = items[-1]["id"]
