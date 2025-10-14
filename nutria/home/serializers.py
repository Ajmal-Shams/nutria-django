# serializers.py
from rest_framework import serializers
from .models import Post, Comment, Story
import hashlib

class CommentSerializer(serializers.ModelSerializer):
    post_id = serializers.CharField(source='post.post_id', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'username', 'text', 'created_at', 'post_id']
        read_only_fields = ['created_at']


# serializers.py (Update only the get_liked_by_user method)
from rest_framework import serializers
from .models import Post, Comment, Story, Like
import hashlib

class PostSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    media_url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    media_file = serializers.FileField(write_only=True)
    post_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    liked_by_user = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'post_id', 'username', 'email', 'caption',
            'media_file', 'media_url', 'avatar_url', 'likes',
            'created_at', 'comments', 'liked_by_user'
        ]
        read_only_fields = ['created_at', 'post_id']

    def get_media_url(self, obj):
        if not obj.media_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.media_file.url)
        return obj.media_file.url

    def get_avatar_url(self, obj):
        email_hash = hashlib.md5(obj.email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=mp&s=150"
    
    def get_liked_by_user(self, obj):
        # Get username from request context
        request = self.context.get('request')
        username = None
        
        if request:
            # Check query parameters first (for GET requests)
            username = request.query_params.get('username')
            
            # If not in query params, check POST data
            if not username and hasattr(request, 'data'):
                username = request.data.get('username')
        
        if not username:
            return False
        
        return Like.objects.filter(post=obj, username=username).exists()


class CommentSerializer(serializers.ModelSerializer):
    post_id = serializers.CharField(source='post.post_id', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'username', 'text', 'created_at', 'post_id']
        read_only_fields = ['created_at']


class StorySerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    media_file = serializers.FileField(write_only=True)
    story_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Story
        fields = [
            'story_id',
            'username',
            'email',
            'media_file',
            'media_url',
            'avatar_url',
            'created_at',
            'expires_at'
        ]
        read_only_fields = ['created_at', 'story_id', 'expires_at']

    def get_media_url(self, obj):
        if not obj.media_file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.media_file.url)
        return obj.media_file.url

    def get_avatar_url(self, obj):
        email_hash = hashlib.md5(obj.email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=mp&s=150"