import io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

# 4 transactions across 2 currencies and 2 months:
#   MDL May:  SALARY +1000, ORANGE -200
#   EUR May:  STRIPE +500
#   MDL June: RENT   -300
SUMMARY_CSV = b"""\
Nr,Data,Data valuta,Descriere,Referinta,Debit,Credit,Valuta,Sold
1,01.05.2026,01.05.2026,SALARY MDL,REF001,,1000.00,MDL,1000.00
2,02.05.2026,02.05.2026,ORANGE MDL,REF002,200.00,,MDL,800.00
3,03.05.2026,03.05.2026,STRIPE EUR,REF003,,500.00,EUR,500.00
4,01.06.2026,01.06.2026,RENT MDL,REF004,300.00,,MDL,500.00
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
        files={"file": ("statement.csv", io.BytesIO(SUMMARY_CSV), "text/csv")},
    ).json()


def _get_currency(body, code):
    return next(c for c in body["currencies"] if c["currency"] == code)


# --- Currency isolation ---

def test_currencies_are_separate(client):
    _upload(client)
    body = client.get("/summary").json()
    codes = {c["currency"] for c in body["currencies"]}
    assert codes == {"MDL", "EUR"}
    assert len(body["currencies"]) == 2


def test_mdl_never_mixed_with_eur(client):
    _upload(client)
    body = client.get("/summary").json()
    mdl = _get_currency(body, "MDL")
    eur = _get_currency(body, "EUR")
    # MDL income is 1000, EUR income is 500 — they must stay separate
    assert Decimal(mdl["income"]) != Decimal(eur["income"])
    assert Decimal(mdl["income"]) == Decimal("1000")
    assert Decimal(eur["income"]) == Decimal("500")


# --- Totals correctness ---

def test_mdl_totals(client):
    _upload(client)
    mdl = _get_currency(client.get("/summary").json(), "MDL")
    assert Decimal(mdl["income"]) == Decimal("1000")
    assert Decimal(mdl["spending"]) == Decimal("-500")
    assert Decimal(mdl["balance"]) == Decimal("500")


def test_eur_totals(client):
    _upload(client)
    eur = _get_currency(client.get("/summary").json(), "EUR")
    assert Decimal(eur["income"]) == Decimal("500")
    assert Decimal(eur["spending"]) == Decimal("0")
    assert Decimal(eur["balance"]) == Decimal("500")


# --- Filters ---

def test_filter_month_limits_spending(client):
    _upload(client)
    # May only: MDL spending should be -200, not -500
    mdl = _get_currency(client.get("/summary?month=2026-05").json(), "MDL")
    assert Decimal(mdl["spending"]) == Decimal("-200")
    assert Decimal(mdl["income"]) == Decimal("1000")


def test_filter_month_excludes_currency(client):
    _upload(client)
    # June only has MDL, EUR has no transactions that month
    body = client.get("/summary?month=2026-06").json()
    codes = {c["currency"] for c in body["currencies"]}
    assert codes == {"MDL"}
    assert "EUR" not in codes


def test_filter_search_isolates_currency(client):
    _upload(client)
    # Only STRIPE EUR matches "stripe"
    body = client.get("/summary?search=stripe").json()
    codes = {c["currency"] for c in body["currencies"]}
    assert codes == {"EUR"}


def test_filter_category(client):
    _upload(client)
    # Patch ORANGE to Telecom, then filter summary by category=Telecom
    tx_id = client.get("/transactions?search=orange").json()[0]["id"]
    client.patch(f"/transactions/{tx_id}", json={"category": "Telecom"})
    body = client.get("/summary?category=Telecom").json()
    assert len(body["currencies"]) == 1
    mdl = _get_currency(body, "MDL")
    assert Decimal(mdl["spending"]) == Decimal("-200")


# --- Per-category breakdown ---

def test_by_category_breakdown(client):
    _upload(client)
    tx_id = client.get("/transactions?search=orange").json()[0]["id"]
    client.patch(f"/transactions/{tx_id}", json={"category": "Telecom"})
    mdl = _get_currency(client.get("/summary").json(), "MDL")
    cats = {b["category"]: b for b in mdl["by_category"]}
    assert "Telecom" in cats
    assert Decimal(cats["Telecom"]["spending"]) == Decimal("-200")
    assert Decimal(cats["Telecom"]["income"]) == Decimal("0")


# --- Edge cases ---

def test_empty_returns_no_currencies(client):
    body = client.get("/summary").json()
    assert body == {"currencies": []}


def test_response_shape(client):
    _upload(client)
    body = client.get("/summary").json()
    assert "currencies" in body
    cur = body["currencies"][0]
    assert set(cur) >= {"currency", "income", "spending", "balance", "by_category"}
    breakdown = cur["by_category"][0]
    assert set(breakdown) >= {"category", "income", "spending", "balance"}
