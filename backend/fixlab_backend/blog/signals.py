from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import BlogPost, NewsletterSubscriber

@receiver(post_save, sender=BlogPost)
def send_blog_notification(sender, instance, created, **kwargs):
    if created:
        # Get all active subscribers
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)

        for subscriber in subscribers:
            subject = f"📢 New Blog Post Published: {instance.title}"
            
            message = f"""
Hello {subscriber.email},

We are excited to inform you that a new blog post has just been published on our platform:

Title: {instance.title}

You can read the full article here: http://127.0.0.1:8000/blog_details.html?id={instance.id}

If you no longer wish to receive these updates, you can unsubscribe anytime by clicking the link below:
http://127.0.0.1:8000/api/newsletter/unsubscribe/{subscriber.email}/

We hope you continue to enjoy our content. If you unsubscribe, you can always resubscribe later!

Best regards,
The Fixlab Team
"""
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [subscriber.email],
                fail_silently=False,
            )
