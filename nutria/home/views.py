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
    



# home/views.py
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Recipe
from .serializers import RecipeSerializer
from authentication.models import GoogleUser
import os

# Optional: restrict image types and size
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_image(image):
    """Optional: validate image type and size"""
    if not image:
        return

    ext = os.path.splitext(image.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Only JPG, PNG, and WebP images are allowed.")

    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError("Image file too large. Max size is 5 MB.")

    # Optional: check dimensions
    # width, height = get_image_dimensions(image)
    # if width < 100 or height < 100:
    #     raise ValidationError("Image too small. Minimum size is 100x100.")


# home/views.py (inside add_recipe)
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([AllowAny])
def add_recipe(request):
    email = request.data.get('author_email')
    if not email:
        return Response({"error": "author_email is required"}, status=400)

    try:
        author = GoogleUser.objects.get(email=email)
    except GoogleUser.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    # Create recipe instance manually to inject temp email
    recipe = Recipe(
        title=request.data.get('title', '').strip(),
        ingredients=request.data.get('ingredients', '').strip(),
        instructions=request.data.get('instructions', '').strip(),
        cuisine=request.data.get('cuisine', '').strip(),
        total_time_mins=int(request.data.get('total_time_mins', 45)),
        author=author,
    )

    # 👇 CRITICAL: Set temp email so upload_to works
    recipe._temp_author_email = email

    # Handle image if present
    if 'image' in request.FILES:
        recipe.image = request.FILES['image']

    try:
        recipe.save()  # Now save — upload_to will use _temp_author_email if needed
        serializer = RecipeSerializer(recipe, context={'request': request})
        return Response(serializer.data, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_recipes(request):
    """
    Search recipes by query string (in title or ingredients).
    Returns list of recipes with author info and image URL.
    """
    query = request.GET.get('q', '').strip()

    recipes = Recipe.objects.select_related('author').all()

    if query:
        recipes = recipes.filter(
            title__icontains=query
        ) | recipes.filter(
            ingredients__icontains=query
        )

    # Optional: order by newest first
    recipes = recipes.order_by('-created_at')

    serializer = RecipeSerializer(recipes, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)



# home/views.py - Add these views to your existing views

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Follow
from django.db import IntegrityError

@api_view(['POST'])
def toggle_follow(request):
    """
    Toggle follow/unfollow a user
    Body: {
        "follower": "current_username",
        "following": "target_username"
    }
    """
    follower = request.data.get('follower')
    following = request.data.get('following')

    if not follower or not following:
        return Response(
            {'error': 'Both follower and following usernames are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if follower == following:
        return Response(
            {'error': 'Cannot follow yourself'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Check if already following
        follow_obj = Follow.objects.filter(follower=follower, following=following).first()
        
        if follow_obj:
            # Unfollow
            follow_obj.delete()
            is_following = False
            message = f"Unfollowed {following}"
        else:
            # Follow
            Follow.objects.create(follower=follower, following=following)
            is_following = True
            message = f"Now following {following}"

        # Get updated counts
        followers_count = Follow.get_followers_count(following)
        following_count = Follow.get_following_count(follower)

        return Response({
            'success': True,
            'message': message,
            'is_following': is_following,
            'followers_count': followers_count,
            'following_count': following_count
        }, status=status.HTTP_200_OK)

    except IntegrityError as e:
        return Response(
            {'error': 'Database error occurred', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_user_stats(request, username):
    """
    Get user statistics (followers, following counts, etc.)
    GET /api/user-stats/<username>/
    Query params: ?current_user=<username> (optional, to check if following)
    """
    current_user = request.query_params.get('current_user')

    followers_count = Follow.get_followers_count(username)
    following_count = Follow.get_following_count(username)
    
    # Check if current user is following this user
    is_following = False
    if current_user and current_user != username:
        is_following = Follow.is_following(current_user, username)

    # Optional: Get post count (if you want to include it)
    from .models import Post
    posts_count = Post.objects.filter(username=username).count()

    return Response({
        'username': username,
        'followers_count': followers_count,
        'following_count': following_count,
        'posts_count': posts_count,
        'is_following': is_following,
        'is_own_profile': current_user == username
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_followers_list(request, username):
    """
    Get list of followers for a user
    GET /api/followers/<username>/
    """
    followers = Follow.get_followers_list(username)
    
    return Response({
        'username': username,
        'followers': followers,
        'count': len(followers)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_following_list(request, username):
    """
    Get list of users this user is following
    GET /api/following/<username>/
    """
    following = Follow.get_following_list(username)
    
    return Response({
        'username': username,
        'following': following,
        'count': len(following)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def check_follow_status(request):
    """
    Check if one user follows another
    GET /api/check-follow/?follower=<username>&following=<username>
    """
    follower = request.query_params.get('follower')
    following = request.query_params.get('following')

    if not follower or not following:
        return Response(
            {'error': 'Both follower and following parameters are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    is_following = Follow.is_following(follower, following)

    return Response({
        'follower': follower,
        'following': following,
        'is_following': is_following
    }, status=status.HTTP_200_OK)



# home/views.py - Add these views

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import SavedPost, Post
from django.db import IntegrityError

@api_view(['POST'])
def toggle_save_post(request):
    """
    Toggle save/unsave a post
    Body: {
        "post_id": "POST-abc123",
        "username": "current_username"
    }
    """
    post_id = request.data.get('post_id')
    username = request.data.get('username')

    if not post_id or not username:
        return Response(
            {'error': 'Both post_id and username are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get the post
        post = Post.objects.filter(post_id=post_id).first()
        if not post:
            return Response(
                {'error': 'Post not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already saved
        saved_post = SavedPost.objects.filter(post=post, username=username).first()
        
        if saved_post:
            # Unsave
            saved_post.delete()
            is_saved = False
            message = "Post removed from saved"
        else:
            # Save
            SavedPost.objects.create(post=post, username=username)
            is_saved = True
            message = "Post saved"

        return Response({
            'success': True,
            'message': message,
            'is_saved': is_saved,
            'post_id': post_id
        }, status=status.HTTP_200_OK)

    except IntegrityError as e:
        return Response(
            {'error': 'Database error occurred', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_saved_posts(request, username):
    """
    Get all saved posts for a user
    GET /api/saved-posts/<username>/
    """
    try:
        saved_posts = SavedPost.get_saved_posts(username)
        
        posts_data = []
        for saved in saved_posts:
            post = saved.post
            
            # Build full media URL
            media_url = None
            if post.media_file:
                media_url = request.build_absolute_uri(post.media_file.url)
            
            # Get avatar URL from authentication.GoogleUser if exists
            avatar_url = None
            try:
                from authentication.models import GoogleUser
                google_user = GoogleUser.objects.filter(name=post.username).first()
                if google_user and google_user.photo_url:
                    avatar_url = google_user.photo_url
            except:
                pass
            
            # Get comments
            comments = []
            for comment in post.comments.all():
                comments.append({
                    'username': comment.username,
                    'text': comment.text,
                    'created_at': comment.created_at.isoformat(),
                })
            
            # Check if current user liked this post
            liked_by_user = post.post_likes.filter(username=username).exists()
            
            posts_data.append({
                'post_id': post.post_id,
                'username': post.username,
                'email': post.email,
                'caption': post.caption,
                'media_url': media_url,
                'avatar_url': avatar_url,
                'created_at': post.created_at.isoformat(),
                'likes': post.post_likes.count(),
                'liked_by_user': liked_by_user,
                'comments': comments,
                'saved_at': saved.created_at.isoformat(),  # When it was saved
            })
        
        return Response({
            'username': username,
            'saved_posts': posts_data,
            'count': len(posts_data)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'Failed to fetch saved posts: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def check_saved_status(request):
    """
    Check if a post is saved by a user
    GET /api/check-saved/?post_id=<post_id>&username=<username>
    """
    post_id = request.query_params.get('post_id')
    username = request.query_params.get('username')

    if not post_id or not username:
        return Response(
            {'error': 'Both post_id and username parameters are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    is_saved = SavedPost.is_saved(post_id, username)

    return Response({
        'post_id': post_id,
        'username': username,
        'is_saved': is_saved
    }, status=status.HTTP_200_OK)


# UPDATED: Modify your existing posts view to include saved status
@api_view(['GET'])
def get_posts(request):
    """
    Get all posts with like and saved status for the requesting user
    GET /api/posts/?username=<username>
    """
    username = request.query_params.get('username')
    
    posts = Post.objects.all().order_by('-created_at')
    posts_data = []
    
    for post in posts:
        # Build full media URL
        media_url = None
        if post.media_file:
            media_url = request.build_absolute_uri(post.media_file.url)
        
        # Get avatar URL
        avatar_url = None
        try:
            from authentication.models import GoogleUser
            google_user = GoogleUser.objects.filter(name=post.username).first()
            if google_user and google_user.photo_url:
                avatar_url = google_user.photo_url
        except:
            pass
        
        # Get comments
        comments = []
        for comment in post.comments.all():
            comments.append({
                'username': comment.username,
                'text': comment.text,
                'created_at': comment.created_at.isoformat(),
            })
        
        # Check if current user liked and saved this post
        liked_by_user = False
        saved_by_user = False
        if username:
            liked_by_user = post.post_likes.filter(username=username).exists()
            saved_by_user = SavedPost.is_saved(post.post_id, username)
        
        posts_data.append({
            'post_id': post.post_id,
            'username': post.username,
            'email': post.email,
            'caption': post.caption,
            'media_url': media_url,
            'avatar_url': avatar_url,
            'created_at': post.created_at.isoformat(),
            'likes': post.post_likes.count(),
            'liked_by_user': liked_by_user,
            'saved_by_user': saved_by_user,  # Added
            'comments': comments,
        })
    
    return Response(posts_data, status=status.HTTP_200_OK)