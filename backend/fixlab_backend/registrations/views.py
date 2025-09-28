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
from datetime import datetime, timedelta

# SendGrid helper
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
    - Pre-payment registration (action='newRegistration')
    - Installments
    - Adding new courses
    """

    def post(self, request):
        data = request.data
        reference = data.get("reference")
        action = data.get("action")
        email = data.get("email")
        course_name = data.get("course")

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

        # ---- NEW REGISTRATION (PRE-PAYMENT) ----
        if action == "newRegistration":
            serializer = RegistrationSerializer(data={
                "full_name": data.get("full_name"),
                "email": email,
                "phone": data.get("phone"),
                "course": course_obj.id if course_obj else None,
                "mode_of_learning": data.get("mode_of_learning"),
                "payment_option": payment_option,
                "reference": reference or "pending",
                "message": data.get("message", "")
            })
            if serializer.is_valid():
                reg = serializer.save()
                # Emails are NOT sent yet; only after payment
                return Response({
                    "success": True,
                    "message": "Registration recorded. Proceed to payment.",
                    "registration_id": reg.id,
                    "reference": reg.reference
                })
            return Response({"success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # ---- INSTALLMENT ----
        elif action == "installment":
            reg = Registration.objects.filter(email=email).order_by("-created_at").first()
            if not reg:
                return Response({"success": False, "message": "No registration found for this email."},
                                status=status.HTTP_404_NOT_FOUND)
            reg.payment_status = "partial"
            reg.reference = reference or reg.reference
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
                payment_status="partial",
                reference=reference or "pending",
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
            # Support email
            support_subject = f"🎓 New Student Registration: {reg.full_name}"
            support_message = f"""
<b>New Student Registration Alert</b><br><br>
Name: {reg.full_name}<br>
Email: {reg.email}<br>
Phone: {reg.phone}<br>
Course: {reg.course.name if reg.course else "N/A"}<br>
Mode of learning: {reg.mode_of_learning}<br>
Payment option: {reg.payment_option.capitalize()}<br>
Payment status: {reg.payment_status.capitalize()}<br>
Reference: {reg.reference}<br>
Message: {reg.message or "None"}<br><br>
📌 Ensure the student’s LMS account is created and credentials sent within 24 hours.<br><br>
Regards,<br>
<i>Fixlab Academy Automated System</i>
"""
            # Student email
            student_subject = f"Welcome to Fixlab Academy - {course_obj.name if course_obj else ''}"
            student_message = f"""
Hello {reg.full_name},<br><br>
Your registration for <b>{course_obj.name if course_obj else ''}</b> ({reg.mode_of_learning}) has been recorded.<br>
Payment status: {reg.payment_status.capitalize()}<br>
Reference: {reg.reference}<br><br>
Please complete your payment to finalize registration.<br><br>
Warm regards,<br><b>Fixlab Team</b>
"""
            send_email_via_sendgrid(support_subject, support_message, "support@fixlabtech.com")
            send_email_via_sendgrid(student_subject, student_message, reg.email)

        elif action in ["installment", "newCourse"]:
            # Implement notifications if needed
            pass

    @staticmethod
    def send_pending_payment_reminders():
        """
        Send reminder emails to users with partial payment older than 4 days
        """
        four_days_ago = datetime.now() - timedelta(days=4)
        pending_regs = Registration.objects.filter(payment_status="partial", created_at__lte=four_days_ago)
        for reg in pending_regs:
            subject = f"🔔 Payment Reminder - {reg.course.name if reg.course else ''}"
            message = f"""
Hello {reg.full_name},<br><br>
We noticed your payment for <b>{reg.course.name if reg.course else ''}</b> is still pending.<br>
Please complete your payment to confirm your registration.<br><br>
Reference: {reg.reference}<br><br>
Thank you,<br>Fixlab Team
"""
            send_email_via_sendgrid(subject, message, reg.email)


class PaymentVerificationAPIView(APIView):
    """
    Called after Paystack payment is completed.
    Updates registration with real reference and sets payment_status to completed.
    """

    def post(self, request):
        reference = request.data.get("reference")
        registration_id = request.data.get("registration_id")

        if not reference or not registration_id:
            return Response({"success": False, "message": "Reference and registration ID required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Verify payment with Paystack
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            result = r.json()
        except Exception as e:
            return Response({"success": False, "message": f"Paystack error: {str(e)}"},
                            status=status.HTTP_502_BAD_GATEWAY)

        if not result.get("status") or not result.get("data") or result["data"].get("status") != "success":
            return Response({"success": False, "message": "Payment not successful."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Update registration
        try:
            reg = Registration.objects.get(id=registration_id)
        except Registration.DoesNotExist:
            return Response({"success": False, "message": "Registration not found."},
                            status=status.HTTP_404_NOT_FOUND)

        reg.reference = reference
        reg.payment_status = "completed"
        reg.save()

        # Send email notifications
        course_obj = reg.course
        RegistrationAPIView()._send_notifications(reg, course_obj, action="newRegistration")

        return Response({"success": True, "message": "Payment verified and registration completed."})


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
