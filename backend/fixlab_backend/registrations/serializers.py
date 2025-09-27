class RegistrationSerializer(serializers.ModelSerializer):
    course = serializers.SlugRelatedField(
        queryset=Course.objects.all(),
        slug_field="name"   # allows passing course name instead of id
    )

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
