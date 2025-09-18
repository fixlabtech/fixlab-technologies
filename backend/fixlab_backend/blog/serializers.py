from rest_framework import serializers
from .models import BlogPost, Category, Tag, Comment, NewsletterSubscriber


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class CategorySerializer(serializers.ModelSerializer):
    blog_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "blog_count")

    def get_blog_count(self, obj):
        return obj.posts.count()


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "post", "name", "email", "content", "created_at", "is_public")
        read_only_fields = ("id", "created_at", "is_public")  # removed 'post'



class BlogListSerializer(serializers.ModelSerializer):
    author = serializers.CharField()
    image = serializers.SerializerMethodField()
    excerpt = serializers.CharField()
    created_at = serializers.DateTimeField()
    category = CategorySerializer(read_only=True)  # ✅ include category info
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            "id", "title", "slug", "author", "excerpt", "content",
            "image", "created_at", "category","comments_count",
        )

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            try:
                url = obj.image.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                return ""
        return ""

    def get_comments_count(self, obj):
        return obj.comments.filter(is_public=True).count()
    

class BlogDetailSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    

    class Meta:
        model = BlogPost
        fields = (
            "id", "title", "slug", "author", "excerpt", "content",
            "image", "created_at", "updated_at", "category", "tags", "comments"
        )

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            try:
                url = obj.image.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                return ""
        return ""


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'subscribed_at', 'is_active']
