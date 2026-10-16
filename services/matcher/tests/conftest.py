import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from matcher.api import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def job() -> dict:
    data = json.loads((FIXTURES / "getonbrd_job.json").read_text(encoding="utf-8"))
    data.pop("_note")
    return copy.deepcopy(data)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
