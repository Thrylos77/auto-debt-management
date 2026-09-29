from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from rbac.policies.permission_policy import AutoPermissionMixin
from users.models import User, UserPreference
from users.policies.user_policy import UserPolicy
from users.serializers import (
    EmptyRequestSerializer,
    HistoricalUserSerializer,
    OwnProfileSerializer,
    RegisterSerializer,
    UserSerializer,
    UserPreferenceSerializer,
)
from users.services import user_service


@extend_schema(tags=["Users"])
class RegisterView(AutoPermissionMixin, generics.CreateAPIView):
    serializer_class = RegisterSerializer
    resource = "user"


@extend_schema(tags=["Users"])
class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OwnProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        serializer.save()


@extend_schema(tags=["Users"])
class UserListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = UserSerializer
    resource = "user"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active"]
    ordering = ["id"]

    def get_queryset(self):
        return user_service.get_accessible_users(self.request.user)


@extend_schema(tags=["Users"])
class UserRetrieveUpdateDestroyView(AutoPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    resource = "user"
    # GenericAPIView exposes the action as the HTTP method; keep the
    # explicit CRUD key as well for compatibility with DRF viewsets.
    permission_code_map = {"destroy": "deactivate", "DELETE": "deactivate"}

    def perform_update(self, serializer):
        target = self.get_object()
        if not UserPolicy.can_update(self.request.user, target):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to update this user.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        target = self.get_object()
        successor_id = request.data.get("successor_user_id")
        successor = None
        if successor_id:
            successor = get_object_or_404(User, pk=successor_id)
            if not successor.is_active:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"successor_user_id": "Successor must be active."})
        user_service.deactivate_user(
            target,
            successor_user=successor,
            reason=request.data.get("reason", ""),
            actor=request.user,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Users"])
class ReactivateUserView(AutoPermissionMixin, generics.GenericAPIView):
    queryset = User.objects.all()
    serializer_class = EmptyRequestSerializer
    resource = "user"
    permission_code_map = {"POST": "reactivate"}

    @extend_schema(
        summary="Reactivate a user",
        request=None,
        responses=OpenApiResponse(
            response=UserSerializer,
            description="The user has been reactivated.",
        ),
    )
    def post(self, request, *args, **kwargs):
        target = self.get_object()
        if not UserPolicy.can_reactivate(request.user, target):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to reactivate this user.")
        user_service.reactivate_user(target, actor=request.user, request=request)
        return Response({"detail": "User has been reactivated."}, status=status.HTTP_200_OK)


@extend_schema(tags=["Users"])
class UserHistoryListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = HistoricalUserSerializer
    resource = "user_history"
    queryset = User.history.none()

    def get_queryset(self):
        # OpenAPI generation does not provide the runtime ``pk`` kwarg.
        # Return the empty historical queryset while drf-spectacular inspects
        # the view, then resolve the real object history during requests.
        if getattr(self, "swagger_fake_view", False):
            return self.queryset

        return User.history.filter(
            id=self.kwargs["pk"]
        ).order_by("-history_date")


@extend_schema_view(get=extend_schema(operation_id="all_user_history", tags=["Users"]))
class AllUserHistoryListView(AutoPermissionMixin, generics.ListAPIView):
    serializer_class = HistoricalUserSerializer
    resource = "user_history"
    queryset = User.history.all().order_by("-history_date")


class UserPreferenceView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserPreferenceSerializer

    def get_object(self):
        preference, _ = UserPreference.objects.get_or_create(user=self.request.user)
        return preference
