from app.providers.caixa import CaixaLotteryProvider
from app.services.backfill_service import BackfillService
from app.services.result_service import ResultService


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
        self.urls = []

    def get(self, url, timeout, headers):
        self.urls.append(url)
        return FakeResponse(self.payload)


def test_provider_fetches_specific_contest():
    session = FakeSession({
        "numero": 100,
        "dataApuracao": "01/01/2000",
        "listaDezenas": ["01", "02", "03", "04", "05", "06"],
    })

    provider = CaixaLotteryProvider(
        "https://servicebus2.caixa.gov.br/portaldeloterias/api",
        session=session,
    )

    result = provider.by_contest("megasena", 100)

    assert result["concurso"] == 100
    assert session.urls[-1].endswith("/megasena/100")


class FakeProvider:
    source_name = "caixa-loterias"

    def __init__(self):
        self.requested = []

    def latest(self, lottery):
        return {
            "concurso": 3,
            "data": "03/01/2000",
            "dezenas": ["01", "02", "03", "04", "05", "06"],
            "mesSorte": None,
        }

    def by_contest(self, lottery, contest):
        self.requested.append(contest)
        return {
            "concurso": contest,
            "data": "01/01/2000",
            "dezenas": ["01", "02", "03", "04", "05", "06"],
            "mesSorte": None,
        }


def test_result_service_updates_specific_contest(app):
    repository = app.extensions["result_repository"]
    provider = FakeProvider()
    service = ResultService(repository, provider)

    service.update_contest("megasena", 2)

    saved = repository.list_results("megasena")
    assert saved[0]["contest"] == 2
    assert provider.requested == [2]


def test_backfill_is_idempotent_and_skips_existing(app):
    repository = app.extensions["result_repository"]
    provider = FakeProvider()
    result_service = ResultService(repository, provider)

    repository.save_result(
        "megasena",
        1,
        "01/01/2000",
        [1, 2, 3, 4, 5, 6],
        "test",
    )

    service = BackfillService(
        repository,
        result_service,
        provider,
        sleep_fn=lambda _: None,
    )

    summary = service.backfill(
        "megasena",
        start=1,
        end=3,
        delay=0,
    )

    assert provider.requested == [2, 3]
    assert summary["inserted"] == 2
    assert summary["skipped"] == 1
    assert repository.count_results("megasena") == 3
