from django.urls import path
from . import views
from .views import NewsletterSubscribeView,NewsletterUnsubscribeView


urlpatterns = [
    path("blogs/", views.BlogListView.as_view(), name="api-blogs"),
    path("blogs/<int:id>/", views.BlogDetailView.as_view(), name="api-blog-detail"),
    path("blogs/<int:post_id>/comments/", views.PostCommentsView.as_view(), name="api-blog-comments"),
    path("categories/", views.CategoryListView.as_view(), name="api-categories"),
    path("tags/", views.TagListView.as_view(), name="api-tags"),
    path("newsletter/subscribe/", NewsletterSubscribeView.as_view(), name='newsletter-subscribe'),
    path("unsubscribe/<str:email>/", NewsletterUnsubscribeView.as_view(), name='unsubscribe'),

]
