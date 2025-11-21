from django.urls import path
from .views import *

urlpatterns = [
    # Permissions
    path('permissions/', PermissionListView.as_view(), name='permission-list'),
    path('permissions/<int:pk>/', PermissionRetrieveUpdateView.as_view(), name='permission-ru'),
    path('permissions/history/<int:pk>/', PermissionHistoryListView.as_view(), name='permission-history-detail'),
    path('permissions/history/', AllPermissionHistoryListView.as_view(), name='permission-history-list'),
    
    # Roles
    path('roles/', RoleListCreateView.as_view(), name='role-list-create'),
    path('roles/<int:pk>/', RoleRetrieveUpdateDestroyView.as_view(), name='role-rud'),
    path('roles/history/<int:pk>/', RoleHistoryListView.as_view(), name='role-history-detail'),
    path('roles/history/', AllRoleHistoryListView.as_view(), name='role-history-list'),
    
    # Groups
    path('groups/', GroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<int:pk>/', GroupRetrieveUpdateDestroyView.as_view(), name='group-rud'),
    path('groups/history/<int:pk>/', GroupHistoryListView.as_view(), name='group-history-detail'),
    path('groups/history/', AllGroupHistoryListView.as_view(), name='group-history-list'),
    path('groups/<int:group_id>/users/', GroupUsersListView.as_view(), name='group-users-list'),

    # Assignations
    path('roles/assign/<int:user_id>/', AssignRoleToUserView.as_view(), name='assign-role'),
    path('roles/remove/<int:user_id>/', RemoveRoleFromUserView.as_view(), name='remove-role'),
    path('groups/add_user/<int:group_id>/', AddUserToGroupView.as_view(), name='add-user-to-group'),
    path('groups/remove_user/<int:group_id>/', RemoveUserFromGroupView.as_view(), name='remove-user-from-group'),
]
