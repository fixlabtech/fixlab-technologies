from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from contact.views import ContactMessageCreateView  # if needed

urlpatterns = [
    
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path("api/blog/", include("blog.urls")),
    path('api/', include('registrations.urls')),  # Our registrations API
    path('api/contact/', ContactMessageCreateView.as_view(), name='contact-create'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
