import requests


class ProviderError(RuntimeError):
    pass


class CaixaLotteryProvider:
    source_name = "caixa-loterias"

    def __init__(self, base_url, timeout=15, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    @staticmethod
    def _clean_special_value(value):
        if not isinstance(value, str):
            return None

        value = value.replace("\x00", "").strip()
        return value or None

    def _fetch(self, url):
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "megasena-intelligence/0.1",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError("provider_request_failed") from exc

        return self._normalize(payload)

    def _normalize(self, payload):
        if not isinstance(payload, dict):
            raise ProviderError("provider_invalid_payload")

        try:
            contest = int(payload["numero"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("provider_invalid_contest") from exc

        numbers = payload.get("listaDezenas")
        if not isinstance(numbers, list):
            raise ProviderError("provider_invalid_numbers")

        return {
            "concurso": contest,
            "data": payload.get("dataApuracao"),
            "dezenas": numbers,
            "proximoConcurso": payload.get("numeroConcursoProximo"),
            "dataProximoConcurso": payload.get("dataProximoConcurso"),
            "mesSorte": self._clean_special_value(
                payload.get("nomeTimeCoracaoMesSorte")
            ),
        }

    def latest(self, lottery):
        return self._fetch(f"{self.base_url}/{lottery}")

    def by_contest(self, lottery, contest):
        try:
            contest = int(contest)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid_contest") from exc

        if contest <= 0:
            raise ValueError("invalid_contest")

        return self._fetch(f"{self.base_url}/{lottery}/{contest}")
