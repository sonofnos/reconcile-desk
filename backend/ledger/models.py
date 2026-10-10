import uuid

from django.db import models


class Account(models.Model):
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=10, default="NGN")
    kind = models.CharField(
        max_length=20,
        choices=[("user", "User"), ("system_liquidity", "System Liquidity")],
        default="user",
    )
    # Minor units (kobo), never a float.
    balance = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.currency})"


class LedgerEntry(models.Model):
    DIRECTION_CHOICES = [("debit", "Debit"), ("credit", "Credit")]
    TYPE_CHOICES = [
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("transfer", "Transfer"),
    ]

    transaction_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="entries")
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    amount = models.BigIntegerField()
    balance_after = models.BigIntegerField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    external_reference = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["account", "created_at"]),
            # Covers the cross-account transaction search endpoint: filter by
            # type, order by created_at. Added after measuring the query
            # without it under 2M rows, documented in README under "Scale, for real".
            models.Index(fields=["type", "-created_at"], name="ledger_entry_type_created_idx"),
        ]


class IdempotencyKey(models.Model):
    key = models.CharField(max_length=255, unique=True)
    request_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=20,
        choices=[("processing", "Processing"), ("completed", "Completed")],
        default="processing",
    )
    status_code = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StatementImport(models.Model):
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class StatementLine(models.Model):
    STATUS_CHOICES = [
        ("MATCHED", "Matched"),
        ("AMOUNT_MISMATCH", "Amount mismatch"),
        ("MISSING_IN_LEDGER", "Missing in ledger"),
    ]

    statement_import = models.ForeignKey(StatementImport, on_delete=models.CASCADE, related_name="lines")
    external_reference = models.CharField(max_length=255)
    date = models.DateField()
    amount = models.BigIntegerField()
    description = models.CharField(max_length=500, blank=True)
    matched_entry = models.ForeignKey(
        LedgerEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
