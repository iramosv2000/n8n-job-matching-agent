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


def test_sources_lists_policies(client, monkeypatch):
    monkeypatch.delenv("MATCHER_ENABLED_SOURCES", raising=False)
    body = {s["name"]: s for s in client.get("/sources").json()}
    assert body["getonbrd"]["enabled"] is True
    assert body["getonbrd"]["fetched_by"] == "n8n"
    assert body["chiletrabajos"]["enabled"] is False
    assert body["chiletrabajos"]["external_llm_allowed"] is False


def test_fetch_guards(client, monkeypatch):
    monkeypatch.delenv("MATCHER_ENABLED_SOURCES", raising=False)
    payload = {"queries": ["plc"]}
    assert client.post("/sources/computrabajo/fetch", json=payload).status_code == 404
    assert client.post("/sources/getonbrd/fetch", json=payload).status_code == 400
    assert client.post("/sources/chiletrabajos/fetch", json=payload).status_code == 403


def test_fetch_enabled_source_and_normalize(client, monkeypatch):
    from chiletrabajos_site import transport

    import matcher.api
    from matcher.http import PoliteClient

    monkeypatch.setenv("MATCHER_ENABLED_SOURCES", "chiletrabajos, unknown")
    mock, _ = transport()
    monkeypatch.setattr(matcher.api, "make_client", lambda: PoliteClient(transport=mock, min_interval=0))
    fetched = client.post("/sources/chiletrabajos/fetch", json={"queries": ["plc"], "days": 60})
    assert fetched.status_code == 200
    items = fetched.json()["items"]
    assert {i["id"] for i in items} == {"101", "102"}
    normalized = client.post("/normalize", json={"source": "chiletrabajos", "items": items}).json()
    assert len(normalized["offers"]) == 2
    assert normalized["rejected"] == []


def test_fetch_enabled_runs_each_enabled_source(client, monkeypatch):
    from chiletrabajos_site import transport

    import matcher.api
    from matcher.http import PoliteClient

    monkeypatch.delenv("MATCHER_ENABLED_SOURCES", raising=False)
    assert client.post("/sources/fetch-enabled", json={"queries": ["plc"]}).json() == {"batches": []}

    monkeypatch.setenv("MATCHER_ENABLED_SOURCES", "chiletrabajos")
    mock, _ = transport()
    monkeypatch.setattr(matcher.api, "make_client", lambda: PoliteClient(transport=mock, min_interval=0))
    [batch] = client.post("/sources/fetch-enabled", json={"queries": ["plc"], "days": 60}).json()["batches"]
    assert batch["source"] == "chiletrabajos"
    assert len(batch["items"]) == 2
