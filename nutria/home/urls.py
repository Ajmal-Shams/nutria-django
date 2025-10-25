from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.post_list_create, name='post-list-create'),
    path('posts/<str:post_id>/like/', views.post_like, name='post-like'),  # ← str, not int
    path('comments/', views.comment_list_create, name='comment-create'),
    path('stories/', views.story_list_create, name='story-list-create'), 
    path('recipes/add/', views.add_recipe, name='add_recipe'),
    path('recipes/search/', views.search_recipes, name='search_recipes'),
     # home/urls.py - Add these URL patterns to your existing urls



    path('toggle-follow/', views.toggle_follow, name='toggle_follow'),
    path('user-stats/<str:username>/', views.get_user_stats, name='user_stats'),
    path('followers/<str:username>/', views.get_followers_list, name='followers_list'),
    path('following/<str:username>/', views.get_following_list, name='following_list'),
    path('check-follow/', views.check_follow_status, name='check_follow_status'),
    path('toggle-save/', views.toggle_save_post, name='toggle_save_post'),
    path('saved-posts/<str:username>/', views.get_saved_posts, name='saved_posts'),
    path('check-saved/', views.check_saved_status, name='check_saved_status'),
] # ← NEW