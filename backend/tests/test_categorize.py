import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models.rule import CategoryRule
from app.services.category import categorize


def _make_rule(pattern, category, priority=0, rule_id=1):
    r = CategoryRule()
    r.id = rule_id
    r.pattern = pattern
    r.category = category
    r.priority = priority
    return r


def test_categorize_case_insensitive():
    assert categorize("ORANGE MOLDOVA SA", [_make_rule("orange", "Telecom")]) == "Telecom"


def test_categorize_priority_wins():
    rules = [
        _make_rule("test", "Low", priority=0, rule_id=1),
        _make_rule("test", "High", priority=10, rule_id=2),
    ]
    assert categorize("TEST PAYMENT", rules) == "High"


def test_categorize_no_match():
    assert categorize("SALARY PAYMENT", [_make_rule("orange", "Telecom")]) == "Uncategorized"


def test_categorize_empty_rules():
    assert categorize("ANYTHING", []) == "Uncategorized"


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


CATEGORIZE_CSV = b"""\
Nr,Data,Data valuta,Descriere,Referinta,Debit,Credit,Valuta,Sold
1,01.05.2026,01.05.2026,ORANGE MOLDOVA SA,REF001,,500.00,MDL,500.00
2,02.05.2026,02.05.2026,SALARY PAYMENT,REF002,200.00,,MDL,300.00
"""


def _upload(client, csv_bytes: bytes):
    return client.post(
        "/import",
        files={"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")},
    )


def test_apply_rules_updates_categories(client):
    _upload(client, CATEGORIZE_CSV)
    client.post("/rules", json={"pattern": "orange", "category": "Telecom", "priority": 5})
    resp = client.post("/rules/apply")
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1


def test_apply_rules_no_rules_no_update(client):
    _upload(client, CATEGORIZE_CSV)
    resp = client.post("/rules/apply")
    assert resp.status_code == 200
    assert resp.json()["updated"] == 0


def test_import_applies_existing_rules(client):
    client.post("/rules", json={"pattern": "orange", "category": "Telecom", "priority": 5})
    result = _upload(client, CATEGORIZE_CSV).json()
    orange_tx = next(t for t in result["transactions"] if "ORANGE" in t["description"])
    assert orange_tx["category"] == "Telecom"
