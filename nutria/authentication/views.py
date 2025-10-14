from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import GoogleUser
from .serializers import GoogleUserSerializer

@api_view(['POST'])
def save_google_user(request):
    data = request.data
    user, created = GoogleUser.objects.get_or_create(
        email=data.get('email'),
        defaults={
            'name': data.get('name'),
            'photo_url': data.get('photoUrl')
        }
    )
    serializer = GoogleUserSerializer(user)
    if created:
        return Response({'status': 'created', 'user': serializer.data})
    else:
        return Response({'status': 'exists', 'user': serializer.data})
    