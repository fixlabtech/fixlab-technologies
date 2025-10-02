from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.timezone import now
from .models import BlogPost, NewsletterSubscriber
from .utils import send_email_via_sendgrid


# Reuse styled email builder
def build_email_html(title, greeting, message, footer):
    greeting_html = f"<p>Hello <strong>{greeting}</strong>,</p>" if greeting else ""
    html = f"""
<div style="font-family:Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
  <div style="max-width:600px; margin:auto; background-color:#ffffff; border-radius:8px; overflow:hidden; border:1px solid #ddd;">
    <div style="background-color:#0b5394; color:#fff; padding:15px; text-align:center; font-size:20px;">Fixlab Academy</div>
    <div style="padding:20px; color:#333;">
      <h2 style="color:#0b5394;">{title}</h2>
      {greeting_html}
      <p>{message}</p>
      <p>{footer}</p>
    </div>
    <div style="background-color:#0b5394; color:#fff; text-align:center; padding:10px; font-size:12px;">
      &copy; {now().year} Fixlab Team. All rights reserved.
    </div>
  </div>
</div>
"""
    return html


@receiver(post_save, sender=BlogPost)
def send_blog_notification(sender, instance, created, **kwargs):
    if created:
        # Get all active subscribers
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)

        for subscriber in subscribers:
            subject = f"📢 New Blog Post: {instance.title}"

            # Styled email content
            html_message = build_email_html(
                title=f"New Blog Published: {instance.title}",
                greeting=subscriber.email,
                message=f"We’ve just published a new blog post on our platform! 🎉<br><br>"
                        f"<strong>{instance.title}</strong><br><br>"
                        f"<a href='https://www.fixlabtech.com/blog_details?id={instance.id}' "
                        f"style='display:inline-block; padding:10px 20px; background:#0b5394; color:#fff; border-radius:5px; text-decoration:none;'>"
                        f"Read Full Article</a>",
                footer=f"If you no longer wish to receive these updates, you can unsubscribe anytime:<br>"
                       f"<a href='https://www.services.fixlabtech.com/api/blog/unsubscribe/{subscriber.email}/'>Unsubscribe</a>"
            )

            send_email_via_sendgrid(subject, html_message, subscriber.email)
