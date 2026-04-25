from .models import TaskList


def user_task_lists(request):
    if request.user.is_authenticated:
        return {'nav_task_lists': TaskList.objects.filter(owner=request.user)}
    return {'nav_task_lists': []}
