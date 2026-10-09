import hashlib
import json
from functools import wraps

from django.db import IntegrityError, transaction
from rest_framework.response import Response

from .models import IdempotencyKey


def idempotent(view_func):
    """Requires an Idempotency-Key header on the wrapped DRF view method.

    Same key + same body replays the cached response. Same key + different
    body is a 409. A concurrent duplicate of the same key while the first
    request is still being processed is also a 409 (the unique constraint on
    `key`, not a check-then-act race, is what actually prevents two requests
    from both proceeding).
    """

    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key")
        if not key:
            return Response({"message": "Idempotency-Key header is required."}, status=400)

        request_hash = hashlib.sha256(request.body or b"").hexdigest()

        try:
            with transaction.atomic():
                record = IdempotencyKey.objects.create(key=key, request_hash=request_hash)
        except IntegrityError:
            record = IdempotencyKey.objects.select_for_update().get(key=key)
            with transaction.atomic():
                record.refresh_from_db()
                if record.request_hash != request_hash:
                    return Response(
                        {"message": "Idempotency-Key was already used with a different request payload."},
                        status=409,
                    )
                if record.status == "processing":
                    return Response({"message": "This request is already being processed."}, status=409)
                return Response(record.response_body, status=record.status_code, headers={"X-Idempotent-Replay": "true"})

        response = view_func(self, request, *args, **kwargs)

        record.status = "completed"
        record.status_code = response.status_code
        record.response_body = response.data if hasattr(response, "data") else None
        record.save(update_fields=["status", "status_code", "response_body"])

        return response

    return wrapper
