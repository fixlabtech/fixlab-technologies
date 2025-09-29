from django.contrib import admin
from .models import Course, Registration


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'code')   # ✅ added amount so you see fees at a glance
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
        'created_at'
    )
    list_filter = ('course', 'mode_of_learning', 'gender', 'payment_status')
    search_fields = ('full_name', 'email', 'phone')
    readonly_fields = ('reference', 'created_at')   # ✅ avoid editing system-generated fields



