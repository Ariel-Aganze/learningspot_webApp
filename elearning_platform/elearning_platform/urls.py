from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from . import views  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home_view, name='home'),  
    path('accounts/', include('accounts.urls')),
    path('courses/', include('courses.urls')),
    path('quizzes/', include('quizzes.urls')),
    path('events/', include('events.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)