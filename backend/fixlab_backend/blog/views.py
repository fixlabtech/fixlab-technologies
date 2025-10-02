from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import now

from .utils import send_email_via_sendgrid
from .models import BlogPost, Category, Tag, Comment, NewsletterSubscriber
from .serializers import (
    BlogListSerializer,
    BlogDetailSerializer,
    CategorySerializer,
    TagSerializer,
    CommentSerializer,
)
from .pagination import StandardResultsSetPagination


# Helper for standardized API responses
def api_response(status_text, message, data=None, http_status=status.HTTP_200_OK):
    return Response(
        {"status": status_text, "message": message, "data": data},
        status=http_status,
    )


# Helper to build styled HTML email (same design across all emails)
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


# ---------------- BLOG VIEWS ----------------

class BlogListView(generics.ListAPIView):
    serializer_class = BlogListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = BlogPost.objects.filter(is_published=True).select_related("category").prefetch_related("tags")
        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")
        ordering = self.request.query_params.get("ordering")

        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(content__icontains=search)
                | Q(excerpt__icontains=search)
                | Q(author__icontains=search)
            )

        if category:
            try:
                qs = qs.filter(category__id=int(category))
            except ValueError:
                pass

        if ordering:
            qs = qs.order_by(ordering)

        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return api_response("success", "Blogs retrieved successfully", response.data)


class BlogDetailView(generics.RetrieveAPIView):
    queryset = BlogPost.objects.filter(is_published=True).prefetch_related("tags", "comments", "category")
    serializer_class = BlogDetailSerializer
    lookup_field = "id"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response("success", "Blog retrieved successfully", serializer.data)


class CategoryListView(APIView):
    def get(self, request):
        cats = Category.objects.annotate(blog_count=Count("posts")).order_by("name")
        serializer = CategorySerializer(cats, many=True)
        return api_response("success", "Categories retrieved successfully", serializer.data)


class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return api_response("success", "Tags retrieved successfully", response.data)


class PostCommentsView(APIView):
    def get(self, request, post_id):
        comments = Comment.objects.filter(post_id=post_id, is_public=True)
        serializer = CommentSerializer(comments, many=True)
        return api_response("success", "Comments retrieved successfully", serializer.data)

    def post(self, request, post_id):
        data = request.data.copy()
        data["post"] = post_id
        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return api_response("success", "Comment added successfully", serializer.data, status.HTTP_201_CREATED)
        return api_response("error", "Invalid data", serializer.errors, status.HTTP_400_BAD_REQUEST)


# ---------------- NEWSLETTER VIEWS ----------------

class NewsletterSubscribeView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return api_response("error", "Email is required.", http_status=status.HTTP_400_BAD_REQUEST)

        subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)

        if not created and subscriber.is_active:
            return api_response("exists", "You are already subscribed.")

        subscriber.is_active = True
        subscriber.save()

        subject = "🎉 Welcome to The Fixlab Newsletter!"
        html_message = build_email_html(
            title="Welcome to Fixlab Newsletter",
            greeting=subscriber.email,
            message="Thank you for subscribing 🎊. You’ll now receive updates whenever we publish new blogs and announcements.",
            footer=f"If you wish to unsubscribe anytime, click here:<br>"
                   f"<a href='https://www.services.fixlabtech.com/api/blog/unsubscribe/{subscriber.email}/'>Unsubscribe</a>"
        )
        send_email_via_sendgrid(subject, html_message, subscriber.email)

        return api_response(
            "subscribed" if created else "resubscribed",
            "Subscription successful! A confirmation email has been sent.",
        )


class NewsletterUnsubscribeView(APIView):
    def get(self, request, email):
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email)

            if not subscriber.is_active:
                message = "You are already unsubscribed."
            else:
                subscriber.is_active = False
                subscriber.save()

                subject = "⚠️ You Have Unsubscribed"
                html_message = build_email_html(
                    title="You Have Unsubscribed",
                    greeting=subscriber.email,
                    message="You have successfully unsubscribed from our newsletter. We’re sorry to see you go 💔.",
                    footer=f"If you ever change your mind, resubscribe here:<br>"
                           f"<a href='https://www.services.fixlabtech.com/api/blog/subscribe/{subscriber.email}/'>Resubscribe</a>"
                )
                send_email_via_sendgrid(subject, html_message, subscriber.email)

                message = "You have unsubscribed successfully. A confirmation email has been sent."

            return render(request, "newsletter/unsubscribe.html", {"message": message})

        except NewsletterSubscriber.DoesNotExist:
            message = "Email not found."
            return render(request, "newsletter/unsubscribe.html", {"message": message})
