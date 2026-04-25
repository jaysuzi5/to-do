import json
import logging
import time
import uuid

logger = logging.getLogger('todo')

SKIP_PATHS = ('/static/', '/media/', '/health', '/favicon.ico')


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in SKIP_PATHS):
            return self.get_response(request)

        transaction_id = str(uuid.uuid4())[:8]
        request.transaction_id = transaction_id
        start = time.monotonic()

        try:
            response = self.get_response(request)
        except Exception as exc:
            logger.error(json.dumps({
                'transaction_id': transaction_id,
                'method': request.method,
                'path': request.path,
                'error': str(exc),
            }), exc_info=True)
            raise

        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        user = request.user if hasattr(request, 'user') else None
        logger.info(json.dumps({
            'transaction_id': transaction_id,
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'elapsed_ms': elapsed_ms,
            'user_id': user.pk if user and user.is_authenticated else None,
            'username': user.email if user and user.is_authenticated else None,
        }))
        return response
