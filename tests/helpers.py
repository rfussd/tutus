import json


class MockResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    @property
    def ok(self):
        return self.status_code < 400

    @property
    def text(self):
        return json.dumps(self._json)

    @property
    def headers(self):
        return {"content-type": "application/json"}

    def __getattr__(self, name):
        if name in ("iter_lines", "iter_content", "raw"):
            return lambda *a, **kw: iter([])
        raise AttributeError(name)
