def test_generation_isolated_by_lottery(client):
    headers = {"Authorization": "Bearer test-token"}

    mega = client.get("/api/generate/megasena", headers=headers)
    assert mega.status_code == 200
    assert len(mega.json["numbers"]) == 6
    assert all(1 <= n <= 60 for n in mega.json["numbers"])

    lotofacil = client.get("/api/generate/lotofacil", headers=headers)
    assert lotofacil.status_code == 200
    assert len(lotofacil.json["numbers"]) == 15
    assert all(1 <= n <= 25 for n in lotofacil.json["numbers"])
