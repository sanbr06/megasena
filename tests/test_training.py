def test_training_isolated_by_lottery(client, app):
    repository = app.extensions["result_service"].repository

    repository.save_result(
        "megasena", 1, "01/01/2026", [1, 2, 3, 4, 5, 6], "test"
    )
    repository.save_result(
        "lotofacil", 1, "01/01/2026", list(range(1, 16)), "test"
    )

    headers = {"Authorization": "Bearer test-token"}

    mega = client.post("/api/train/megasena", headers=headers)
    lotofacil = client.post("/api/train/lotofacil", headers=headers)

    assert mega.status_code == 200
    assert lotofacil.status_code == 200
    assert mega.json["lottery"] == "megasena"
    assert lotofacil.json["lottery"] == "lotofacil"
    assert mega.json["draws_used"] == 1
    assert lotofacil.json["draws_used"] == 1
