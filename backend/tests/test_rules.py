import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


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


def test_list_rules_empty(client):
    resp = client.get("/rules")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_rule(client):
    resp = client.post("/rules", json={"pattern": "orange", "category": "Telecom", "priority": 5})
    assert resp.status_code == 201
    body = resp.json()
    assert body["pattern"] == "orange"
    assert body["category"] == "Telecom"
    assert body["priority"] == 5
    assert "id" in body


def test_create_rule_default_priority(client):
    resp = client.post("/rules", json={"pattern": "test", "category": "Other"})
    assert resp.status_code == 201
    assert resp.json()["priority"] == 0


def test_list_rules_ordered_by_priority_desc(client):
    client.post("/rules", json={"pattern": "low", "category": "Low", "priority": 1})
    client.post("/rules", json={"pattern": "high", "category": "High", "priority": 10})
    rules = client.get("/rules").json()
    assert rules[0]["priority"] >= rules[-1]["priority"]


def test_update_rule(client):
    rule_id = client.post("/rules", json={"pattern": "old", "category": "OldCat"}).json()["id"]
    resp = client.put(f"/rules/{rule_id}", json={"pattern": "new", "category": "NewCat", "priority": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pattern"] == "new"
    assert body["category"] == "NewCat"
    assert body["priority"] == 3


def test_update_rule_not_found(client):
    resp = client.put("/rules/9999", json={"pattern": "x", "category": "y", "priority": 0})
    assert resp.status_code == 404


def test_delete_rule(client):
    rule_id = client.post("/rules", json={"pattern": "to_delete", "category": "Cat"}).json()["id"]
    assert client.delete(f"/rules/{rule_id}").status_code == 204
    remaining = client.get("/rules").json()
    assert all(r["id"] != rule_id for r in remaining)


def test_delete_rule_not_found(client):
    resp = client.delete("/rules/9999")
    assert resp.status_code == 404
