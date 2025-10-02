from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BlogPost, NewsletterSubscriber
from .utils import send_email_via_sendgrid

@receiver(post_save, sender=BlogPost)
def send_blog_notification(sender, instance, created, **kwargs):
    if created:
        subscribers = NewsletterSubscriber.objects.filter(is_active=True)
        for subscriber in subscribers:
            subject = f"📢 New Blog Post Published: {instance.title}"
            message = f"""
Hello {subscriber.email},

We are excited to inform you that a new blog post has just been published:

{instance.title}

Read here: https://www.fixlabtech.com/blog/{instance.id}

If you no longer wish to receive updates, unsubscribe here:
https://www.fixlabtech.com/api/blog/unsubscribe/{subscriber.email}/

Best regards,  
The Fixlab Team
"""
            send_email_via_sendgrid(subject, message, subscriber.email)
