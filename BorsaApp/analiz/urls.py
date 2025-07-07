# analiz/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.anasayfa, name='anasayfa'), # Anasayfa için URL (boş yol)
    path('autocomplete/', views.autocomplete, name='autocomplete'), # Otomatik tamamlama için URL
    path('analiz/<str:kod>/', views.analiz_sayfasi, name='analiz_sayfasi'), # Hisse kodu ile analiz sayfası
]