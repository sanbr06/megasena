import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    database = tmp_path / "test.sqlite3"
    return create_app({
        "TESTING": True,
        "API_TOKEN": "test-token",
        "DATABASE_URL": f"sqlite:///{database}",
    })


@pytest.fixture()
def client(app):
    return app.test_client()
