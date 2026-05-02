from rest_framework import serializers

from drf_spectacular.utils import extend_schema_field

from .models import Task, TaskList


class TaskListSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()

    class Meta:
        model = TaskList
        fields = ['id', 'name', 'slug', 'owner', 'is_default', 'pending_count', 'created_at']

    @extend_schema_field(serializers.CharField())
    def get_owner(self, obj):
        return obj.owner.get_full_name() or obj.owner.email

    @extend_schema_field(serializers.IntegerField())
    def get_pending_count(self, obj):
        return obj.pending_count


class TaskSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'priority', 'status', 'due_date',
            'is_overdue', 'created_at', 'added_via_alexa',
        ]


class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    priority = serializers.ChoiceField(
        choices=Task.PRIORITY_CHOICES,
        default=Task.PRIORITY_MEDIUM,
        required=False,
    )
    due_date = serializers.DateField(required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def create(self, validated_data):
        return Task.objects.create(**validated_data)
