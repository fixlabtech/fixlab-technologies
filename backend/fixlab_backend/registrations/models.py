from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, blank=True)  # Google Classroom code

    def __str__(self):
        return self.name


class Registration(models.Model):
    PAYMENT_CHOICES = (
        ('full', 'Full Payment'),
        ('installment', 'Installment')
    )
    STATUS_CHOICES = (
        ('partial', 'Partial'),
        ('completed', 'Completed')
    )
    MODE_CHOICES = (
        ("onsite", "Onsite"),
        ("virtual", "Virtual"),
    )

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)   # 🔑 one student = one row
    phone = models.CharField(max_length=20)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="registrations")
    mode_of_learning = models.CharField(max_length=10, choices=MODE_CHOICES)
    payment_option = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.course.name}"
    
    
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # For unsubscribe

    def __str__(self):
        return self.email