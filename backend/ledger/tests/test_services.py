import pytest

from ledger import services
from ledger.models import Account, LedgerEntry


@pytest.mark.django_db
def test_post_moves_balance_as_balanced_debit_credit_pair():
    sender = Account.objects.create(name="Sender", balance=500000)
    recipient = Account.objects.create(name="Recipient", balance=0)

    tx_id = services.post(sender.id, recipient.id, 150000, "transfer")

    sender.refresh_from_db()
    recipient.refresh_from_db()
    assert sender.balance == 350000
    assert recipient.balance == 150000

    entries = LedgerEntry.objects.filter(transaction_id=tx_id)
    assert entries.count() == 2
    total = sum(e.amount if e.direction == "credit" else -e.amount for e in entries)
    assert total == 0


@pytest.mark.django_db
def test_post_rejects_insufficient_funds_and_moves_nothing():
    sender = Account.objects.create(name="Poor", balance=0)
    recipient = Account.objects.create(name="Rich", balance=0)

    with pytest.raises(services.InsufficientFundsError):
        services.post(sender.id, recipient.id, 1, "transfer")

    sender.refresh_from_db()
    assert sender.balance == 0


@pytest.mark.django_db
def test_deposit_credits_from_system_liquidity_account():
    account = Account.objects.create(name="User", currency="NGN", balance=0)

    services.deposit(account, 250000)

    account.refresh_from_db()
    assert account.balance == 250000
    system = services.system_liquidity_account("NGN")
    system.refresh_from_db()
    assert system.balance == -250000
