from django.views import View
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
import requests

from .models import Registration, Course
from .serializers import RegistrationSerializer
from .utils import send_email_via_sendgrid


PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/"


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        # DB check
        db_conn = connections["default"]
        try:
            db_conn.cursor()
            db_status = "ok"
        except OperationalError:
            db_status = "error"

        # Cache check
        try:
            cache.set("health_check", "ok", timeout=5)
            cache_status = "ok" if cache.get("health_check") == "ok" else "error"
        except Exception:
            cache_status = "error"

        overall_status = "ok" if db_status == "ok" and cache_status == "ok" else "error"
        return JsonResponse(
            {"status": overall_status, "database": db_status, "cache": cache_status},
            status=200 if overall_status == "ok" else 500,
        )


class RegistrationAPIView(APIView):
    """
    Handles:
    - New registration (action='newRegistration')
    - New course registration for existing students (action='newCourse')
    """

    def post(self, request):
        data = request.data
        action = data.get("action")
        email = data.get("email")
        course_name = data.get("course")

        # Resolve course
        try:
            course_obj = Course.objects.get(name=course_name)
        except Course.DoesNotExist:
            return Response(
                {"success": False, "message": "Course not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # === 1. NEW REGISTRATION ===
        if action == "newRegistration":
            payload = {
                "email": email,
                "amount": int(course_obj.amount * 100),  # Paystack expects kobo
                "callback_url": "https://www.fixlabtech.com/payment-success",
            }
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            try:
                r = requests.post(PAYSTACK_INIT_URL, json=payload, headers=headers, timeout=10)
                res = r.json()
            except Exception as e:
                return Response(
                    {"success": False, "message": f"Paystack init error: {str(e)}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            if not res.get("status"):
                return Response(
                    {"success": False, "message": res.get("message", "Paystack init failed")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            reference_no = res["data"]["reference"]
            auth_url = res["data"]["authorization_url"]

            serializer = RegistrationSerializer(data={
                "full_name": data.get("full_name"),
                "gender": data.get("gender"),
                "email": email,
                "phone": data.get("phone"),
                "address": data.get("address"),
                "occupation": data.get("occupation"),
                "course": course_obj.id,
                "reference_no": reference_no,
                "message": data.get("message", "")
            })
            if serializer.is_valid():
                serializer.save(payment_status="pending")
                return Response({
                    "success": True,
                    "payment_url": auth_url,
                    "reference_no": reference_no,
                    "message": "Registration created. Redirect to Paystack to complete payment."
                }, status=status.HTTP_201_CREATED)
            return Response({"success": False, "message": serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        # === 2. NEW COURSE (existing student) ===
        elif action == "newCourse":
            existing = Registration.objects.filter(email=email).first()
            if not existing:
                return Response({"success": False, "message": "Student not found. Register first."},
                                status=status.HTTP_404_NOT_FOUND)

            payload = {
                "email": email,
                "amount": int(course_obj.amount * 100),
                "callback_url": "https://www.fixlabtech.com/payment-success",
            }
            headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            r = requests.post(PAYSTACK_INIT_URL, json=payload, headers=headers)
            res = r.json()
            if not res.get("status"):
                return Response({"success": False, "message": "Paystack init failed"},
                                status=status.HTTP_400_BAD_REQUEST)

            reference_no = res["data"]["reference"]
            auth_url = res["data"]["authorization_url"]

            Registration.objects.create(
                full_name=existing.full_name,
                gender=existing.gender,
                email=existing.email,
                phone=existing.phone,
                address=existing.address,
                occupation=existing.occupation,
                course=course_obj,
                payment_status="pending",
                reference_no=reference_no,
                message=data.get("message", existing.message)
            )
            return Response({
                "success": True,
                "payment_url": auth_url,
                "reference_no": reference_no,
                "message": f"New course {course_obj.name} registered. Proceed to payment."
            })

        return Response({"success": False, "message": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def send_pending_payment_reminders():
        """ Reminders for payments older than 4 days """
        four_days_ago = datetime.now() - timedelta(days=4)
        pending_regs = Registration.objects.filter(
            payment_status="pending", created_at__lte=four_days_ago
        )
        for reg in pending_regs:
            subject = f"🔔 Payment Reminder - {reg.course.name}"
            message = f"""
Hello {reg.full_name},<br><br>
We noticed your payment for <b>{reg.course.name}</b> is still pending.<br>
Please complete your payment to confirm your registration.<br><br>
Reference: {reg.reference_no}<br><br>
Thank you,<br>Fixlab Team
"""
            send_email_via_sendgrid(subject, message, reg.email)


class PaymentVerificationAPIView(APIView):
    """ Verifies Paystack transaction and sends notifications after success """

    def get(self, request):
        reference_no = request.query_params.get("reference")
        if not reference_no:
            return Response({"success": False, "message": "Reference required."},
                            status=status.HTTP_400_BAD_REQUEST)

        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        r = requests.get(f"{PAYSTACK_VERIFY_URL}{reference_no}", headers=headers)
        res = r.json()

        try:
            reg = Registration.objects.get(reference_no=reference_no)
        except Registration.DoesNotExist:
            return Response({"success": False, "message": "Registration not found."},
                            status=status.HTTP_404_NOT_FOUND)

        if res.get("status") and res["data"]["status"] == "success":
            reg.payment_status = "completed"
            reg.save()

            # Send notifications after payment success
            self._send_payment_notifications(reg)

            return Response({"success": True, "message": "Payment verified and emails sent."})

        reg.payment_status = "failed"
        reg.save()
        return Response({"success": False, "message": "Payment failed."},
                        status=status.HTTP_400_BAD_REQUEST)

    def _send_payment_notifications(self, reg):
        """
        Sends professional notifications for both new registration and new course
        """

        # Check if this email already had a previous completed course
        completed_courses = Registration.objects.filter(email=reg.email, payment_status="completed").exclude(id=reg.id)

        if completed_courses.exists():
            # === NEW COURSE ===
            student_subject = f"✅ Payment Confirmed - New Course ({reg.course.name})"
            student_msg = f"""
Hello {reg.full_name},<br><br>

We are pleased to confirm that your payment for an <b>additional course</b>, <b>{reg.course.name}</b>, has been successfully received.<br><br>

<b>Course Enrollment Details:</b><br>
- Student Name: {reg.full_name}<br>
- New Course: {reg.course.name}<br>
- Reference No: {reg.reference_no}<br>
- Payment Status: Completed<br>
- Registration Date: {reg.created_at.strftime("%d %B %Y, %I:%M %p")}<br><br>

<b>Next Steps:</b><br>
📌 Your LMS account will be updated to include this new course. Our academic team will reach out with the schedule and materials.<br><br>

Thank you for continuing your learning journey with <b>Fixlab Academy</b>.<br><br>

Warm regards,<br>
<b>Fixlab Academy Team</b><br>
<i>create, innovate and Train</i>
"""
            support_subject = f"🎓 New Course Payment Received - {reg.full_name}"
            support_msg = f"""
<b>Payment Notification - Additional Course</b><br><br>

A student has successfully paid for a new course.<br><br>

<b>Student Information:</b><br>
- Name: {reg.full_name}<br>
- Email: {reg.email}<br>
- Phone: {reg.phone}<br><br>

<b>Course Details:</b><br>
- New Course: {reg.course.name}<br>
- Amount Paid: ₦{reg.course.amount}<br>
- Reference No: {reg.reference_no}<br>
- Date: {reg.created_at.strftime("%d %B %Y, %I:%M %p")}<br><br>

✅ Action Required: Update the student’s LMS account with the new course within 24 hours.<br><br>

Regards,<br>
<i>Fixlab Academy Automated System</i>
"""
        else:
            # === NEW REGISTRATION ===
            student_subject = f"✅ Payment Confirmed - {reg.course.name}"
            student_msg = f"""
Hello {reg.full_name},<br><br>

We are pleased to confirm your <b>new registration</b> for the <b>{reg.course.name}</b> program. Your payment has been successfully received.<br><br>

<b>Registration Details:</b><br>
- Student Name: {reg.full_name}<br>
- Course: {reg.course.name}<br>
- Reference No: {reg.reference_no}<br>
- Payment Status: Completed<br>
- Registration Date: {reg.created_at.strftime("%d %B %Y, %I:%M %p")}<br><br>

<b>Next Steps:</b><br>
📌 Our academic support team will contact you within 24 hours to provide your LMS login details, schedules, and onboarding instructions.<br><br>

Welcome to <b>Fixlab Academy</b>. We are excited to support your learning journey.<br><br>

Warm regards,<br>
<b>Fixlab Academy Team</b><br>
<i>create, innovate and Train</i>
"""
            support_subject = f"🎓 New Registration Payment Received - {reg.full_name}"
            support_msg = f"""
<b>Payment Notification - New Registration</b><br><br>

A new student has successfully registered and paid.<br><br>

<b>Student Information:</b><br>
- Name: {reg.full_name}<br>
- Gender: {reg.gender or "N/A"}<br>
- Email: {reg.email}<br>
- Phone: {reg.phone}<br>
- Address: {reg.address or "N/A"}<br>
- Occupation: {reg.occupation or "N/A"}<br><br>

<b>Course Details:</b><br>
- Course: {reg.course.name}<br>
- Amount Paid: ₦{reg.course.amount}<br>
- Reference No: {reg.reference_no}<br>
- Date: {reg.created_at.strftime("%d %B %Y, %I:%M %p")}<br><br>

✅ Action Required: Create a new LMS account and send credentials within 24 hours.<br><br>

Regards,<br>
<i>Fixlab Academy Automated System</i>
"""

        # Send both student and support emails
        send_email_via_sendgrid(student_subject, student_msg, reg.email)
        send_email_via_sendgrid(support_subject, support_msg, "support@fixlabtech.freshdesk.com")


class CheckUserAPIView(APIView):
    """ Check if student exists by email """

    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response({"success": False, "message": "Email required."},
                            status=status.HTTP_400_BAD_REQUEST)

        reg = Registration.objects.filter(email=email).order_by("-created_at").first()
        if not reg:
            return Response({"exists": False})

        return Response({
            "exists": True,
            "full_name": reg.full_name,
            "gender": reg.gender,
            "email": reg.email,
            "phone": reg.phone,
            "address": reg.address,
            "occupation": reg.occupation,
            "course": reg.course.name if reg.course else None,
            "payment_status": reg.payment_status,
            "reference_no": reg.reference_no
        })
