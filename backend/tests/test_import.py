import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

MINIMAL_CSV = b"""\
Nr,Data,Data valuta,Descriere,Referinta,Debit,Credit,Valuta,Sold
1,01.05.2026,01.05.2026,TEST INCOME,REF001,,500.00,MDL,500.00
2,02.05.2026,02.05.2026,TEST EXPENSE,REF002,200.00,,MDL,300.00
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


def _upload(client, csv_bytes: bytes):
    return client.post(
        "/import",
        files={"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")},
    )


def test_import_happy_path(client):
    resp = _upload(client, MINIMAL_CSV)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["skipped"] == 0
    assert body["ignored"] == 0
    assert len(body["transactions"]) == 2


def test_import_response_shape(client):
    resp = _upload(client, MINIMAL_CSV)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) >= {"imported", "skipped", "ignored", "transactions", "skipped_rows", "ignored_rows"}


def test_import_cross_import_dedup(client):
    _upload(client, MINIMAL_CSV)
    resp = _upload(client, MINIMAL_CSV)
    body = resp.json()
    assert body["imported"] == 0
    assert body["skipped"] == 2
    assert all(r["reason"] == "Duplicate transaction" for r in body["skipped_rows"])
