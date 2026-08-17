import requests


class ProviderError(RuntimeError):
    pass


class LotteryApiProvider:
    def __init__(self, base_url, timeout=15, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    @property
    def source_name(self):
        return self.base_url

    def latest(self, lottery):
        url = f"{self.base_url}/{lottery}/latest"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError("provider_request_failed") from exc

        if not isinstance(data, dict):
            raise ProviderError("provider_invalid_payload")

        return data
