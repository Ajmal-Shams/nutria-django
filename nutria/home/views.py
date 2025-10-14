# views.py
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Post, Comment, Story, Like
from .serializers import PostSerializer, CommentSerializer, StorySerializer
import logging

logger = logging.getLogger(__name__)

@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser])
def post_list_create(request):
    if request.method == 'GET':
        posts = Post.objects.all().order_by('-created_at')
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = PostSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            post = serializer.save()
            # Re-serialize the saved instance with context
            output_serializer = PostSerializer(post, context={'request': request})
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def post_like(request, post_id):
    try:
        post = Post.objects.get(post_id=post_id)
        username = request.data.get('username')
        
        if not username:
            return Response(
                {'error': 'Username is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from .models import Like
        
        # Check if user already liked this post
        like_exists = Like.objects.filter(post=post, username=username).exists()
        
        if like_exists:
            # Unlike: Remove the like
            Like.objects.filter(post=post, username=username).delete()
            post.likes = max(0, post.likes - 1)  # Prevent negative likes
            post.save()
            return Response({
                'likes': post.likes,
                'liked': False,
                'message': 'Post unliked'
            })
        else:
            # Like: Add the like
            Like.objects.create(post=post, username=username)
            post.likes += 1
            post.save()
            return Response({
                'likes': post.likes,
                'liked': True,
                'message': 'Post liked'
            })
            
    except Post.DoesNotExist:
        return Response(
            {'error': 'Post not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    


# views.py (updated comment view)
@api_view(['POST'])
def comment_list_create(request):
    if request.method == 'POST':
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            post_id = request.data.get('post')  # Now expects "POST-xxxxxx"
            try:
                post = Post.objects.get(post_id=post_id)
                serializer.save(post=post)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Post.DoesNotExist:
                return Response(
                    {'error': 'Post not found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# views.py (add these)
@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser])
def story_list_create(request):
    from django.utils import timezone

    if request.method == 'GET':
        # Include both current user's story and others' active stories
        stories = Story.objects.filter(expires_at__gt=timezone.now()).order_by('-created_at')
        serializer = StorySerializer(stories, many=True, context={'request': request})
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = StorySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            story = serializer.save()
            output_serializer = StorySerializer(story, context={'request': request})
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)