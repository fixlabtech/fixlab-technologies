from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .utils import send_email_via_sendgrid
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.shortcuts import render


from .models import BlogPost, Category, Tag, Comment, NewsletterSubscriber
from .serializers import (
    BlogListSerializer,
    BlogDetailSerializer,
    CategorySerializer,
    TagSerializer,
    CommentSerializer,
)
from .pagination import StandardResultsSetPagination


# Helper for standardized responses
def api_response(status_text, message, data=None, http_status=status.HTTP_200_OK):
    return Response(
        {"status": status_text, "message": message, "data": data},
        status=http_status,
    )


# List & create blogs (list is public)
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


# Retrieve single post
class BlogDetailView(generics.RetrieveAPIView):
    queryset = BlogPost.objects.filter(is_published=True).prefetch_related("tags", "comments", "category")
    serializer_class = BlogDetailSerializer
    lookup_field = "id"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})  # For absolute image URLs
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response("success", "Blog retrieved successfully", serializer.data)


# Categories list with blog counts
class CategoryListView(APIView):
    def get(self, request):
        cats = Category.objects.annotate(blog_count=Count("posts")).order_by("name")
        serializer = CategorySerializer(cats, many=True)
        return api_response("success", "Categories retrieved successfully", serializer.data)


# Tags list
class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return api_response("success", "Tags retrieved successfully", response.data)


# Comments for a post and creating new comment
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


# Newsletter subscription
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

        # Send welcome email
        subject = "🎉 Welcome to The Fixlab Newsletter!"
        message = f"""
Hi {subscriber.email},

Thank you for subscribing to our newsletter. 🎊  
You’ll now receive updates whenever a new blog post is published.

👉 If you wish to unsubscribe anytime, click here:
https://www.fixlabtech.com/api/blog/unsubscribe/{subscriber.email}/

We’re glad to have you onboard! 🚀  

Best regards,  
The Fixlab Team
"""
        send_email_via_sendgrid(subject, message, subscriber.email)

        return api_response(
            "subscribed" if created else "resubscribed",
            "Subscription successful! A confirmation email has been sent.",
        )


# Newsletter unsubscribe

class NewsletterUnsubscribeView(APIView):
    def get(self, request, email):
        try:
            subscriber = NewsletterSubscriber.objects.get(email=email)

            if not subscriber.is_active:
                message = "You are already unsubscribed."
            else:
                subscriber.is_active = False
                subscriber.save()

                # Send unsubscribe confirmation email
                subject = "⚠️ You Have Unsubscribed"
                email_message = f"""
Hi {subscriber.email},

You have successfully unsubscribed from The Fixlab Newsletter.  
We’re sorry to see you go. 💔

If you ever change your mind, you can resubscribe here:
https://www.fixlabtech.com/api/blog/subscribe/{subscriber.email}/

Thank you for being part of our community! 🙏  

Best regards,  
The Fixlab Team
"""
                send_email_via_sendgrid(
                    subject, email_message, subscriber.email
                )
                
                message = "You have unsubscribed successfully. A confirmation email has been sent."

            # Render HTML page with SweetAlert
            return render(request, "newsletter/unsubscribe.html", {"message": message})

        except NewsletterSubscriber.DoesNotExist:
            message = "Email not found."
            return render(request, "newsletter/unsubscribe.html", {"message": message})
