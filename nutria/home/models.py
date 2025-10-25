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
    

# home/models.py
from django.db import models
import os

def recipe_image_path(instance, filename):
    # If author is already set (e.g., on update), use it
    if hasattr(instance, 'author') and instance.author_id:
        email = instance.author.email
    else:
        # Fallback: use temp_email if provided (during creation)
        email = getattr(instance, '_temp_author_email', 'unknown')
    
    safe_email = email.replace('@', '_at_').replace('.', '_')
    return f'recipe_photos/{safe_email}/{filename}'


class Recipe(models.Model):
    title = models.CharField(max_length=255)
    ingredients = models.TextField()
    instructions = models.TextField()
    cuisine = models.CharField(max_length=100, blank=True)
    total_time_mins = models.IntegerField(default=45)
    image = models.ImageField(upload_to=recipe_image_path, blank=True, null=True)
    author = models.ForeignKey('authentication.GoogleUser', on_delete=models.CASCADE, related_name='recipes')
    created_at = models.DateTimeField(auto_now_add=True)

    # Temporary storage for email during creation
    _temp_author_email = None

    def __str__(self):
        return f"{self.title} by {self.author.email}"
    

# home/models.py - Add these to your existing models

from django.db import models
from django.utils.text import slugify
import os
import uuid
import random
import string

# ... (Keep all your existing helper functions and models) ...

# === NEW Follow model ===
class Follow(models.Model):
    """
    Represents a follow relationship between users.
    follower follows following
    """
    follower = models.CharField(max_length=100)  # Username of the person following
    following = models.CharField(max_length=100)  # Username of the person being followed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')  # Prevent duplicate follows
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['following']),
            models.Index(fields=['follower', 'following']),
        ]
        constraints = [
            # Prevent users from following themselves
            models.CheckConstraint(
                check=~models.Q(follower=models.F('following')),
                name='prevent_self_follow'
            )
        ]

    def __str__(self):
        return f"{self.follower} follows {self.following}"

    @classmethod
    def get_followers_count(cls, username):
        """Get count of followers for a user"""
        return cls.objects.filter(following=username).count()

    @classmethod
    def get_following_count(cls, username):
        """Get count of users this user is following"""
        return cls.objects.filter(follower=username).count()

    @classmethod
    def is_following(cls, follower, following):
        """Check if follower is following the user"""
        return cls.objects.filter(follower=follower, following=following).exists()

    @classmethod
    def get_followers_list(cls, username):
        """Get list of usernames who follow this user"""
        return list(cls.objects.filter(following=username).values_list('follower', flat=True))

    @classmethod
    def get_following_list(cls, username):
        """Get list of usernames this user follows"""
        return list(cls.objects.filter(follower=username).values_list('following', flat=True))
    

# home/models.py - Add this to your existing models

# === NEW SavedPost model ===
class SavedPost(models.Model):
    """
    Represents a saved post by a user (like Instagram's bookmark feature)
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    username = models.CharField(max_length=100)  # User who saved the post
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'username')  # User can save a post only once
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['username', '-created_at']),
            models.Index(fields=['post', 'username']),
        ]

    def __str__(self):
        return f"{self.username} saved {self.post.post_id}"

    @classmethod
    def is_saved(cls, post_id, username):
        """Check if a post is saved by a user"""
        return cls.objects.filter(post__post_id=post_id, username=username).exists()

    @classmethod
    def get_saved_posts(cls, username):
        """Get all saved posts for a user"""
        return cls.objects.filter(username=username).select_related('post').order_by('-created_at')