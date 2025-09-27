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
        # 👇 make payment_status read-only so only backend sets it
        read_only_fields = ['id', 'created_at', 'payment_status']

    def create(self, validated_data):
        """
        Automatically set payment_status based on payment_option
        """
        payment_option = validated_data.get("payment_option")
        # ✅ Default: "partial", unless full payment is chosen
        validated_data["payment_status"] = (
            "completed" if payment_option == "full" else "partial"
        )
        return super().create(validated_data)

    def validate_reference(self, value):
        """
        Each Paystack transaction generates a unique reference.
        Prevent duplicates but allow same student/course to register multiple times with new references.
        """
        if Registration.objects.filter(reference=value).exists():
            raise serializers.ValidationError("This payment reference has already been used.")
        return value
