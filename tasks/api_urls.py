from django.urls import path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import api, rest_views

urlpatterns = [
    # Alexa (existing)
    path('alexa/add-task/', api.AlexaAddTaskView.as_view(), name='alexa_add_task'),

    # REST API v1
    path('v1/lists/', rest_views.TaskListsView.as_view(), name='api_task_lists'),
    path('v1/lists/<int:list_id>/tasks/', rest_views.TaskListTasksView.as_view(), name='api_list_tasks'),
    path('v1/tasks/<int:task_id>/complete/', rest_views.TaskCompleteView.as_view(), name='api_task_complete'),

    # OpenAPI schema + Swagger UI
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
]
