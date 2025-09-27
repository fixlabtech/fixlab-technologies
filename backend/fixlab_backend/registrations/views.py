from django.views import View
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Registration, Course
from .serializers import RegistrationSerializer
from django.conf import settings
import requests
from django.core.cache import cache

# ✅ Import SendGrid helper
from .utils import send_email_via_sendgrid


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        # Check database
        db_conn = connections['default']
        try:
            db_conn.cursor()
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
    Handles:
    - newRegistration: first-time registration
    - installment: complete installment
    - newCourse: existing user adding a new course
    """

    def post(self, request):
        data = request.data
        reference = data.get("reference")
        action = data.get("action")
        email = data.get("email")
        course_name = data.get("course")

        if not reference:
            return Response(
                {"success": False, "message": "Payment reference is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ----- VERIFY PAYSTACK PAYMENT -----
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        url = f"https://api.paystack.co/transaction/verify/{reference}"

        try:
            r = requests.get(url, headers=headers, timeout=10)
            result = r.json()
        except Exception as e:
            return Response(
                {"success": False, "message": f"Could not connect to Paystack: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        if not result.get("status") or not result.get("data") or result["data"].get("status") != "success":
            return Response(
                {"success": False, "message": "Payment not successful."},
                status=status.HTTP_400_BAD_REQUEST
            )

        paystack_data = result["data"]
        amount_paid = paystack_data.get("amount", 0) / 100  # Paystack returns amount in kobo
        metadata = paystack_data.get("metadata", {})

        # ----- GET COURSE OBJECT IF NEEDED -----
        course_obj = None
        if course_name:
            try:
                course_obj = Course.objects.get(name=course_name)
            except Course.DoesNotExist:
                return Response(
                    {"success": False, "message": "Course not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        payment_option = data.get("payment_option", "installment")

        # ✅ Payment status logic:
        # if payment_option == "full", set to completed
        # if payment_option == "installment" but amount >= expected_full_amount, set to completed
        # otherwise partial
        expected_amount = float(metadata.get("course_price", amount_paid))  # fallback to paid amount if no metadata
        if payment_option == "full" or amount_paid >= expected_amount:
            payment_status = "completed"
        else:
            payment_status = "partial"

        # ---- NEW REGISTRATION ----
        if action == "newRegistration":
            serializer = RegistrationSerializer(data={
                "full_name": data.get("full_name"),
                "email": email,
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
                self._send_notifications(reg, course_obj, action="newRegistration")
                return Response({"success": True, "message": "Registration successful"})
            return Response({"success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # ---- INSTALLMENT ----
        elif action == "installment":
            reg = Registration.objects.filter(email=email).order_by("-created_at").first()
            if not reg:
                return Response({"success": False, "message": "No registration found for this email."},
                                status=status.HTTP_404_NOT_FOUND)
            reg.payment_status = payment_status
            reg.reference = reference
            reg.save()
            self._send_notifications(reg, reg.course, action="installment")
            return Response({"success": True, "message": "Installment updated"})

        # ---- NEW COURSE ----
        elif action == "newCourse":
            existing_reg = Registration.objects.filter(email=email).first()
            if not existing_reg:
                return Response({"success": False, "message": "Student not found. Please register first."},
                                status=status.HTTP_404_NOT_FOUND)

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
            self._send_notifications(new_reg, course_obj, action="newCourse")
            return Response({"success": True, "message": "New course registered"})

        else:
            return Response({"success": False, "message": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

    def _send_notifications(self, reg, course_obj=None, action=None):
        """
        Sends emails to support and student for all actions using SendGrid
        """
        if action == "newRegistration":
            # Support
            support_subject = f"🎓 New Student Registration: {reg.full_name}"
            support_message = f"""
A new student has registered successfully.<br><br>

Name: {reg.full_name}<br>
Email: {reg.email}<br>
Phone: {reg.phone}<br>
Course: {reg.course.name if reg.course else "N/A"}<br>
Mode of learning: {reg.mode_of_learning}<br>
Payment option: {reg.payment_option}<br>
Payment status: {reg.payment_status}<br>
Reference: {reg.reference}<br>
Message: {reg.message}<br>
"""
            # Student
            student_subject = f"Welcome to Fixlab Academy - {course_obj.name if course_obj else ''}"
            student_message = f"""
Hello {reg.full_name},<br><br>

We are delighted to confirm your registration for <b>{course_obj.name if course_obj else ''}</b> ({reg.mode_of_learning}).<br><br>

📌 Payment option: {reg.payment_option.capitalize()}<br>
📌 Payment status: {reg.payment_status.capitalize()}<br>
📌 Payment reference: {reg.reference}<br><br>

Our support team is creating your LMS account.<br>
➡️ You will receive your login details via email within 24 hours.<br><br>

Best regards,<br>
Fixlab Academy
"""
        elif action == "installment":
            support_subject = f"💰 Installment Updated: {reg.full_name}"
            support_message = f"""
Student installment status has been updated.<br><br>

Name: {reg.full_name}<br>
Email: {reg.email}<br>
Course: {reg.course.name if reg.course else "N/A"}<br>
Reference: {reg.reference}<br>
Payment status: {reg.payment_status.capitalize()}<br>
"""
            student_subject = f"Payment Update - {reg.course.name if reg.course else ''}"
            student_message = f"""
Hello {reg.full_name},<br><br>

Your installment payment for <b>{reg.course.name if reg.course else ''}</b> has been updated.<br><br>

📌 Payment status: {reg.payment_status.capitalize()}<br>
📌 Payment reference: {reg.reference}<br><br>

Thank you for your commitment.<br><br>
Best regards,<br>
Fixlab Academy
"""
        elif action == "newCourse":
            support_subject = f"📚 New Course Enrollment: {reg.full_name}"
            support_message = f"""
An existing student has enrolled in a new course.<br><br>

Name: {reg.full_name}<br>
Email: {reg.email}<br>
New Course: {reg.course.name if reg.course else "N/A"}<br>
Mode of learning: {reg.mode_of_learning}<br>
Payment option: {reg.payment_option}<br>
Payment status: {reg.payment_status}<br>
Reference: {reg.reference}<br>
"""
            student_subject = f"Enrollment Update - {reg.course.name if reg.course else ''}"
            student_message = f"""
Hello {reg.full_name},<br><br>

Your enrollment has been successfully updated with a new course:<br>
<b>{reg.course.name if reg.course else ''}</b> ({reg.mode_of_learning})<br><br>

📌 Payment option: {reg.payment_option.capitalize()}<br>
📌 Payment status: {reg.payment_status.capitalize()}<br>
📌 Payment reference: {reg.reference}<br><br>

Thank you for continuing your learning journey with us.<br><br>
Best regards,<br>
Fixlab Academy
"""

        # ✅ Send via SendGrid
        send_email_via_sendgrid(support_subject, support_message, "support@fixlabtech.com")
        send_email_via_sendgrid(student_subject, student_message, reg.email)


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
