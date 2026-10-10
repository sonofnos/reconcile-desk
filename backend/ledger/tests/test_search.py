import pytest
from rest_framework.test import APIClient

from ledger.models import Account
from ledger import services


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_search_filters_by_type(client):
    account = Account.objects.create(name="A", balance=0)
    services.deposit(account, 1000, external_reference="REF-1")
    services.deposit(account, 2000, external_reference="REF-2")

    response = client.get("/api/transactions/search/?type=deposit")

    assert response.status_code == 200
    assert response.data["page"] == 1
    assert all(r["type"] == "deposit" for r in response.data["results"])


@pytest.mark.django_db
def test_search_has_next_without_counting_the_full_set(client):
    # Each deposit() posts a debit (system) + credit (user) pair, both typed
    # 'deposit', so 30 calls produce exactly 60 matching entries: one full
    # page of 50 with more remaining, then a final page of 10 with none left.
    account = Account.objects.create(name="A", balance=0)
    for i in range(30):
        services.deposit(account, 100, external_reference=f"REF-{i}")

    first_page = client.get("/api/transactions/search/?type=deposit&page=1")
    second_page = client.get("/api/transactions/search/?type=deposit&page=2")

    assert len(first_page.data["results"]) == 50
    assert first_page.data["has_next"] is True
    assert len(second_page.data["results"]) == 10
    assert second_page.data["has_next"] is False
