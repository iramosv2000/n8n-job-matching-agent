from datetime import date

import pytest

from matcher.sources.getonbrd import to_canonical


def test_maps_a_complete_item(job):
    offer = to_canonical(job, usd_clp=950.0)
    assert offer.offer_id == "getonbrd:ingeniero-a-de-automatizacion-andes-procesos-ficticia"
    assert offer.title == "Ingeniero/a de Automatización"
    assert offer.company == "Andes Procesos SpA"
    assert offer.location_raw == "Calama"
    assert offer.region == "Antofagasta"
    # 02:00 UTC on 16 Oct is still 15 Oct in Santiago (UTC-3): dates follow the local calendar.
    assert offer.published_at == date(2026, 10, 15)
    assert offer.structured.schedule == "Full time"
    assert offer.structured.seniority == "Semi Senior"
    assert offer.structured.salary_min_clp == 1_900_000
    assert offer.structured.salary_max_clp == 2_280_000
    assert offer.structured.salary_note == "USD 2000–2400 /mes"
    assert offer.structured.outside_chile is False
    assert offer.raw == job


def test_description_is_plain_text_with_contacts_redacted(job):
    offer = to_canonical(job, usd_clp=None)
    assert "<" not in offer.description
    assert "reclutamiento@example.com" not in offer.description
    assert "[email]" in offer.description
    assert offer.redactions == 1
    assert "Deseable: Experiencia con Modbus TCP" in offer.description
    assert "HMI & SCADA" in offer.description


def test_salary_without_exchange_rate_is_kept_as_note(job):
    offer = to_canonical(job, usd_clp=None)
    assert offer.structured.salary_min_clp is None
    assert offer.structured.salary_note == "USD 2000–2400 /mes"


def test_remote_offer_from_abroad(job):
    job["attributes"].update(
        remote_modality="fully_remote", countries=["Argentina"], location_cities={"data": []}
    )
    offer = to_canonical(job, usd_clp=None)
    assert offer.region == "Remoto"
    assert offer.location_raw == "Argentina"
    assert offer.structured.outside_chile is True


def test_remote_without_location(job):
    job["attributes"].update(remote_modality="remote_local", countries=[], location_cities={})
    offer = to_canonical(job, usd_clp=None)
    assert offer.location_raw == "Remoto"
    assert offer.structured.outside_chile is False


@pytest.mark.parametrize(("schedule", "contract"), [("Freelance", "freelance"), ("Internship", "practica")])
def test_contract_from_schedule(job, schedule, contract):
    job["attributes"]["modality"]["data"]["attributes"]["name"] = schedule
    assert to_canonical(job, usd_clp=None).structured.contract == contract


@pytest.mark.parametrize("field", ["id", "title", "public_url"])
def test_missing_mandatory_fields_raise(job, field):
    if field == "id":
        job.pop("id")
    elif field == "title":
        job["attributes"]["title"] = ""
    else:
        job["links"] = {}
    with pytest.raises(ValueError, match="missing"):
        to_canonical(job, usd_clp=None)


def test_tolerates_missing_optional_relations(job):
    for key in ("company", "seniority", "modality", "published_at", "min_salary", "max_salary"):
        job["attributes"].pop(key)
    job["attributes"]["company"] = {"data": None}
    offer = to_canonical(job, usd_clp=950.0)
    assert offer.company is None
    assert offer.published_at is None
    assert offer.structured.salary_note is None
