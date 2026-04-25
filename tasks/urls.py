from django.urls import path
from . import views

urlpatterns = [
    # Health check (no auth, used by k8s readiness probe)
    path('health/', views.health, name='health'),

    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Task Lists
    path('lists/new/', views.TaskListCreateView.as_view(), name='task_list_create'),
    path('lists/<slug:slug>/', views.TaskListDetailView.as_view(), name='task_list_detail'),
    path('lists/<slug:slug>/delete/', views.TaskListDeleteView.as_view(), name='task_list_delete'),

    # Tasks
    path('lists/<slug:list_slug>/tasks/new/', views.TaskCreateView.as_view(), name='task_create'),
    path('lists/<slug:list_slug>/tasks/quick-add/', views.QuickAddTaskView.as_view(), name='task_quick_add'),
    path('tasks/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_edit'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('tasks/<int:pk>/toggle/', views.TaskToggleCompleteView.as_view(), name='task_toggle'),
]
