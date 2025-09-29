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
        db_conn = connections["default"]
        try:
            db_conn.cursor()
            db_status = "ok"
        except OperationalError:
            db_status = "error"

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

        try:
            course_obj = Course.objects.get(name=course_name)
        except Course.DoesNotExist:
            return Response(
                {"success": False, "message": "Course not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if action == "newRegistration":
            payload = {
                "email": email,
                "amount": int(course_obj.amount * 100),
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
                "course": course_obj.name,
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
        four_days_ago = datetime.now() - timedelta(days=4)
        pending_regs = Registration.objects.filter(
            payment_status="pending", created_at__lte=four_days_ago
        )
        for reg in pending_regs:
            subject = f"🔔 Payment Reminder - {reg.course.name}"
            message = f"""
<div style="font-family:Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
  <div style="max-width:600px; margin:auto; background-color:#ffffff; border-radius:8px; overflow:hidden; border:1px solid #ddd;">
    <div style="background-color:#0b5394; color:#fff; padding:15px; text-align:center; font-size:20px;">Fixlab Academy</div>
    <div style="padding:20px; color:#333;">
      <h2 style="color:#0b5394;">Payment Reminder</h2>
      <p>Hello <strong>{reg.full_name}</strong>,</p>
      <p>We noticed your payment for <strong>{reg.course.name}</strong> is still pending.</p>
      <table style="border-collapse: collapse; width: 100%;">
        <tr style="background-color:#e6f2ff;">
          <td style="padding:8px; border:1px solid #ccc;"><strong>Reference:</strong></td>
          <td style="padding:8px; border:1px solid #ccc;">{reg.reference_no}</td>
        </tr>
      </table>
      <p>Please complete your payment to confirm your registration.</p>
      <p>Thank you,<br><strong>Fixlab Academy Team</strong></p>
    </div>
    <div style="background-color:#0b5394; color:#fff; text-align:center; padding:10px; font-size:12px;">
      &copy; {datetime.now().year} Fixlab Academy. All rights reserved.
    </div>
  </div>
</div>
"""
            send_email_via_sendgrid(subject, message, reg.email)


class PaymentVerificationAPIView(APIView):
    """ Verifies Paystack transaction and sends notifications after success """

    def get(self, request):
        reference_no = request.query_params.get("reference") or request.query_params.get("trxref")
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
            self._send_payment_notifications(reg)
            return Response({"success": True, "message": "Payment verified and emails sent."})

        reg.payment_status = "failed"
        reg.save()
        return Response({"success": False, "message": "Payment failed."},
                        status=status.HTTP_400_BAD_REQUEST)

    def _send_payment_notifications(self, reg):
        completed_courses = Registration.objects.filter(email=reg.email, payment_status="completed").exclude(id=reg.id)

        if completed_courses.exists():
            student_subject = f"New Course Registration)"
            student_msg = self._build_email_html(
                title="Payment Confirmed",
                greeting=reg.full_name,
                message=f"Your payment for the <strong>additional course {reg.course.name}</strong> has been successfully received.
                </br>
                <b> Registration Details: </b>",
                table_rows=[
                    ("Course", reg.course.name),
                    ("Amount Paid", f"₦{reg.course.amount}"),
                    ("Reference No.", reg.reference_no),
                    ("Date", reg.created_at.strftime("%d %B %Y, %I:%M %p"))
                ],
                footer="Thank you for continuing your learning journey with <strong>Fixlab Academy, your LMS account will be updated with the new course within 24 hours</strong>.
                </br>
                Warm regards</br>
                Fixlab Academy Team </br>
                <i>Creat, Innovate and Train</i>"
            )
            support_subject = f"New Course Payment Received - {reg.full_name}"
            support_msg = self._build_email_html(
                title="New Course Payment Received",
                greeting=None,
                message=f"Student <strong>{reg.full_name}</strong> has successfully paid for a new course.
                </br>
                <b> Registration Details: </b>",
                table_rows=[
                    ("Course", reg.course.name),
                    ("Amount Paid", f"₦{reg.course.amount}"),
                    ("Reference", reg.reference_no),
                    ("Date", reg.created_at.strftime("%d %B %Y, %I:%M %p"))
                ],
                footer="Update student LMS account with the new course within 24 hours."
            )
        else:
            student_subject = f"Course Registration"
            student_msg = self._build_email_html(
                title="Payment Confirmed",
                greeting=reg.full_name,
                message=f"Your registration for <strong>{reg.course.name}</strong> has been confirmed.
                </br>
                <b> Registration Details: </b>",
                table_rows=[
                    ("Course", reg.course.name),
                    ("Amount Paid", f"₦{reg.course.amount}"),
                    ("Reference No.", reg.reference_no),
                    ("Date", reg.created_at.strftime("%d %B %Y, %I:%M %p"))
                ],
                footer="Our academic support team will contact you within 24 hours with your LMS credentials and schedule. </br>
                Warm regards</br>
                Fixlab Academy Team </br>
                <i>Creat, Innovate and Train</i>"
            )
            support_subject = f"New Registration Received"
            support_msg = self._build_email_html(
                title="New Registration Payment Received",
                greeting=None,
                message=f"A new student has successfully registered and paid.
                </br>
                <b> Registration Details: </b>",
                table_rows=[
                    ("Name", reg.full_name),
                    ("Email", reg.email),
                    ("Phone", reg.phone),
                    ("Course", reg.course.name),
                    ("Amount Paid", f"₦{reg.course.amount}"),
                    ("Reference", reg.reference_no),
                    ("Date", reg.created_at.strftime("%d %B %Y, %I:%M %p"))
                ],
                footer="Create a new LMS account and send credentials within 24 hours."
            )

        send_email_via_sendgrid(student_subject, student_msg, reg.email)
        send_email_via_sendgrid(support_subject, support_msg, "support@fixlabtech.freshdesk.com")

    @staticmethod
    def _build_email_html(title, greeting, message, table_rows, footer):
        table_html = "".join(
            f'<tr style="background-color:#e6f2ff;"><td style="padding:8px; border:1px solid #ccc;">{k}</td>'
            f'<td style="padding:8px; border:1px solid #ccc;">{v}</td></tr>'
            for k, v in table_rows
        )
        greeting_html = f"<p>Hello <strong>{greeting}</strong>,</p>" if greeting else ""
        html = f"""
<div style="font-family:Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
  <div style="max-width:600px; margin:auto; background-color:#ffffff; border-radius:8px; overflow:hidden; border:1px solid #ddd;">
    <div style="background-color:#0b5394; color:#fff; padding:15px; text-align:center; font-size:20px;">Fixlab Academy</div>
    <div style="padding:20px; color:#333;">
      <h2 style="color:#0b5394;">{title}</h2>
      {greeting_html}
      <p>{message}</p>
      <table style="border-collapse: collapse; width: 100%;">{table_html}</table>
      <p>{footer}</p>
    </div>
    <div style="background-color:#0b5394; color:#fff; text-align:center; padding:10px; font-size:12px;">
      &copy; {datetime.now().year} Fixlab Academy. All rights reserved.
    </div>
  </div>
</div>
"""
        return html


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
