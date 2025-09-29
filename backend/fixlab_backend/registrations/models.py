from django.db import models


class Course(models.Model):
    name = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # ✅ Course fee
    code = models.CharField(max_length=20, blank=True)  # Optional: Classroom/Zoom/internal code

    def __str__(self):
        return f"{self.name} - ₦{self.amount}"


class Registration(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),     # Registration created, awaiting payment
        ('completed', 'Completed'), # Payment verified successfully
        ('failed', 'Failed'),       # Payment attempt failed/cancelled
    )

    MODE_CHOICES = (
        ("onsite", "Onsite"),
        ("virtual", "Virtual"),
    )

    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="registrations")
    mode_of_learning = models.CharField(max_length=10, choices=MODE_CHOICES)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reference_no = models.CharField(max_length=100, unique=True)  # ✅ Paystack reference number
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.course.name} ({self.payment_status})"

    @property
    def amount_due(self):
        """ Always return the full course fee """
        return self.course.amount
