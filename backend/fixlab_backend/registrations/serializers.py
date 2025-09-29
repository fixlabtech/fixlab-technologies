from rest_framework import serializers
from .models import Registration, Course


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name', 'code', 'amount']


class RegistrationSerializer(serializers.ModelSerializer):
    # Use course name instead of primary key
    course = serializers.SlugRelatedField(
        queryset=Course.objects.all(),
        slug_field='name'
    )

    class Meta:
        model = Registration
        fields = [
            'id',
            'full_name',
            'gender',
            'email',
            'phone',
            'address',
            'occupation',
            'course',
            'payment_status',
            'reference_no',   # ✅ renamed here
            'message',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'payment_status']

    def create(self, validated_data):
        """
        - Do NOT generate reference_no here.
        - reference_no is returned by Paystack when initializing a transaction.
        - Backend updates registration with Paystack’s reference.
        """
        validated_data["payment_status"] = "pending"
        return super().create(validated_data)

    def validate_reference_no(self, value):
        """
        Ensure reference_no is unique.
        """
        if Registration.objects.filter(reference_no=value).exists():
            raise serializers.ValidationError("This reference number has already been used.")
        return value
