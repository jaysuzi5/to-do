from django.contrib import admin
from .models import Task, TaskList


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ['title', 'priority', 'status', 'due_date', 'added_via_alexa']
    readonly_fields = ['added_via_alexa']


@admin.register(TaskList)
class TaskListAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_default', 'pending_count', 'created_at']
    list_filter = ['owner', 'is_default']
    search_fields = ['name', 'owner__email', 'owner__first_name', 'owner__last_name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [TaskInline]

    def pending_count(self, obj):
        return obj.pending_count
    pending_count.short_description = 'Pending'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'task_list', 'priority', 'status', 'due_date', 'added_via_alexa', 'created_at']
    list_filter = ['status', 'priority', 'added_via_alexa', 'task_list__owner']
    search_fields = ['title', 'notes', 'task_list__name', 'task_list__owner__email']
    date_hierarchy = 'created_at'
    readonly_fields = ['added_via_alexa', 'completed_at', 'created_at', 'updated_at']
    fieldsets = [
        (None, {'fields': ['task_list', 'title', 'notes']}),
        ('Status', {'fields': ['status', 'priority', 'due_date', 'completed_at']}),
        ('Meta', {'fields': ['added_via_alexa', 'created_at', 'updated_at']}),
    ]
