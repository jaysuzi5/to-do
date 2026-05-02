import json
import logging

from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import OpenApiParameter, extend_schema

from .models import Task, TaskList
from .serializers import TaskCreateSerializer, TaskListSerializer, TaskSerializer

logger = logging.getLogger('todo')

USER_MAP = {
    'jay': 'jaysuzi5@gmail.com',
    'suzanne': 'jaysuziq@gmail.com',
}


class StaticTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'tasks.rest_views.StaticTokenAuthentication'
    name = 'BearerToken'

    def get_security_definition(self, auto_schema):
        return {'type': 'http', 'scheme': 'bearer'}


class StaticTokenAuthentication(BaseAuthentication):
    """Validates Authorization: Bearer <TODO_API_TOKEN>."""

    def authenticate(self, request):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return None
        token = auth[7:]
        api_token = getattr(settings, 'TODO_API_TOKEN', '')
        if not api_token or token != api_token:
            raise AuthenticationFailed('Invalid API token.')
        return (None, token)

    def authenticate_header(self, request):
        return 'Bearer'


class HasAPIToken(BasePermission):
    def has_permission(self, request, view):
        return request.auth is not None


class TaskListsView(APIView):
    authentication_classes = [StaticTokenAuthentication]
    permission_classes = [HasAPIToken]

    @extend_schema(
        summary='List all task lists',
        parameters=[
            OpenApiParameter(
                'owner',
                str,
                description='Filter by owner username (jay or suzanne)',
                required=False,
            ),
        ],
        responses={200: TaskListSerializer(many=True)},
    )
    def get(self, request):
        qs = TaskList.objects.select_related('owner').all()
        owner = request.query_params.get('owner', '').lower().strip()
        if owner:
            email = USER_MAP.get(owner)
            if not email:
                return Response(
                    {'error': f"Unknown owner '{owner}'. Valid values: {', '.join(USER_MAP)}"},
                    status=400,
                )
            qs = qs.filter(owner__email=email)
        return Response(TaskListSerializer(qs, many=True).data)


class TaskListTasksView(APIView):
    authentication_classes = [StaticTokenAuthentication]
    permission_classes = [HasAPIToken]

    @extend_schema(
        summary='List open tasks in a task list',
        responses={200: TaskSerializer(many=True)},
    )
    def get(self, request, list_id):
        task_list = get_object_or_404(TaskList, pk=list_id)
        tasks = task_list.tasks.exclude(status=Task.STATUS_COMPLETED).order_by(
            'due_date', 'created_at'
        )
        return Response(TaskSerializer(tasks, many=True).data)

    @extend_schema(
        summary='Add a task to a task list',
        request=TaskCreateSerializer,
        responses={201: TaskSerializer},
    )
    def post(self, request, list_id):
        task_list = get_object_or_404(TaskList, pk=list_id)
        serializer = TaskCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        task = serializer.save(task_list=task_list)
        logger.info(json.dumps({
            'event': 'api_task_created',
            'task_id': task.pk,
            'task_title': task.title,
            'list_id': list_id,
        }))
        return Response(TaskSerializer(task).data, status=201)


class TaskCompleteView(APIView):
    authentication_classes = [StaticTokenAuthentication]
    permission_classes = [HasAPIToken]

    @extend_schema(
        summary='Mark a task as complete',
        request=None,
        responses={200: TaskSerializer},
    )
    def post(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        if task.is_complete:
            return Response(TaskSerializer(task).data)
        task.mark_complete()
        return Response(TaskSerializer(task).data)
