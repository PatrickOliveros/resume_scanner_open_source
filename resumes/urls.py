from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('scan/', views.scan),
    path('health/', views.health)
]