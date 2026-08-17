from app.repositories.result_repository import ResultRepository
from app.services.result_service import ResultService


class FakeProvider:
    source_name = "caixa-loterias"

    def latest(self, lottery):
        return {
            "concurso": 1273,
            "data": "16/08/2026",
            "dezenas": ["01", "02", "03", "04", "05", "06", "07"],
            "proximoConcurso": 1274,
            "mesSorte": "Outubro",
        }


def test_dia_de_sorte_month_is_persisted(tmp_path):
    database = tmp_path / "results.sqlite3"

    repository = ResultRepository(f"sqlite:///{database}")
    repository.initialize()

    service = ResultService(repository, FakeProvider())
    service.update_from_api("diadesorte")

    result = repository.list_results("diadesorte")[0]

    assert result["contest"] == 1273
    assert result["metadata"]["mes_sorte"] == "Outubro"
