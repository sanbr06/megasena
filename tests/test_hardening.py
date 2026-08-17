from app import create_app
from app.services.result_service import ResultService


class FakeProvider:
    source_name = "fake-provider"

    def latest(self, lottery):
        return {
            "concurso": 123,
            "data": "01/01/2026",
            "dezenas": ["01", "02", "03", "04", "05", "06"],
        }


def test_protected_endpoint_fails_closed_without_token(tmp_path):
    database = tmp_path / "missing-token.sqlite3"
    app = create_app({
        "TESTING": True,
        "API_TOKEN": "",
        "DATABASE_URL": f"sqlite:///{database}",
    })

    response = app.test_client().get("/api/stats/megasena")

    assert response.status_code == 503
    assert response.json["error"] == "auth_not_configured"


def test_repository_does_not_silently_limit_history(app):
    repository = app.extensions["result_repository"]

    for contest in range(1, 1002):
        repository.save_result(
            "megasena",
            contest,
            "01/01/2026",
            [1, 2, 3, 4, 5, 6],
            "test",
        )

    assert len(repository.list_results("megasena")) == 1001
    assert repository.count_results("megasena") == 1001


def test_result_service_uses_provider(app):
    repository = app.extensions["result_repository"]
    service = ResultService(repository, FakeProvider())

    data = service.update_from_api("megasena")

    assert data["concurso"] == 123
    saved = repository.list_results("megasena")
    assert len(saved) == 1
    assert saved[0]["contest"] == 123
    assert saved[0]["source"] == "fake-provider"
