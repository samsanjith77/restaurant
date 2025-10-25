from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser




from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ✅ Register - only superuser can create users
class RegisterUserView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # Only admin

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password required'}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=400)

        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )

        # Optional: return tokens for new user
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'User created successfully',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=201)

# ✅ Example protected API
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'username': user.username,
            'email': user.email,
            'is_superuser': user.is_superuser
        })
