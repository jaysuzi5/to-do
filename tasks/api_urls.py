from django.urls import path
from . import api

urlpatterns = [
    path('alexa/add-task/', api.AlexaAddTaskView.as_view(), name='alexa_add_task'),
]
