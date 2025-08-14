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

from rest_framework.urlpatterns import format_suffix_patterns

# Main URL patterns - using the refactored API views
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Main chat endpoint - now using modular ChatView via ChatAPIView alias
    path('api/chat/', ChatAPIView.as_view(), name='chat-api'),
    
    # User endpoints - using refactored UserListView
    path('api/users/', UserListView.as_view(), name='user-list-api'),
    
    # Admin endpoints - using refactored RunStoredProcedureView
    path('run-stored-procedure/', RunStoredProcedureView.as_view(), name='run-procedure-api'),
]

urlpatterns = format_suffix_patterns(urlpatterns)