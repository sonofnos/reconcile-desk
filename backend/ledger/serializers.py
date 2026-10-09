from rest_framework import serializers

from .models import Account, LedgerEntry, StatementImport, StatementLine


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "name", "currency", "balance", "created_at"]


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ["id", "transaction_id", "direction", "amount", "balance_after", "type", "created_at"]


class StatementLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatementLine
        fields = ["id", "external_reference", "date", "amount", "description", "status"]


class StatementImportSerializer(serializers.ModelSerializer):
    lines = StatementLineSerializer(many=True, read_only=True)

    class Meta:
        model = StatementImport
        fields = ["id", "filename", "uploaded_at", "lines"]
