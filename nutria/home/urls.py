from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.post_list_create, name='post-list-create'),
    path('posts/<str:post_id>/like/', views.post_like, name='post-like'),  # ← str, not int
    path('comments/', views.comment_list_create, name='comment-create'),
    path('stories/', views.story_list_create, name='story-list-create'),  # ← NEW
]