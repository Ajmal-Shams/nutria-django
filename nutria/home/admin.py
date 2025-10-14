# admin.py
from django.contrib import admin
from .models import Post, Comment

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('post_id', 'username', 'email', 'created_at', 'likes')
    search_fields = ('post_id', 'username', 'email')
    readonly_fields = ('post_id',)  # Since it's auto-generated

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post_id_display', 'username', 'text_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('username', 'text', 'post__post_id')

    def post_id_display(self, obj):
        return obj.post.post_id
    post_id_display.short_description = 'Post ID'

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Comment Preview'