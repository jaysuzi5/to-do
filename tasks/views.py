import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView
from django.urls import reverse, reverse_lazy

from .forms import QuickAddTaskForm, TaskForm, TaskListForm
from .models import Task, TaskList

logger = logging.getLogger('todo')


def health(request):
    return HttpResponse('ok')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tasks/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        task_lists = TaskList.objects.filter(owner=self.request.user).annotate(
            ann_pending=Count('tasks', filter=Q(tasks__status__in=['pending', 'in_progress'])),
            ann_completed=Count('tasks', filter=Q(tasks__status='completed')),
            ann_total=Count('tasks'),
        )
        ctx['task_lists'] = task_lists
        ctx['total_pending'] = sum(tl.ann_pending for tl in task_lists)
        ctx['total_completed'] = sum(tl.ann_completed for tl in task_lists)
        ctx['quick_form'] = QuickAddTaskForm()
        return ctx


class TaskListDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'tasks/task_list.html'

    def get_object(self):
        return get_object_or_404(TaskList, slug=self.kwargs['slug'], owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        task_list = self.get_object()
        status_filter = self.request.GET.get('status', 'active')
        priority_filter = self.request.GET.get('priority', '')

        tasks = task_list.tasks.all()
        if status_filter == 'active':
            tasks = tasks.filter(status__in=[Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS])
        elif status_filter == 'completed':
            tasks = tasks.filter(status=Task.STATUS_COMPLETED)
        if priority_filter:
            tasks = tasks.filter(priority=priority_filter)

        ctx['task_list'] = task_list
        ctx['tasks'] = tasks
        ctx['status_filter'] = status_filter
        ctx['priority_filter'] = priority_filter
        ctx['quick_form'] = QuickAddTaskForm()
        return ctx


class TaskListCreateView(LoginRequiredMixin, CreateView):
    model = TaskList
    form_class = TaskListForm
    template_name = 'tasks/task_list_form.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, f'"{form.instance.name}" created.')
        return super().form_valid(form)


class TaskListDeleteView(LoginRequiredMixin, DeleteView):
    model = TaskList
    template_name = 'tasks/task_list_confirm_delete.html'
    success_url = reverse_lazy('dashboard')

    def get_queryset(self):
        return TaskList.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object.name}" deleted.')
        return super().form_valid(form)


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def get_task_list(self):
        return get_object_or_404(TaskList, slug=self.kwargs['list_slug'], owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['task_list'] = self.get_task_list()
        ctx['action'] = 'Add'
        return ctx

    def form_valid(self, form):
        form.instance.task_list = self.get_task_list()
        messages.success(self.request, 'Task added.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('task_list_detail', kwargs={'slug': self.kwargs['list_slug']})


class QuickAddTaskView(LoginRequiredMixin, View):
    def post(self, request, list_slug):
        task_list = get_object_or_404(TaskList, slug=list_slug, owner=request.user)
        form = QuickAddTaskForm(request.POST)
        if form.is_valid():
            Task.objects.create(task_list=task_list, title=form.cleaned_data['title'])
            messages.success(request, 'Task added.')
        return redirect(request.META.get('HTTP_REFERER') or reverse('task_list_detail', kwargs={'slug': list_slug}))


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def get_queryset(self):
        return Task.objects.filter(task_list__owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['task_list'] = self.object.task_list
        ctx['action'] = 'Edit'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Task updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('task_list_detail', kwargs={'slug': self.object.task_list.slug})


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'tasks/task_confirm_delete.html'

    def get_queryset(self):
        return Task.objects.filter(task_list__owner=self.request.user)

    def get_success_url(self):
        return reverse('task_list_detail', kwargs={'slug': self.object.task_list.slug})

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object.title}" deleted.')
        return super().form_valid(form)


class TaskToggleCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, task_list__owner=request.user)
        if task.is_complete:
            task.mark_pending()
            messages.success(request, f'"{task.title}" marked as pending.')
        else:
            task.mark_complete()
            messages.success(request, f'"{task.title}" completed!')
        return redirect(request.META.get('HTTP_REFERER') or reverse('task_list_detail', kwargs={'slug': task.task_list.slug}))
