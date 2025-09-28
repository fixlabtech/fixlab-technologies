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
        # Read-only fields; backend controls ID, timestamp, and payment_status
        read_only_fields = ['id', 'created_at', 'payment_status']

    def create(self, validated_data):
        """
        Handle registration creation.
        - Assign default reference if not provided
        - Set payment_status to "partial" until payment verified
        """
        # If reference is missing or placeholder
        validated_data["reference"] = validated_data.get("reference", "pending")

        # Default payment status
        validated_data["payment_status"] = "partial"

        return super().create(validated_data)

    def validate_reference(self, value):
        """
        Prevent duplicate payment references
        """
        if Registration.objects.filter(reference=value).exists():
            raise serializers.ValidationError("This payment reference has already been used.")
        return value
