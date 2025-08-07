"""
URL configuration for chatbot project.

This configuration maintains backward compatibility with existing routes
while supporting the new modular API structure.
"""

from django.contrib import admin
from django.urls import path

# Import from the refactored API router (maintains backward compatibility)
from .api import ChatView, UserListView, RunStoredProcedureView

# Create aliases for backward compatibility
ChatAPIView = ChatView

# Import from existing API modules (for routes not yet migrated)
from .api_users import UserListAPIView
from .api_tasks import TaskListCreateView

from rest_framework.urlpatterns import format_suffix_patterns

# Main URL patterns - using the refactored API views
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Main chat endpoint - now using modular ChatView via ChatAPIView alias
    path('api/chat/', ChatAPIView.as_view(), name='chat-api'),
    
    # User endpoints - using refactored UserListView
    path('api/users/', UserListView.as_view(), name='user-list-api'),
    
    # Task endpoints - still using existing api_tasks.py (could be migrated later)
    path('api/tasks/', TaskListCreateView.as_view(), name='task-list-create-api'),
    path('api/tasks/<int:pk>/', TaskListCreateView.as_view(), name='task-detail-api'),
    
    # Admin endpoints - using refactored RunStoredProcedureView
    path('run-stored-procedure/', RunStoredProcedureView.as_view(), name='run-procedure-api'),
]

# Alternative: If you want to fully use the new modular structure, uncomment below:
# from .api.views.chat import ChatView
# from .api.views.users import UserListView
# from .api.views.admin import RunStoredProcedureView
# 
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('api/chat/', ChatView.as_view(), name='chat-api'),
#     path('api/users/', UserListView.as_view(), name='user-list-api'),
#     path('api/tasks/', TaskListCreateView.as_view(), name='task-list-create-api'),
#     path('api/tasks/<int:pk>/', TaskListCreateView.as_view(), name='task-detail-api'),
#     path('run-stored-procedure/', RunStoredProcedureView.as_view(), name='run-procedure-api'),
# ]

urlpatterns = format_suffix_patterns(urlpatterns)