import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

SAMPLE_CSV = b"""\
Nr,Data,Data valuta,Descriere,Referinta,Debit,Credit,Valuta,Sold
1,01.05.2026,01.05.2026,ORANGE MOLDOVA SA,REF001,,500.00,MDL,500.00
2,02.05.2026,02.05.2026,SALARY PAYMENT,REF002,200.00,,MDL,300.00
"""


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _upload(client):
    return client.post(
        "/import",
        files={"file": ("statement.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    ).json()


# --- GET /transactions ---

def test_list_empty(client):
    resp = client.get("/transactions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_all(client):
    _upload(client)
    resp = client.get("/transactions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_filter_by_category(client):
    tx_id = _upload(client)["transactions"][0]["id"]
    client.patch(f"/transactions/{tx_id}", json={"category": "Telecom"})
    results = client.get("/transactions?category=Telecom").json()
    assert len(results) == 1
    assert results[0]["category"] == "Telecom"


def test_filter_by_month_match(client):
    _upload(client)
    results = client.get("/transactions?month=2026-05").json()
    assert len(results) == 2


def test_filter_by_month_no_match(client):
    _upload(client)
    results = client.get("/transactions?month=2026-06").json()
    assert results == []


def test_filter_by_search_case_insensitive(client):
    _upload(client)
    results = client.get("/transactions?search=orange").json()
    assert len(results) == 1
    assert "ORANGE" in results[0]["description"]


def test_filter_combined(client):
    _upload(client)
    results = client.get("/transactions?month=2026-05&search=salary").json()
    assert len(results) == 1
    assert "SALARY" in results[0]["description"]


# --- PATCH /transactions/{id} ---

def test_patch_category(client):
    tx_id = _upload(client)["transactions"][0]["id"]
    resp = client.patch(f"/transactions/{tx_id}", json={"category": "Telecom"})
    assert resp.status_code == 200
    assert resp.json()["category"] == "Telecom"
    assert resp.json()["id"] == tx_id


def test_patch_not_found(client):
    resp = client.patch("/transactions/9999", json={"category": "X"})
    assert resp.status_code == 404


def test_patch_save_as_rule_creates_rule(client):
    tx_id = _upload(client)["transactions"][0]["id"]
    client.patch(
        f"/transactions/{tx_id}",
        json={"category": "Telecom", "save_as_rule": True, "pattern": "orange"},
    )
    rules = client.get("/rules").json()
    assert any(r["pattern"] == "orange" and r["category"] == "Telecom" for r in rules)


def test_patch_save_as_rule_requires_pattern(client):
    tx_id = _upload(client)["transactions"][0]["id"]
    resp = client.patch(
        f"/transactions/{tx_id}",
        json={"category": "Telecom", "save_as_rule": True},
    )
    assert resp.status_code == 422


def test_patch_without_save_as_rule_no_rule_created(client):
    tx_id = _upload(client)["transactions"][0]["id"]
    client.patch(f"/transactions/{tx_id}", json={"category": "Telecom"})
    assert client.get("/rules").json() == []
