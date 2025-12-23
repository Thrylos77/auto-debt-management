from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import generics, permissions, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView as SimpleJWTTokenObtainPairView
from rest_framework.decorators import action
from rest_framework.response import Response

from rbac.services.permission_services import AutoPermissionMixin
from .models import User
from .serializers import *
from .services import otp_services, user_services


# Custom TokenObtainPairView to log user login
@extend_schema(tags=["Users"])
class TokenObtainPairView(SimpleJWTTokenObtainPairView):
    """
    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # The user object is attached to the serializer after successful validation
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
        return response

# Register a new user
@extend_schema(tags=["Users"])
class RegisterView(AutoPermissionMixin, generics.CreateAPIView):
    serializer_class = RegisterSerializer
    resource = "user"

# This view allows users to retrieve their own details
@extend_schema(tags=["Users"])
class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

# This view allows admins to list all users
@extend_schema(tags=["Users"])
class UserListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = UserSerializer
    resource = "user"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['roles', 'groups', 'is_active']

    def get_queryset(self):
        return user_services.get_accessible_users(self.request.user).order_by('id')


# This view allows admins to retrieve, update, or delete a user by their ID
@extend_schema(tags=["Users"])
class UserRetrieveUpdateDestroyView(AutoPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'pk'
    resource = "user"

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user_services.desactivate_user(user)
        return Response({'detail': 'User has been deactivated (soft delete).'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='reactivate')
    def reactivate(self, request, pk=None):
        user = self.get_object()
        user_services.reactivate_user(user)
        return Response({'detail': 'User has been reactivated.'}, status=status.HTTP_200_OK)



# A view for logging user logout and blacklisting the refresh token
@extend_schema(tags=["Users"])
class LogoutView(AutoPermissionMixin, generics.GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


# ----- Historical Read -----
@extend_schema(tags=["Users"])
class UserHistoryListView(AutoPermissionMixin, generics.ListAPIView):
    # Retrieves the change history for a specific user.
    serializer_class = HistoricalUserSerializer
    resource = "user_history"

    def get_queryset(self):
        user_pk = self.kwargs['pk']
        return User.history.filter(id=user_pk).order_by('-history_date')

@extend_schema_view(get=extend_schema(operation_id="all_user_history", tags=["Users"]))
class AllUserHistoryListView(AutoPermissionMixin, generics.ListAPIView):
    """
    Retrieves the complete change history for all users, ordered by most recent first.
    This provides a full audit trail for the system.
    """
    serializer_class = HistoricalUserSerializer
    resource = "user_history"
    queryset = User.history.all().order_by('-history_date')



# ----- Password management -----

# USER to change their own password
@extend_schema(tags=["Users"])
class ChangeOwnPasswordView(AutoPermissionMixin, generics.GenericAPIView):
    serializer_class = ChangeOwnPasswordSerializer
    resource = "user"
    permission_code_map = { 'PUT': 'change_own_password' }

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(instance=request.user)
        
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

# For role ADMIN or Superuser to change any User password
@extend_schema(tags=["Users"])
class AdminChangePasswordView(AutoPermissionMixin, generics.GenericAPIView):
    serializer_class = AdminChangePasswordSerializer
    resource = "user"
    queryset = User.objects.all()
    permission_code_map = { 'PUT': 'change_password' }

    def get_object(self):
        user_id = self.kwargs.get('pk')
        return get_object_or_404(self.get_queryset(), pk=user_id)

    def put(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'request': request, 'user': user})
        serializer.is_valid(raise_exception=True)
        serializer.save(instance=user)
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

# Reset Password OTP management
@extend_schema(tags=["Users"])
class RequestOTPView(generics.CreateAPIView):
    serializer_class = RequestOTPSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.context['user']
        otp_services.request_password_reset_otp(user)
        return Response({"detail": "OTP has been sent to your email."}, status=status.HTTP_200_OK)

@extend_schema(tags=["Users"])
class ResetPasswordView(generics.CreateAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.context['user']
        otp_code = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        otp_services.reset_password_with_otp(user, otp_code, new_password)
        
        return Response({"detail": "✔️ Password reset successfully."}, status=status.HTTP_200_OK)