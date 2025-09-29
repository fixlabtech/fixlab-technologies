from django.contrib import admin
from .models import Course, Registration


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'code')   # ✅ show amount
    search_fields = ('name', 'code')


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'email',
        'course',
        'mode_of_learning',
        'gender',
        'payment_status',
        'reference_no',
        'created_at'
    )
    list_filter = ('course', 'mode_of_learning', 'gender', 'payment_status')
    search_fields = ('full_name', 'email', 'phone', 'reference_no')
    readonly_fields = ('created_at',)   # ✅ allow editing reference_no if needed

