import pytest

from app.providers.caixa import CaixaLotteryProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.last_url = None
        self.last_timeout = None

    def get(self, url, timeout, headers):
        self.last_url = url
        self.last_timeout = timeout
        return FakeResponse(self.payload)


@pytest.mark.parametrize(
    ("lottery", "contest", "numbers", "month"),
    [
        ("megasena", 3044, ["04", "15", "17", "40", "55", "58"], None),
        (
            "lotofacil",
            3762,
            [
                "01", "02", "03", "04", "05",
                "06", "09", "10", "13", "16",
                "18", "21", "22", "23", "25",
            ],
            None,
        ),
        ("quina", 7092, ["23", "30", "47", "70", "80"], None),
        (
            "diadesorte",
            1272,
            ["01", "02", "05", "11", "18", "20", "23"],
            "Maio",
        ),
    ],
)
def test_caixa_provider_normalizes_results(lottery, contest, numbers, month):
    payload = {
        "numero": contest,
        "dataApuracao": "14/08/2026",
        "listaDezenas": numbers,
        "numeroConcursoProximo": contest + 1,
        "dataProximoConcurso": "15/08/2026",
        "nomeTimeCoracaoMesSorte": month,
    }

    session = FakeSession(payload)

    provider = CaixaLotteryProvider(
        base_url="https://servicebus2.caixa.gov.br/portaldeloterias/api",
        timeout=15,
        session=session,
    )

    result = provider.latest(lottery)

    assert result["concurso"] == contest
    assert result["dezenas"] == numbers
    assert result["proximoConcurso"] == contest + 1
    assert result["mesSorte"] == month
    assert session.last_url.endswith(f"/{lottery}")
    assert session.last_timeout == 15
