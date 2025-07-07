from django.contrib import admin
from django.urls import path, include  # include eklendi

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analiz.urls')),  # 👈 analiz app'e yönlendirme
]
