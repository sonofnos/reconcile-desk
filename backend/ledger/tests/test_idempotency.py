import json

import pytest
from rest_framework.test import APIClient

from ledger.models import Account


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_replaying_same_key_and_body_does_not_double_process(client):
    sender = Account.objects.create(name="A", balance=100000)
    recipient = Account.objects.create(name="B", balance=0)

    payload = {"from_account": sender.id, "to_account": recipient.id, "amount": 50000}
    headers = {"HTTP_IDEMPOTENCY_KEY": "same-key"}

    first = client.post("/api/transfers/", data=json.dumps(payload), content_type="application/json", **headers)
    second = client.post("/api/transfers/", data=json.dumps(payload), content_type="application/json", **headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.data["transaction_id"] == second.data["transaction_id"]

    sender.refresh_from_db()
    assert sender.balance == 50000  # moved once, not twice


@pytest.mark.django_db
def test_reusing_key_with_different_body_is_rejected(client):
    sender = Account.objects.create(name="A", balance=100000)
    recipient = Account.objects.create(name="B", balance=0)
    headers = {"HTTP_IDEMPOTENCY_KEY": "reused-key"}

    client.post(
        "/api/transfers/",
        data=json.dumps({"from_account": sender.id, "to_account": recipient.id, "amount": 1000}),
        content_type="application/json",
        **headers,
    )
    response = client.post(
        "/api/transfers/",
        data=json.dumps({"from_account": sender.id, "to_account": recipient.id, "amount": 2000}),
        content_type="application/json",
        **headers,
    )

    assert response.status_code == 409


@pytest.mark.django_db
def test_missing_idempotency_key_is_rejected(client):
    sender = Account.objects.create(name="A", balance=100000)
    recipient = Account.objects.create(name="B", balance=0)

    response = client.post(
        "/api/transfers/",
        data=json.dumps({"from_account": sender.id, "to_account": recipient.id, "amount": 1000}),
        content_type="application/json",
    )

    assert response.status_code == 400
