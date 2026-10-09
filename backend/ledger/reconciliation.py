import csv
import io
from datetime import datetime

from .models import LedgerEntry, StatementImport, StatementLine


def import_statement(filename, csv_content):
    """Parse a bank statement CSV (columns: reference,date,amount,description)
    and classify each line against the ledger by external_reference.

    amount is in major units in the CSV (e.g. "1500.00"), stored as minor
    units like everything else in the ledger.
    """
    statement_import = StatementImport.objects.create(filename=filename)

    reader = csv.DictReader(io.StringIO(csv_content))
    lines = []
    for row in reader:
        reference = row["reference"].strip()
        amount_minor = round(float(row["amount"]) * 100)
        date = datetime.strptime(row["date"].strip(), "%Y-%m-%d").date()
        description = row.get("description", "").strip()

        matching_entry = (
            LedgerEntry.objects.filter(external_reference=reference, direction="credit").first()
        )

        if matching_entry is None:
            status = "MISSING_IN_LEDGER"
        elif matching_entry.amount != amount_minor:
            status = "AMOUNT_MISMATCH"
        else:
            status = "MATCHED"

        lines.append(
            StatementLine(
                statement_import=statement_import,
                external_reference=reference,
                date=date,
                amount=amount_minor,
                description=description,
                matched_entry=matching_entry,
                status=status,
            )
        )

    StatementLine.objects.bulk_create(lines)
    return statement_import
