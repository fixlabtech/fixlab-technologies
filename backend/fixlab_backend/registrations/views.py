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

        # ----- GET COURSE OBJECT -----
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

        # ✅ Payment status logic
        expected_amount = float(metadata.get("course_price", amount_paid))
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
        Sends detailed professional emails via SendGrid
        """
        if action == "newRegistration":
            # Support
            support_subject = f"🎓 New Student Registration: {reg.full_name}"
            support_message = f"""
<b>New Student Registration Alert</b><br><br>
A new student has successfully registered.<br><br>

<b>Student Details:</b><br>
- Name: {reg.full_name}<br>
- Email: {reg.email}<br>
- Phone: {reg.phone}<br>
- Course: {reg.course.name if reg.course else "N/A"}<br>
- Mode of learning: {reg.mode_of_learning}<br>
- Payment option: {reg.payment_option.capitalize()}<br>
- Payment status: {reg.payment_status.capitalize()}<br>
- Reference: {reg.reference}<br>
- Additional message: {reg.message or "None"}<br><br>

📌 Please ensure the student’s LMS account is created and access credentials sent within 24 hours.<br><br>

Regards,<br>
<i>Fixlab Academy Automated System</i>
"""

            # Student
            student_subject = f"✅ Welcome to Fixlab Academy - {course_obj.name if course_obj else ''}"
            student_message = f"""
Hello {reg.full_name},<br><br>

Welcome to <b>Fixlab Academy</b>! 🎉<br>
Your registration for <b>{course_obj.name if course_obj else ''}</b> ({reg.mode_of_learning}) has been confirmed.<br><br>

<b>Payment Details:</b><br>
- Option: {reg.payment_option.capitalize()}<br>
- Status: {reg.payment_status.capitalize()}<br>
- Reference: {reg.reference}<br><br>

<b>Next Steps:</b><br>
- Your LMS account is being created.<br>
- You will receive login credentials via email within 24 hours.<br>
- Our support team is available if you need assistance.<br><br>

We are committed to providing world-class, practical training to help you achieve your career goals.<br><br>

Warm regards,<br>
<b>Fixlab Academy Team</b><br>
<i>Transforming Learners into Professionals</i>
"""

        elif action == "installment":
            support_subject = f"💰 Installment Payment Update: {reg.full_name}"
            support_message = f"""
<b>Installment Payment Update</b><br><br>
The following student’s payment record has been updated:<br><br>

- Name: {reg.full_name}<br>
- Email: {reg.email}<br>
- Course: {reg.course.name if reg.course else "N/A"}<br>
- Reference: {reg.reference}<br>
- Current Status: {reg.payment_status.capitalize()}<br><br>

📌 Please reconcile this payment and ensure the student’s account reflects the update.<br><br>

Fixlab Academy Automated System
"""

            student_subject = f"📢 Payment Update - {reg.course.name if reg.course else ''}"
            student_message = f"""
Hello {reg.full_name},<br><br>

Your installment payment for <b>{reg.course.name if reg.course else ''}</b> has been updated in our system.<br><br>

<b>Payment Details:</b><br>
- Status: {reg.payment_status.capitalize()}<br>
- Reference: {reg.reference}<br><br>

Thank you for your continued trust and commitment.<br><br>

Best regards,<br>
<b>Fixlab Academy Team</b>
"""

        elif action == "newCourse":
            support_subject = f"📚 New Course Enrollment: {reg.full_name}"
            support_message = f"""
<b>New Course Enrollment</b><br><br>
An existing student has enrolled in a new course.<br><br>

- Name: {reg.full_name}<br>
- Email: {reg.email}<br>
- Course: {reg.course.name if reg.course else "N/A"}<br>
- Mode: {reg.mode_of_learning}<br>
- Payment option: {reg.payment_option.capitalize()}<br>
- Payment status: {reg.payment_status.capitalize()}<br>
- Reference: {reg.reference}<br><br>

📌 Ensure LMS access is updated for the new course.<br><br>

Fixlab Academy Automated System
"""

            student_subject = f"🎉 New Course Enrollment - {reg.course.name if reg.course else ''}"
            student_message = f"""
Hello {reg.full_name},<br><br>

We’re excited to let you know your enrollment has been updated with a new course:<br><br>

<b>Course:</b> {reg.course.name if reg.course else ''}<br>
<b>Mode of learning:</b> {reg.mode_of_learning}<br>
<b>Payment option:</b> {reg.payment_option.capitalize()}<br>
<b>Status:</b> {reg.payment_status.capitalize()}<br>
<b>Reference:</b> {reg.reference}<br><br>

Our team will update your LMS account within 24 hours so you can start accessing your new course materials.<br><br>

Best regards,<br>
<b>Fixlab Academy Team</b><br>
<i>Transforming Learners into Professionals</i>
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
