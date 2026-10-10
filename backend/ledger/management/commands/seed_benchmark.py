from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Seeds a large synthetic dataset for load testing and EXPLAIN ANALYZE comparisons."

    def add_arguments(self, parser):
        parser.add_argument("--accounts", type=int, default=5000)
        parser.add_argument("--entries", type=int, default=2_000_000)

    def handle(self, *args, **options):
        accounts = options["accounts"]
        entries = options["entries"]

        with connection.cursor() as cursor:
            self.stdout.write(f"Seeding {accounts} accounts...")
            cursor.execute(
                """
                INSERT INTO ledger_account (name, currency, kind, balance, created_at)
                SELECT
                    'Load Test Account ' || n,
                    'NGN',
                    'user',
                    0,
                    now() - (random() * interval '730 days')
                FROM generate_series(1, %s) AS n
                """,
                [accounts],
            )

            cursor.execute("SELECT min(id) FROM ledger_account")
            (min_account_id,) = cursor.fetchone()

            self.stdout.write(f"Seeding {entries} ledger entries (this is the slow part)...")
            # Single set-based INSERT ... SELECT, not a Python loop building
            # 2 million ORM objects: that would spend most of its time in
            # object construction and round-trips, not the database.
            # Picking a random account via an ORDER BY random() subquery per
            # row would be O(accounts log accounts) per row; since ids are a
            # known contiguous range from this seed run, a direct offset into
            # that range is O(1) per row instead.
            cursor.execute(
                """
                INSERT INTO ledger_ledgerentry
                    (transaction_id, account_id, direction, amount, balance_after, type, external_reference, created_at)
                SELECT
                    gen_random_uuid(),
                    %s + floor(random() * %s)::int,
                    (ARRAY['debit', 'credit'])[floor(random() * 2 + 1)],
                    (floor(random() * 10000000) + 100)::bigint,
                    (floor(random() * 100000000))::bigint,
                    (ARRAY['deposit', 'withdrawal', 'transfer'])[floor(random() * 3 + 1)],
                    'LOAD-' || n,
                    now() - (random() * interval '730 days')
                FROM generate_series(1, %s) AS n
                """,
                [min_account_id, accounts, entries],
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {accounts} accounts and {entries} ledger entries."))
