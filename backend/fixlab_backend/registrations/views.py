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


class VerifyAndRegisterAPIView(APIView):
    """
    Verify Paystack payment before registering student
    """
    def post(self, request):
        reference = request.data.get("reference")
        if not reference:
            return Response(
                {"success": False, "message": "Payment reference is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

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

        if not result.get("status"):
            return Response(
                {"success": False, "message": result.get("message", "Verification failed.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = result.get("data")
        if not data or data.get("status") != "success":
            return Response(
                {"success": False, "message": "Payment not successful."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Payment verified, forward to Registration
        reg_view = RegistrationAPIView.as_view()
        return reg_view(request._request)


class RegistrationAPIView(APIView):
    """
    Handles:
    - newRegistration: first-time registration
    - installment: complete installment
    - newCourse: existing user adding a new course
    """

    def post(self, request):
        data = request.data
        action = data.get('action')
        email = data.get('email')
        course_name = data.get('course')
        reference = data.get('reference')

        if not action or not email or not reference:
            return Response(
                {"success": False, "message": "Email, action, and reference are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get course if needed
        course_obj = None
        if action in ["newRegistration", "newCourse"] and course_name:
            try:
                course_obj = Course.objects.get(name=course_name)
            except Course.DoesNotExist:
                return Response(
                    {"success": False, "message": "Course not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        payment_option = data.get('payment_option', 'installment')
        payment_status = "completed" if payment_option == "full" else "partial"

        # ---- NEW REGISTRATION ----
        if action == "newRegistration":
            serializer = RegistrationSerializer(data={
                "full_name": data.get('full_name'),
                "email": email,
                "phone": data.get('phone'),
                "course": course_obj.id,
                "mode_of_learning": data.get('mode_of_learning'),
                "payment_option": payment_option,
                "payment_status": payment_status,
                "reference": reference,
                "message": data.get('message', '')
            })
            if serializer.is_valid():
                reg = serializer.save()

                # Notify support
                support_subject = f"🎓 New Student Registration: {reg.full_name}"
                support_message = f"""
A new student has registered:

Name: {reg.full_name}
Email: {reg.email}
Phone: {reg.phone}
Course: {reg.course.name}
Mode of learning: {reg.mode_of_learning}
Payment option: {reg.payment_option}
Payment status: {reg.payment_status}
Reference: {reg.reference}
Message: {reg.message}
"""
                send_mail(support_subject, support_message, settings.DEFAULT_FROM_EMAIL,
                          ["support@fixlabtech.freshdesk.com"])

                # Notify student
                student_subject = f"Welcome to Fixlab Academy - {course_obj.name}"
                student_message = f"""
Hello {reg.full_name},

We are delighted to confirm your registration for **{course_obj.name}** ({reg.mode_of_learning}).

📌 Payment option: {reg.payment_option.capitalize()}
📌 Payment status: {reg.payment_status.capitalize()}
📌 Payment reference: {reg.reference}

Our support team is creating your LMS account.  
➡️ You will receive your login details via email within 24 hours.

Best regards,  
Fixlab Academy
"""
                send_mail(student_subject, student_message, settings.DEFAULT_FROM_EMAIL, [email])

                return Response({"success": True, "message": "Registration successful"})
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---- INSTALLMENT ----
        elif action == "installment":
            reg = Registration.objects.filter(email=email, reference=reference).first()
            if not reg:
                return Response(
                    {"success": False, "message": "Registration not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            reg.payment_status = "completed"
            reg.save()

            # Notify support
            support_subject = f"💰 Installment Completed: {reg.full_name}"
            support_message = f"""
Student has completed installment payment:

Name: {reg.full_name}
Email: {reg.email}
Course: {reg.course.name}
Reference: {reg.reference}

Payment status is now: Completed.
"""
            send_mail(support_subject, support_message, settings.DEFAULT_FROM_EMAIL,
                      ["support@fixlabtech.freshdesk.com"])

            # Notify student
            student_subject = f"Payment Confirmation - {reg.course.name}"
            student_message = f"""
Hello {reg.full_name},

We are pleased to confirm that your installment payment for **{reg.course.name}** has been completed.

📌 Payment status: Completed
📌 Payment reference: {reg.reference}

Thank you for your commitment.

Best regards,  
Fixlab Academy
"""
            send_mail(student_subject, student_message, settings.DEFAULT_FROM_EMAIL, [email])

            return Response({"success": True})

        # ---- NEW COURSE ----
        elif action == "newCourse":
            existing_reg = Registration.objects.filter(email=email).first()
            if not existing_reg:
                return Response(
                    {"success": False, "message": "Student not found. Please register first."},
                    status=status.HTTP_404_NOT_FOUND
                )

            if existing_reg.course == course_obj:
                return Response(
                    {"success": False, "message": "Student is already registered for this course."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            existing_reg.course = course_obj
            existing_reg.mode_of_learning = data.get('mode_of_learning', existing_reg.mode_of_learning)
            existing_reg.payment_option = payment_option
            existing_reg.payment_status = payment_status
            existing_reg.reference = data.reference
            existing_reg.message = data.get('message', existing_reg.message)
            existing_reg.save()

            # Notify support
            support_subject = f"📚 New Course Enrollment: {existing_reg.full_name}"
            support_message = f"""
An existing student has registered for a new course:

Name: {existing_reg.full_name}
Email: {existing_reg.email}
New Course: {course_obj.name}
Mode of learning: {existing_reg.mode_of_learning}
Payment option: {existing_reg.payment_option}
Payment status: {existing_reg.payment_status}
Reference: {existing_reg.reference}
"""
            send_mail(support_subject, support_message, settings.DEFAULT_FROM_EMAIL,
                      ["support@fixlabtech.freshdesk.com"])

            # Notify student
            student_subject = f"Enrollment Update - {course_obj.name}"
            student_message = f"""
Hello {existing_reg.full_name},

Your enrollment has been successfully updated with a new course:  
**{course_obj.name}** ({existing_reg.mode_of_learning})

📌 Payment option: {existing_reg.payment_option.capitalize()}
📌 Payment status: {existing_reg.payment_status.capitalize()}
📌 Payment reference: {existing_reg.reference}

Thank you for continuing your learning journey with us.

Best regards,  
Fixlab Academy
"""
            send_mail(student_subject, student_message, settings.DEFAULT_FROM_EMAIL, [email])

            return Response({"success": True, "message": "New course registered"})

        else:
            return Response(
                {"success": False, "message": "Invalid action."},
                status=status.HTTP_400_BAD_REQUEST
            )


class CheckUserAPIView(APIView):
    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response(
                {"success": False, "message": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        reg = Registration.objects.filter(email=email).first()
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
