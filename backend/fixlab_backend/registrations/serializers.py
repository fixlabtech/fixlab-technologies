from rest_framework import serializers
from .models import Registration, Course

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name', 'code']


class RegistrationSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())

    class Meta:
        model = Registration
        fields = [
            'id',
            'full_name',
            'email',
            'phone',
            'course',
            'mode_of_learning',
            'payment_option',
            'payment_status',
            'reference',
            'message',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

