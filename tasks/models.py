from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class TaskList(models.Model):
    """A named to-do list belonging to a single user."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_lists')
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.name} ({self.owner.get_full_name() or self.owner.email})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.owner.pk}-{self.name}")
            slug = base
            n = 1
            while TaskList.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def pending_count(self):
        return self.tasks.filter(status__in=[Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS]).count()

    @property
    def completed_count(self):
        return self.tasks.filter(status=Task.STATUS_COMPLETED).count()


class Task(models.Model):
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    PRIORITY_ORDER = {PRIORITY_URGENT: 0, PRIORITY_HIGH: 1, PRIORITY_MEDIUM: 2, PRIORITY_LOW: 3}

    task_list = models.ForeignKey(TaskList, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=500)
    notes = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    added_via_alexa = models.BooleanField(default=False)

    class Meta:
        ordering = ['status', 'due_date', 'created_at']

    def __str__(self):
        return self.title

    @property
    def is_complete(self):
        return self.status == self.STATUS_COMPLETED

    @property
    def is_overdue(self):
        return (
            self.due_date
            and self.status != self.STATUS_COMPLETED
            and self.due_date < timezone.localdate()
        )

    @property
    def priority_badge_class(self):
        return {
            self.PRIORITY_URGENT: 'danger',
            self.PRIORITY_HIGH: 'warning',
            self.PRIORITY_MEDIUM: 'primary',
            self.PRIORITY_LOW: 'secondary',
        }.get(self.priority, 'secondary')

    def mark_complete(self):
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def mark_pending(self):
        self.status = self.STATUS_PENDING
        self.completed_at = None
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
