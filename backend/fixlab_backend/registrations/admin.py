from django.contrib import admin
from .models import Course, Registration

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'course', 'mode_of_learning', 'payment_option', 'payment_status', 'reference', 'created_at')
    list_filter = ('course', 'mode_of_learning', 'payment_option', 'payment_status')
    search_fields = ('full_name', 'email', 'phone')
