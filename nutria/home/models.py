# models.py
from django.db import models
from django.utils.text import slugify
import os
import uuid
import random
import string

def generate_id(prefix, length=6):
    """Reusable ID generator: POST-xxxxxx or STORY-xxxxxx"""
    while True:
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        candidate = f"{prefix}-{suffix}"
        # Check both Post and Story to avoid collision (optional)
        if not Post.objects.filter(post_id=candidate).exists() and not Story.objects.filter(story_id=candidate).exists():
            return candidate

def user_media_path(instance, filename):
    """Generic media path: users/<username>/<ID>/<file>"""
    clean_username = slugify(instance.username)
    folder_id = instance.post_id if hasattr(instance, 'post_id') else instance.story_id
    ext = os.path.splitext(filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    return f'users/{clean_username}/{folder_id}/{unique_filename}'

# === Existing Post model ===
class Post(models.Model):
    post_id = models.CharField(max_length=12, unique=True, editable=False)
    username = models.CharField(max_length=100)
    email = models.EmailField()
    caption = models.TextField(blank=True)
    media_file = models.FileField(upload_to=user_media_path)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['username']),
            models.Index(fields=['post_id']),
        ]

    def save(self, *args, **kwargs):
        if not self.post_id:
            self.post_id = generate_id("POST")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} - {self.caption[:20]}"

# === NEW Like model ===
class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_likes')
    username = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'username')  # Ensures one like per user per post
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'username']),
        ]

    def __str__(self):
        return f"{self.username} likes {self.post.post_id}"

# === NEW Story model ===
class Story(models.Model):
    story_id = models.CharField(max_length=12, unique=True, editable=False)  # STORY-xxxxxx
    username = models.CharField(max_length=100)
    email = models.EmailField()
    media_file = models.FileField(upload_to=user_media_path)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # Optional: auto-delete after 24h

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['username']),
            models.Index(fields=['story_id']),
        ]

    def save(self, *args, **kwargs):
        if not self.story_id:
            self.story_id = generate_id("STORY")
        # Optional: auto-set expiry (24 hours from now)
        from datetime import timedelta
        from django.utils import timezone
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Story by {self.username} ({self.story_id})"

# === Comment model (unchanged) ===
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    username = models.CharField(max_length=100)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]

    def __str__(self):
        return f"{self.username}: {self.text[:20]}"