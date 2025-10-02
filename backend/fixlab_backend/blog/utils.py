import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_email_via_sendgrid(subject, message, to_email):
    """Send an email using SendGrid API client"""
    email = Mail(
        from_email="noreply@fixlabtech.com",   # must be verified in SendGrid
        to_emails=to_email,
        subject=subject,
        html_content=message
    )
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(email)
        print(f"✅ Email sent! Status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False
