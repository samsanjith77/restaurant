from django.urls import path
from .views import RegisterUserView, ProfileView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import CustomTokenObtainPairView

urlpatterns = [
    # JWT login and refresh
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Only superuser can create new users
    path('register/', RegisterUserView.as_view(), name='register'),

    # Example protected API
    path('profile/', ProfileView.as_view(), name='profile'),
]
