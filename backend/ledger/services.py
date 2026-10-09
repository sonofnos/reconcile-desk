import uuid

from django.db import transaction

from .models import Account, LedgerEntry


class InsufficientFundsError(Exception):
    def __init__(self, account_id):
        self.account_id = account_id
        super().__init__(f"Account {account_id} has insufficient funds.")


def post(from_account_id, to_account_id, amount, type_, external_reference=None, allow_overdraft=False):
    """Move `amount` between two accounts as a balanced debit/credit pair.

    Both accounts are locked with SELECT ... FOR UPDATE in ascending id order
    (not from/to order), so two transfers sharing an account can't deadlock
    each other regardless of which side either call names as "from".
    """
    if amount <= 0:
        raise ValueError("Ledger amount must be positive.")

    transaction_id = uuid.uuid4()
    ids = sorted([from_account_id, to_account_id])

    with transaction.atomic():
        locked = {a.id: a for a in Account.objects.select_for_update().filter(id__in=ids).order_by("id")}

        from_account = locked.get(from_account_id)
        to_account = locked.get(to_account_id)
        if from_account is None or to_account is None:
            raise ValueError("One or both accounts do not exist.")

        if not allow_overdraft and from_account.balance < amount:
            raise InsufficientFundsError(from_account_id)

        from_account.balance -= amount
        to_account.balance += amount
        from_account.save(update_fields=["balance"])
        to_account.save(update_fields=["balance"])

        LedgerEntry.objects.create(
            transaction_id=transaction_id,
            account=from_account,
            direction="debit",
            amount=amount,
            balance_after=from_account.balance,
            type=type_,
            external_reference=external_reference,
        )
        LedgerEntry.objects.create(
            transaction_id=transaction_id,
            account=to_account,
            direction="credit",
            amount=amount,
            balance_after=to_account.balance,
            type=type_,
            external_reference=external_reference,
        )

    return transaction_id


def system_liquidity_account(currency):
    account, _ = Account.objects.get_or_create(
        name="System Liquidity", currency=currency, kind="system_liquidity"
    )
    return account


def deposit(account, amount, external_reference=None):
    system = system_liquidity_account(account.currency)
    return post(system.id, account.id, amount, "deposit", external_reference, allow_overdraft=True)
