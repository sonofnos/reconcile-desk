import threading

import pytest
from django.db import connection
from django.test import TransactionTestCase

from ledger import services
from ledger.models import Account


class ConcurrentTransferTest(TransactionTestCase):
    """Fires real concurrent requests at a shared account, each from its own
    thread with its own DB connection, to prove select_for_update actually
    prevents overdraft rather than just asserting it worked once.
    """

    def test_only_one_of_many_concurrent_full_balance_spends_succeeds(self):
        spender = Account.objects.create(name="Spender", balance=100000)
        recipients = [Account.objects.create(name=f"R{i}", balance=0) for i in range(15)]

        results = []
        lock = threading.Lock()

        def attempt(recipient_id):
            try:
                services.post(spender.id, recipient_id, 100000, "transfer")
                with lock:
                    results.append("success")
            except services.InsufficientFundsError:
                with lock:
                    results.append("rejected")
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt, args=(r.id,)) for r in recipients]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        spender.refresh_from_db()
        assert results.count("success") == 1
        assert spender.balance == 0
