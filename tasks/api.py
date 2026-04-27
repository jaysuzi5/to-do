import base64
import json
import logging
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Task, TaskList

logger = logging.getLogger('todo')

USER_MAP = {
    'jay': 'jaysuzi5@gmail.com',
    'suzanne': 'jaysuziq@gmail.com',
}


def _alexa_speech(text, end_session=True):
    return JsonResponse({
        'version': '1.0',
        'response': {
            'outputSpeech': {'type': 'PlainText', 'text': text},
            'shouldEndSession': end_session,
        },
    })


def _valid_cert_url(url):
    p = urlparse(url)
    return (
        p.scheme == 'https'
        and p.hostname == 's3.amazonaws.com'
        and (p.port is None or p.port == 443)
        and p.path.startswith('/echo.api/')
    )


def _create_task(username, task_title, list_name):
    """
    Returns (task, resolved_list_name) on success.
    Raises ValueError with a user-friendly message on failure.
    """
    email = USER_MAP.get(username)
    if not email:
        names = ' or '.join(k.title() for k in USER_MAP)
        raise ValueError(f"I don't know who {username!r} is. I can add tasks for {names}.")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        raise ValueError(f"Account not found for {username}.")

    task_list = None
    if list_name:
        task_list = (
            TaskList.objects.filter(owner=user, name__iexact=list_name).first()
            or TaskList.objects.filter(owner=user, name__icontains=list_name).first()
        )
    if not task_list:
        task_list = (
            TaskList.objects.filter(owner=user, is_default=True).first()
            or TaskList.objects.filter(owner=user).first()
        )
    if not task_list:
        raise ValueError(f"No task list found for {username}.")

    task = Task.objects.create(
        task_list=task_list,
        title=task_title,
        added_via_alexa=True,
    )
    logger.info(json.dumps({
        'event': 'alexa_task_created',
        'task_id': task.pk,
        'task_title': task_title,
        'list': task_list.name,
        'user': username,
    }))
    return task, task_list.name


@method_decorator(csrf_exempt, name='dispatch')
class AlexaAddTaskView(View):

    def post(self, request):
        try:
            _body_preview = json.loads(request.body)
            _req_type = _body_preview.get('request', {}).get('type', 'unknown')
            _intent_name = _body_preview.get('request', {}).get('intent', {}).get('name', '')
        except Exception:
            _req_type = 'parse_error'
            _intent_name = ''
        logger.info(json.dumps({
            'event': 'alexa_request_received',
            'path': request.path,
            'request_type': _req_type,
            'intent_name': _intent_name,
            'has_sig': bool(request.headers.get('Signature')),
            'has_cert': bool(request.headers.get('SignatureCertChainUrl')),
            'has_auth': bool(request.headers.get('Authorization')),
            'content_length': request.headers.get('Content-Length', '?'),
        }))

        auth = request.headers.get('Authorization', '')
        is_direct = auth.startswith('Bearer ')

        if is_direct:
            token = auth[7:]
            if not settings.ALEXA_SKILL_TOKEN or token != settings.ALEXA_SKILL_TOKEN:
                return JsonResponse({'error': 'Unauthorized'}, status=401)
        else:
            skip_verify = getattr(settings, 'ALEXA_SKIP_VERIFY', False)
            if skip_verify:
                logger.warning(json.dumps({'event': 'alexa_verify_skipped'}))
            elif not self._verify_alexa(request):
                return JsonResponse({'error': 'Forbidden'}, status=403)

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            if is_direct:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            return _alexa_speech("I couldn't understand that request.")

        if is_direct:
            return self._direct(body)
        return self._alexa(body)

    # ------------------------------------------------------------------
    # Direct API (Bearer token)
    # ------------------------------------------------------------------

    def _direct(self, body):
        username = (body.get('user') or '').lower().strip()
        task_title = (body.get('task') or '').strip()
        list_name = (body.get('list') or '').strip()

        if not task_title:
            return JsonResponse({'error': 'task is required'}, status=400)

        try:
            task, _ = _create_task(username, task_title, list_name)
            return JsonResponse({'status': 'ok', 'task_id': task.pk})
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

    # ------------------------------------------------------------------
    # Alexa intent handler
    # ------------------------------------------------------------------

    def _alexa(self, body):
        req = body.get('request', {})
        req_type = req.get('type', '')

        if req_type == 'LaunchRequest':
            return _alexa_speech(
                "Welcome to To Do. You can say: add wash the windows to Jay's list.",
                end_session=False,
            )

        if req_type == 'SessionEndedRequest':
            return JsonResponse({'version': '1.0', 'response': {}})

        if req_type != 'IntentRequest':
            return _alexa_speech("I'm not sure what to do with that.")

        intent = req.get('intent', {})
        name = intent.get('name', '')

        if name in ('AMAZON.CancelIntent', 'AMAZON.StopIntent'):
            return _alexa_speech("Goodbye!")

        if name == 'AMAZON.HelpIntent':
            return _alexa_speech(
                "Say things like: add wash the windows to Jay's To Do List. "
                "What would you like to add?"
            )

        if name != 'AddTaskIntent':
            return _alexa_speech("I can only add tasks right now.")

        slots = intent.get('slots', {})
        username = (slots.get('UserName', {}).get('value') or '').lower().strip()
        task_title = (slots.get('Task', {}).get('value') or '').strip()
        list_name = (slots.get('ListName', {}).get('value') or '').strip()

        if not task_title:
            return _alexa_speech("I didn't catch the task name. Please try again.")

        try:
            _, resolved_list = _create_task(username, task_title, list_name)
            return _alexa_speech(f"Added {task_title} to {resolved_list}.")
        except ValueError as e:
            return _alexa_speech(str(e))

    # ------------------------------------------------------------------
    # Alexa request verification (signature + timestamp)
    # ------------------------------------------------------------------

    def _verify_alexa(self, request):
        cert_url = request.headers.get('SignatureCertChainUrl', '')
        sig_b64 = request.headers.get('Signature', '')

        if not cert_url or not sig_b64:
            return False

        if not _valid_cert_url(cert_url):
            logger.warning('Alexa: invalid cert URL: %s', cert_url)
            return False

        # Timestamp check — reject requests older than 150 s
        try:
            body = json.loads(request.body)
            ts_str = body.get('request', {}).get('timestamp', '')
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            age = abs((datetime.now(timezone.utc) - ts).total_seconds())
            if age > 150:
                logger.warning('Alexa: stale timestamp %.0fs', age)
                return False
        except Exception:
            logger.warning('Alexa: missing or invalid timestamp')
            return False

        # Certificate download + signature verification
        try:
            with urllib.request.urlopen(cert_url, timeout=5) as resp:
                cert_pem = resp.read()

            cert = x509.load_pem_x509_certificate(cert_pem)
            now = datetime.now(timezone.utc)
            if now < cert.not_valid_before_utc or now > cert.not_valid_after_utc:
                logger.warning('Alexa: certificate outside validity window')
                return False

            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            if 'echo-api.amazon.com' not in san.value.get_values_for_type(x509.DNSName):
                logger.warning('Alexa: cert SAN missing echo-api.amazon.com')
                return False

            sig = base64.b64decode(sig_b64)
            cert.public_key().verify(sig, request.body, padding.PKCS1v15(), hashes.SHA1())
            return True

        except InvalidSignature:
            logger.warning('Alexa: signature mismatch')
            return False
        except Exception as e:
            logger.warning('Alexa: verification error: %s', e)
            return False
