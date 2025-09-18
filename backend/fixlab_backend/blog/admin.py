from django.contrib import admin
from .models import Category, Tag, BlogPost, Comment, NewsletterSubscriber

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at", "is_published")
    list_filter = ("is_published", "category")
    search_fields = ("title", "content", "author")
    prepopulated_fields = {"slug": ("title",)}

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "created_at", "is_public")
    list_filter = ("is_public",)
    readonly_fields = ("created_at",)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'is_active', 'subscribed_at')  # updated field names
    list_filter = ('is_active', 'subscribed_at')  # updated field names
    search_fields = ('email',)
    ordering = ('-subscribed_at',)  # order by subscription date



