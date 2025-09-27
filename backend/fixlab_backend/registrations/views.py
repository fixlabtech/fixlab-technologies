from django.views import View
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Registration, Course
from .serializers import RegistrationSerializer
from django.core.mail import send_mail
from django.conf import settings
import requests
from django.core.cache import cache


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        # Check database
        try:
            connections['default'].cursor()
            db_status = "ok"
        except OperationalError:
            db_status = "error"

        # Check cache
        try:
            cache.set('health_check', 'ok', timeout=5)
            cache_status = "ok" if cache.get('health_check') == 'ok' else "error"
        except Exception:
            cache_status = "error"

        overall_status = "ok" if db_status == "ok" and cache_status == "ok" else "error"
        status_code = 200 if overall_status == "ok" else 500

        return JsonResponse(
            {"status": overall_status, "database": db_status, "cache": cache_status},
            status=status_code
        )


class RegistrationAPIView(APIView):
    """
    Handles all registration-related actions:
    - newRegistration
    - installment
    - newCourse
    """

    def post(self, request):
        data = request.data
        reference = data.get("reference")
        action = data.get("action")
        email = data.get("email")
        course_name = data.get("course")

        if not reference or not action or not email:
            return Response(
                {"success": False, "message": "Reference, action, and email are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----- VERIFY PAYSTACK PAYMENT -----
        if not self.verify_payment(reference):
            return Response(
                {"success": False, "message": "Payment verification failed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----- GET COURSE -----
        course_obj = None
        if course_name:
            try:
                course_obj = Course.objects.get(name=course_name)
            except Course.DoesNotExist:
                return Response({"success": False, "message": "Course not found."},
                                status=status.HTTP_404_NOT_FOUND)

        # ----- HANDLE ACTIONS -----
        if action == "newRegistration":
            return self.handle_new_registration(data, course_obj, reference)
        elif action == "installment":
            return self.handle_installment(email, reference)
        elif action == "newCourse":
            return self.handle_new_course(email, data, course_obj, reference)
        else:
            return Response({"success": False, "message": "Invalid action."},
                            status=status.HTTP_400_BAD_REQUEST)

    def verify_payment(self, reference):
        """Returns True if Paystack payment is successful"""
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            result = r.json()
            data = result.get("data")
            return result.get("status") and data and data.get("status") == "success"
        except Exception:
            return False

    def handle_new_registration(self, data, course_obj, reference):
        payment_option = data.get("payment_option", "installment")
        payment_status = "completed" if payment_option == "full" else "partial"

        serializer = RegistrationSerializer(data={
            "full_name": data.get("full_name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "course": course_obj.id if course_obj else None,
            "mode_of_learning": data.get("mode_of_learning"),
            "payment_option": payment_option,
            "payment_status": payment_status,
            "reference": reference,
            "message": data.get("message", "")
        })
        if serializer.is_valid():
            reg = serializer.save()
            self.send_notifications(reg, course_obj, "newRegistration")
            return Response({"success": True, "message": "Registration successful"})
        return Response({"success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def handle_installment(self, email, reference):
        reg = Registration.objects.filter(email=email).order_by("-created_at").first()
        if not reg:
            return Response({"success": False, "message": "No registration found for this email."},
                            status=status.HTTP_404_NOT_FOUND)
        reg.payment_status = "completed"
        reg.reference = reference
        reg.save()
        self.send_notifications(reg, reg.course, "installment")
        return Response({"success": True, "message": "Installment completed"})

    def handle_new_course(self, email, data, course_obj, reference):
        existing_reg = Registration.objects.filter(email=email).first()
        if not existing_reg:
            return Response({"success": False, "message": "Student not found. Please register first."},
                            status=status.HTTP_404_NOT_FOUND)

        payment_option = data.get("payment_option", "installment")
        payment_status = "completed" if payment_option == "full" else "partial"

        new_reg = Registration.objects.create(
            full_name=existing_reg.full_name,
            email=existing_reg.email,
            phone=existing_reg.phone,
            course=course_obj,
            mode_of_learning=data.get("mode_of_learning", existing_reg.mode_of_learning),
            payment_option=payment_option,
            payment_status=payment_status,
            reference=reference,
            message=data.get("message", existing_reg.message)
        )
        self.send_notifications(new_reg, course_obj, "newCourse")
        return Response({"success": True, "message": "New course registered"})

    def send_notifications(self, reg, course_obj, action):
        """Sends emails to support and student for all actions"""
        if action == "newRegistration":
            support_subject = f"🎓 New Student Registration: {reg.full_name}"
            support_message = f"""
A new student has registered successfully.

Name: {reg.full_name}
Email: {reg.email}
Phone: {reg.phone}
Course: {reg.course.name if reg.course else "N/A"}
Mode of learning: {reg.mode_of_learning}
Payment option: {reg.payment_option}
Payment status: {reg.payment_status}
Reference: {reg.reference}
Message: {reg.message}
"""
            student_subject = f"Welcome to Fixlab Academy - {course_obj.name if course_obj else ''}"
            student_message = f"""
Hello {reg.full_name},

We are delighted to confirm your registration for **{course_obj.name if course_obj else ''}** ({reg.mode_of_learning}).

📌 Payment option: {reg.payment_option.capitalize()}
📌 Payment status: {reg.payment_status.capitalize()}
📌 Payment reference: {reg.reference}

Our support team is creating your LMS account.  
➡️ You will receive your login details via email within 24 hours.

Best regards,  
Fixlab Academy
"""
        elif action == "installment":
            support_subject = f"💰 Installment Completed: {reg.full_name}"
            support_message = f"""
Student has completed installment payment.

Name: {reg.full_name}
Email: {reg.email}
Course: {reg.course.name if reg.course else "N/A"}
Reference: {reg.reference}

Payment status updated to: Completed
"""
            student_subject = f"Payment Confirmation - {reg.course.name if reg.course else ''}"
            student_message = f"""
Hello {reg.full_name},

We are pleased to confirm that your installment payment for **{reg.course.name if reg.course else ''}** has been completed.

📌 Payment status: Completed
📌 Payment reference: {reg.reference}

Thank you for your commitment.

Best regards,  
Fixlab Academy
"""
        elif action == "newCourse":
            support_subject = f"📚 New Course Enrollment: {reg.full_name}"
            support_message = f"""
An existing student has enrolled in a new course.

Name: {reg.full_name}
Email: {reg.email}
New Course: {reg.course.name if reg.course else "N/A"}
Mode of learning: {reg.mode_of_learning}
Payment option: {reg.payment_option}
Payment status: {reg.payment_status}
Reference: {reg.reference}
"""
            student_subject = f"Enrollment Update - {reg.course.name if reg.course else ''}"
            student_message = f"""
Hello {reg.full_name},

Your enrollment has been successfully updated with a new course:  
**{reg.course.name if reg.course else ''}** ({reg.mode_of_learning})

📌 Payment option: {reg.payment_option.capitalize()}
📌 Payment status: {reg.payment_status.capitalize()}
📌 Payment reference: {reg.reference}

Thank you for continuing your learning journey with us.

Best regards,  
Fixlab Academy
"""
        # Send emails
        send_mail(support_subject, support_message, settings.DEFAULT_FROM_EMAIL,
                  ["support@fixlabtech.freshdesk.com"])
        send_mail(student_subject, student_message, settings.DEFAULT_FROM_EMAIL, [reg.email])


class CheckUserAPIView(APIView):
    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response({"success": False, "message": "Email is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        reg = Registration.objects.filter(email=email).order_by("-created_at").first()
        if not reg:
            return Response({"exists": False})

        return Response({
            "exists": True,
            "full_name": reg.full_name,
            "email": reg.email,
            "course": reg.course.name if reg.course else None,
            "mode_of_learning": reg.mode_of_learning,
            "payment_option": reg.payment_option,
            "payment_status": reg.payment_status,
            "reference": reg.reference
        })
