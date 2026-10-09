from rest_framework.response import Response
from rest_framework.views import APIView

from . import reconciliation, services
from .models import Account, StatementImport
from .serializers import AccountSerializer, StatementImportSerializer
from .idempotency import idempotent


class AccountListCreateView(APIView):
    def get(self, request):
        return Response(AccountSerializer(Account.objects.all().order_by("id"), many=True).data)

    def post(self, request):
        serializer = AccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)


class TransferView(APIView):
    @idempotent
    def post(self, request):
        from_id = request.data.get("from_account")
        to_id = request.data.get("to_account")
        amount = request.data.get("amount")
        reference = request.data.get("reference")

        try:
            transaction_id = services.post(from_id, to_id, amount, "transfer", reference)
        except services.InsufficientFundsError:
            return Response({"message": "Insufficient funds."}, status=422)
        except ValueError as e:
            return Response({"message": str(e)}, status=400)

        from_account = Account.objects.get(id=from_id)
        return Response({"transaction_id": str(transaction_id), "balance": from_account.balance})


class DepositView(APIView):
    @idempotent
    def post(self, request):
        account_id = request.data.get("account")
        amount = request.data.get("amount")
        reference = request.data.get("reference")

        account = Account.objects.get(id=account_id)
        transaction_id = services.deposit(account, amount, reference)
        account.refresh_from_db()
        return Response({"transaction_id": str(transaction_id), "balance": account.balance})


class StatementImportView(APIView):
    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"message": "A 'file' upload is required."}, status=400)

        content = file.read().decode("utf-8")
        statement_import = reconciliation.import_statement(file.name, content)
        return Response(StatementImportSerializer(statement_import).data, status=201)

    def get(self, request):
        imports = StatementImport.objects.all().order_by("-uploaded_at")
        return Response(StatementImportSerializer(imports, many=True).data)
