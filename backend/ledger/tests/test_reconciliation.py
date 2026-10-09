import pytest

from ledger import services
from ledger.models import Account, StatementLine


@pytest.mark.django_db
def test_matched_mismatched_and_missing_lines_are_classified_correctly():
    account = Account.objects.create(name="Merchant", balance=0)
    services.deposit(account, 500000, external_reference="TXN-001")

    csv_content = (
        "reference,date,amount,description\n"
        "TXN-001,2026-10-09,5000.00,Matches the ledger exactly\n"
        "TXN-001-WRONG-AMOUNT,2026-10-09,10.00,No ledger entry at all\n"
    )
    # Second line's reference intentionally doesn't exist in the ledger.

    from ledger.reconciliation import import_statement

    statement_import = import_statement("test.csv", csv_content)
    lines = {line.external_reference: line.status for line in statement_import.lines.all()}

    assert lines["TXN-001"] == "MATCHED"
    assert lines["TXN-001-WRONG-AMOUNT"] == "MISSING_IN_LEDGER"


@pytest.mark.django_db
def test_amount_mismatch_is_detected():
    account = Account.objects.create(name="Merchant", balance=0)
    services.deposit(account, 500000, external_reference="TXN-002")

    from ledger.reconciliation import import_statement

    csv_content = "reference,date,amount,description\nTXN-002,2026-10-09,49.99,Short by a cent times 100\n"
    statement_import = import_statement("test.csv", csv_content)

    line = statement_import.lines.first()
    assert line.status == "AMOUNT_MISMATCH"
