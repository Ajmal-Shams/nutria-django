from django.urls import path
from .views import save_google_user

urlpatterns = [
     path('api/save-user/', save_google_user),
]
