from matcher import __version__


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_normalize_returns_offers_and_rejections(client, job):
    bad = {"id": "x", "attributes": {"title": ""}}
    response = client.post(
        "/normalize", json={"source": "getonbrd", "items": [job, bad, job], "usd_clp": 950}
    )
    assert response.status_code == 200
    body = response.json()
    assert [o["offer_id"] for o in body["offers"]] == [f"getonbrd:{job['id']}"]
    assert [r["index"] for r in body["rejected"]] == [1, 2]
    assert "duplicate offer_id" in body["rejected"][1]["reason"]


def test_normalize_rejects_unknown_source(client):
    assert client.post("/normalize", json={"source": "linkedin", "items": []}).status_code == 422


def test_dedupe_endpoint(client):
    payload = {
        "candidates": [
            {"offer_id": "b:2", "title": "Ingeniero de Control", "company": "ACME", "region": "Maule"}
        ],
        "existing": [{"offer_id": "a:1", "title": "Ingeniero Control", "company": "acme", "region": "Maule"}],
    }
    response = client.post("/dedupe", json=payload)
    assert response.status_code == 200
    assert response.json()["links"][0]["duplicate_of"] == "a:1"


def test_openapi_documents_the_contract(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/normalize", "/dedupe"} <= set(paths)
